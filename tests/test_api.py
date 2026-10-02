import httpx
import pytest
from conftest import DOTS, DOTS_RESULT, FakeNetwork, choice, dots_kev, has_evidence, noul, unsure
from fastapi.testclient import TestClient

from web_search.app import create_app
from web_search.config import Settings


def test_confident_answer_is_returned_without_search(client_for):
    network = FakeNetwork(lambda body: {"when": choice({"2024": 0.02, "2026": 0.96, "before_2024": 0.02})})
    with client_for(network) as client:
        response = client.post("/v1/systemone", json=DOTS, headers={"x-typesafe-request-id": "abc"})

    assert response.status_code == 200
    assert response.headers["x-typesafe-request-id"] == "abc"
    out = response.json()
    assert out["answers"]["when"]["choice"] == "2026"
    assert network.kev_bodies == [DOTS]
    assert network.searches == []
    assert out["search"]["questions"]["when"] == {
        "initial_confidence": 0.94,
        "confidence": 0.94,
        "searched": False,
        "rounds": 0,
        "query": None,
        "needs_review": False,
    }


def test_unsure_answer_is_searched_and_asked_again(client_for):
    network = FakeNetwork(dots_kev, results=lambda query, page: [DOTS_RESULT])
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert out["answers"]["when"]["choice"] == "2026"
    (search,) = network.searches
    assert search.url.params["q"] == (
        "When was OpenAI Dots announced? Which date range corresponds to when OpenAI announced Dots?"
    )
    assert search.url.params["format"] == "json"
    assert search.url.params["pageno"] == "1"

    retried_state = network.kev_bodies[1]["state"]
    assert retried_state.startswith("When was OpenAI Dots announced?\n\nToday's date: 2026-10-02.\n")
    assert f"- OpenAI launches Dots ({DOTS_RESULT['url']}): At OpenAI's DevDay" in retried_state

    report = out["search"]["questions"]["when"]
    assert report["searched"] and report["rounds"] == 1 and not report["needs_review"]
    assert report["initial_confidence"] < 0.5 < report["confidence"]
    assert out["usage"] == {"input_tokens": 200, "output_tokens": 20}
    assert out["search"]["evidence"][0]["url"] == DOTS_RESULT["url"]


def test_web_search_off_returns_kev_answer_unsearched(client_for):
    network = FakeNetwork(dots_kev, results=lambda query, page: [DOTS_RESULT])
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=DOTS, headers={"x-web-search": "off"}).json()

    assert out["answers"]["when"]["choice"] == "before_2024"
    assert "search" not in out
    assert network.searches == []
    assert network.kev_bodies == [DOTS]


def test_web_search_always_searches_confident_answers_once(client_for):
    network = FakeNetwork(
        lambda body: {"when": choice({"2024": 0.1, "2026": 0.8, "before_2024": 0.1})},
        results=lambda query, page: [DOTS_RESULT],
    )
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=DOTS, headers={"x-web-search": "always"}).json()

    assert len(network.searches) == 1
    assert out["search"]["rounds"] == 1
    assert out["search"]["questions"]["when"]["searched"]
    assert out["search"]["evidence"][0]["url"] == DOTS_RESULT["url"]


def test_threshold_decides_what_is_searched(client_for):
    network = FakeNetwork(lambda body: {"when": choice({"2024": 0.1, "2026": 0.7, "before_2024": 0.2})})
    with client_for(network) as client:
        client.post("/v1/systemone", json=DOTS)
    assert network.searches == []

    network = FakeNetwork(lambda body: {"when": choice({"2024": 0.1, "2026": 0.7, "before_2024": 0.2})})
    with client_for(network, threshold=0.8) as client:
        client.post("/v1/systemone", json=DOTS)
    assert len(network.searches) == 1


def test_only_unsure_questions_are_asked_again(client_for):
    body = {
        "state": "Order #1 was charged twice. When was OpenAI Dots announced?",
        "questions": {
            "billing": {"type": "noul", "instructions": "Is this about billing?"},
            "when": DOTS["questions"]["when"],
        },
    }

    def kev(request):
        answers = {}
        if "billing" in request["questions"]:
            answers["billing"] = noul(0.1 if has_evidence(request["state"]) else 0.97)
        if "when" in request["questions"]:
            answers["when"] = dots_kev(request)["when"]
        return answers

    network = FakeNetwork(kev, results=lambda query, page: [DOTS_RESULT])
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=body).json()

    assert list(network.kev_bodies[1]["questions"]) == ["when"]
    assert out["answers"]["billing"]["noul"] == 0.97
    assert list(out["answers"]) == ["billing", "when"]
    assert not out["search"]["questions"]["billing"]["searched"]


def test_next_round_reads_the_next_page(client_for):
    network = FakeNetwork(
        lambda body: {"when": unsure()},
        results=lambda query, page: [{"title": f"page {page}", "url": f"https://x/{page}", "content": "..."}],
    )
    with client_for(network, max_rounds=2) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert [s.url.params["pageno"] for s in network.searches] == ["1", "2"]
    assert len(network.kev_bodies) == 3
    assert "page 1" in network.kev_bodies[2]["state"] and "page 2" in network.kev_bodies[2]["state"]
    assert out["search"]["rounds"] == 2 and out["search"]["stopped"] is None
    assert out["search"]["questions"]["when"]["needs_review"]


