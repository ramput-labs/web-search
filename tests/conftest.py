import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from web_search.app import create_app
from web_search.config import Settings

TODAY = date(2026, 10, 2)

DOTS = {
    "state": "When was OpenAI Dots announced?",
    "model": "kev-latest",
    "questions": {
        "when": {
            "type": "choice",
            "instructions": "Which date range corresponds to when OpenAI announced Dots?",
            "criteria": {"2024": "During 2024", "2026": "During 2026", "before_2024": "Before 2024"},
        }
    },
}

DOTS_RESULT = {
    "title": "OpenAI launches Dots",
    "url": "https://techcrunch.com/2026/09/29/openai-launches-dots/",
    "content": "At OpenAI's DevDay event on Tuesday, the company announced the launch of Dots.",
}


def choice(probabilities: dict[str, float]) -> dict:
    k = len(probabilities)
    best = max(probabilities, key=probabilities.get)
    return {
        "type": "choice",
        "choice": best,
        "confidence": round((probabilities[best] - 1 / k) / (1 - 1 / k), 4),
        "probabilities": probabilities,
    }


def noul(p: float) -> dict:
    return {"type": "noul", "noul": p}


def has_evidence(state) -> bool:
    if isinstance(state, str):
        return "Web search results" in state
    return "web_search_results_untrusted" in json.dumps(state)


def unsure() -> dict:
    return choice({"2024": 0.34, "2026": 0.33, "before_2024": 0.33})


def dots_kev(body: dict) -> dict:
    if has_evidence(body["state"]):
        return {"when": choice({"2024": 0.04, "2026": 0.92, "before_2024": 0.04})}
    return {"when": choice({"2024": 0.44, "2026": 0.02, "before_2024": 0.54})}


class FakeNetwork:
    """Kev on :8010 answers through `kev(body)`; SearXNG on :8888 returns `results(query, page)`."""

    def __init__(self, kev, results=lambda query, page: [], searxng_status=200, unresponsive=()):
        self.kev = kev
        self.results = results
        self.searxng_status = searxng_status
        self.unresponsive = list(unresponsive)
        self.kev_requests: list[httpx.Request] = []
        self.searches: list[httpx.Request] = []

    @property
    def kev_bodies(self) -> list[dict]:
        return [json.loads(r.content) for r in self.kev_requests if r.url.path == "/v1/systemone"]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.port == 8888:
            return self._searxng(request)
        self.kev_requests.append(request)
        if request.url.path != "/v1/systemone":
            return httpx.Response(200, json={"path": request.url.path, "query": str(request.url.query, "ascii")})
        reply = self.kev(json.loads(request.content))
        if isinstance(reply, httpx.Response):
            return reply
        usage = {"input_tokens": 100, "output_tokens": 10}
        return httpx.Response(200, json={"model": "kev-latest", "answers": reply, "usage": usage, "latency_ms": 5.0})

    def _searxng(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search":
            self.searches.append(request)
        if self.searxng_status != 200:
            return httpx.Response(self.searxng_status, text="unavailable")
        if request.url.path == "/healthz":
            return httpx.Response(200, text="OK")
        params = request.url.params
        results = self.results(params["q"], int(params["pageno"]))
        return httpx.Response(
            200, json={"query": params["q"], "results": results, "unresponsive_engines": self.unresponsive}
        )


@pytest.fixture
def client_for():
    def make(network: FakeNetwork, **settings) -> TestClient:
        http = httpx.AsyncClient(transport=httpx.MockTransport(network))
        return TestClient(create_app(Settings(**settings), http=http, today=lambda: TODAY))

    return make
