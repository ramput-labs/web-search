from typing import Any

import httpx

REQUEST_ID_HEADER = "x-typesafe-request-id"


class KevError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(f"Kev answered {status}")
        self.status = status
        self.body = body


class KevClient:
    def __init__(self, http: httpx.AsyncClient, url: str):
        self.http = http
        self.url = url

    async def systemone(self, body: dict, headers: dict[str, str]) -> dict:
        try:
            response = await self.http.post(f"{self.url}/v1/systemone", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise KevError(502, {"detail": f"Kev unreachable at {self.url}: {e!r}"}) from e
        if response.status_code != 200:
            try:
                detail = response.json()
            except ValueError:
                detail = {"detail": response.text[:500]}
            raise KevError(response.status_code, detail)
        return response.json()