def test_repeated_results_stop_the_rounds(client_for):
    network = FakeNetwork(lambda body: {"when": unsure()}, results=lambda query, page: [DOTS_RESULT])
    with client_for(network, max_rounds=3) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert out["search"]["rounds"] == 1 and out["search"]["stopped"] == "no_new_results"
    assert len(network.searches) == 2 and len(network.kev_bodies) == 2


def test_max_evidence_caps_the_state(client_for):
    def results(query, page):
        return [{"title": f"r{page}-{i}", "url": f"https://x/{page}/{i}", "content": "c"} for i in range(5)]

    network = FakeNetwork(lambda body: {"when": unsure()}, results=results)
    with client_for(network, max_rounds=5, max_evidence=7) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert len(out["search"]["evidence"]) == 7
    assert out["search"]["stopped"] == "max_evidence" and out["search"]["rounds"] == 2


def test_shared_query_is_searched_once(client_for):
    question = {"type": "noul", "instructions": "x"}
    body = {"state": "Глобус", "questions": {"a": question, "b": question}}
    network = FakeNetwork(
        lambda request: {q: noul(0.5) for q in request["questions"]}, results=lambda query, page: [DOTS_RESULT]
    )
    with client_for(network, max_rounds=1) as client:
        client.post("/v1/systemone", json=body)

    assert len(network.searches) == 1


@pytest.mark.parametrize("status", [403, 502])
def test_searxng_failure_returns_the_first_answer_for_review(client_for, status):
    network = FakeNetwork(dots_kev, searxng_status=status)
    with client_for(network) as client:
        response = client.post("/v1/systemone", json=DOTS)

    assert response.status_code == 200
    out = response.json()
    assert out["answers"]["when"]["choice"] == "before_2024"
    assert out["search"]["stopped"] == "search_unavailable"
    assert out["search"]["questions"]["when"]["needs_review"]
    assert len(network.kev_bodies) == 1


def test_blocked_engines_are_reported(client_for, caplog):
    blocked = [["duckduckgo", "CAPTCHA"], ["google", "Suspended: too many requests"]]
    network = FakeNetwork(dots_kev, unresponsive=blocked)
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert out["search"]["stopped"] == "search_unavailable"
    assert out["search"]["unresponsive_engines"] == ["duckduckgo: CAPTCHA", "google: Suspended: too many requests"]
    assert "engines failing" in caplog.text


def test_client_authorization_reaches_kev(client_for):
    network = FakeNetwork(dots_kev, results=lambda query, page: [DOTS_RESULT])
    with client_for(network) as client:
        client.post("/v1/systemone", json=DOTS, headers={"authorization": "Bearer secret"})

    assert [r.headers["authorization"] for r in network.kev_requests] == ["Bearer secret", "Bearer secret"]


@pytest.mark.parametrize(
    "payload, status, detail",
    [
        (b"not json", 400, "not JSON"),
        (b'{"state": "x", "questions": {}}', 422, "non-empty questions"),
        (b"[1, 2]", 422, "non-empty questions"),
    ],
)
def test_bad_requests_never_reach_kev(client_for, payload, status, detail):
    network = FakeNetwork(dots_kev)
    with client_for(network) as client:
        response = client.post("/v1/systemone", content=payload, headers={"content-type": "application/json"})

    assert response.status_code == status and detail in response.text
    assert network.kev_requests == []


def test_kev_errors_on_the_first_call_pass_through(client_for):
    network = FakeNetwork(lambda body: httpx.Response(422, json={"detail": "state has 70,000 tokens"}))
    with client_for(network) as client:
        response = client.post("/v1/systemone", json=DOTS)

    assert response.status_code == 422
    assert response.json() == {"detail": "state has 70,000 tokens"}


def test_kev_refusing_the_retry_keeps_the_first_answer(client_for):
    def kev(body):
        if has_evidence(body["state"]):
            return httpx.Response(422, json={"detail": "too long"})
        return dots_kev(body)

    network = FakeNetwork(kev, results=lambda query, page: [DOTS_RESULT])
    with client_for(network) as client:
        out = client.post("/v1/systemone", json=DOTS).json()

    assert out["answers"]["when"]["choice"] == "before_2024"
    assert out["search"]["stopped"] == "kev_error_422" and out["search"]["rounds"] == 0


def test_other_routes_are_forwarded_to_kev(client_for):
    network = FakeNetwork(dots_kev)
    with client_for(network) as client:
        models = client.get("/v1/models?verbose=1", headers={"authorization": "Bearer secret"})
        permute = client.post("/v1/systemone/permute", json={"n_perm": 4})

    assert models.status_code == 200 and models.json() == {"path": "/v1/models", "query": "verbose=1"}
    assert permute.json()["path"] == "/v1/systemone/permute"
    forwarded = network.kev_requests[0]
    assert str(forwarded.url).startswith("http://localhost:8010/v1/models")
    assert forwarded.headers["authorization"] == "Bearer secret"
    assert network.searches == []


def test_kev_down():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    app = create_app(Settings(), http=httpx.AsyncClient(transport=httpx.MockTransport(refuse)))
    with TestClient(app) as client:
        assert client.post("/v1/systemone", json=DOTS).status_code == 502
        assert client.get("/v1/models").status_code == 502


def test_health_reports_upstreams(client_for):
    with client_for(FakeNetwork(dots_kev)) as client:
        assert client.get("/health").json() == {"status": "ok", "kev": True, "searxng": True}

    with client_for(FakeNetwork(dots_kev, searxng_status=503)) as client:
        assert client.get("/health").json() == {"status": "ok", "kev": True, "searxng": False}
