import asyncio
import json
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .kev import REQUEST_ID_HEADER, KevClient, KevError
from .pipeline import Services, answer
from .searxng import SearxngClient

WEB_SEARCH_HEADER = "x-web-search"
HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding", "content-encoding"}


def create_app(
    settings: Settings | None = None,
    *,
    http: httpx.AsyncClient | None = None,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = http or httpx.AsyncClient(timeout=settings.kev_timeout)
        app.state.http = client
        app.state.services = Services(
            kev=KevClient(client, settings.kev_url),
            searxng=SearxngClient(client, settings.searxng_url, settings.results_per_query, settings.snippet_chars),
            settings=settings,
            today=today,
        )
        yield
        if http is None:
            await client.aclose()

    app = FastAPI(title="web-search", version="0.1.0", lifespan=lifespan)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["content-type", "authorization", WEB_SEARCH_HEADER, REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
        )

    @app.get("/health")
    async def health(request: Request):
        """Liveness of web-search itself, plus whether Kev and SearXNG answer; never fails on their account."""
        http: httpx.AsyncClient = request.app.state.http

        async def up(url: str) -> bool:
            try:
                response = await http.get(url, timeout=3)
            except httpx.HTTPError:
                return False
            return response.status_code < 500

        kev, searxng = await asyncio.gather(up(f"{settings.kev_url}/v1/models"), up(f"{settings.searxng_url}/healthz"))
        return {"status": "ok", "kev": kev, "searxng": searxng}

    @app.post("/v1/systemone")
    async def systemone(request: Request):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        headers = {REQUEST_ID_HEADER: request_id}
        if "authorization" in request.headers:
            headers["authorization"] = request.headers["authorization"]

        def reply(content, status: int = 200) -> JSONResponse:
            return JSONResponse(content, status_code=status, headers={REQUEST_ID_HEADER: request_id})

        try:
            body = json.loads(await request.body())
        except ValueError:
            return reply({"detail": "body is not JSON"}, 400)
        if not isinstance(body, dict) or not isinstance(body.get("questions"), dict) or not body["questions"]:
            return reply({"detail": "body must be a System One request with a non-empty questions object"}, 422)

        services = request.app.state.services
        try:
            mode = request.headers.get(WEB_SEARCH_HEADER, "auto").lower()
            if mode == "off":
                return reply(await services.kev.systemone(body, headers))
            return reply(await answer(body, services, headers, always=mode == "always"))
        except KevError as e:
            return reply(e.body, e.status)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def forward_to_kev(path: str, request: Request):
        """Everything but /v1/systemone (models, permute, separate) goes to Kev unchanged."""
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
        try:
            upstream = await request.app.state.http.request(
                request.method,
                f"{settings.kev_url}/{path}",
                params=request.query_params,
                headers=headers,
                content=await request.body(),
            )
        except httpx.HTTPError as e:
            return JSONResponse({"detail": f"Kev unreachable at {settings.kev_url}: {e!r}"}, status_code=502)
        response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
        return Response(upstream.content, status_code=upstream.status_code, headers=response_headers)

    return app
