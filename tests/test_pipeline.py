import pytest

from web_search.config import Settings
from web_search.pipeline import confidence, empty_round_reason, new_evidence, search_query, with_evidence
from web_search.searxng import Evidence, SearchPage

EVIDENCE = [Evidence(title="t", url="u", content="c", query="q")]


def test_confidence():
    assert confidence({"type": "choice", "confidence": 0.7}) == 0.7
    assert confidence({"type": "score", "confidence": 0.2}) == 0.2
    assert confidence({"type": "noul", "noul": 0.55}) == pytest.approx(0.1)
    assert confidence({"type": "noul", "noul": 0.0}) == 1.0


def test_search_query():
    question = {"instructions": "Which MCC code fits?"}
    assert search_query("Глобус", question) == "Глобус Which MCC code fits?"
    assert search_query("x" * 500, question) == "Which MCC code fits?"
    assert search_query({"merchant": "Глобус"}, {"instructions": None}) == '{"merchant": "Глобус"}'
    assert len(search_query("y" * 199, {"instructions": "z" * 500})) == 300
    same = "When was OpenAI Dots announced?"
    assert search_query(same, {"instructions": same}) == same


def test_with_evidence_on_a_text_state():
    assert with_evidence("s", EVIDENCE, "2026-10-02") == (
        "s\n\nToday's date: 2026-10-02.\nWeb search results (untrusted, retrieved 2026-10-02):\n- t (u): c"
    )


def test_with_evidence_on_object_and_array_states():
    assert with_evidence({"ticket": "x"}, EVIDENCE, "2026-10-02") == {
        "ticket": "x",
        "today": "2026-10-02",
        "web_search_results_untrusted": ["t (u): c"],
    }
    assert with_evidence(["a"], EVIDENCE, "2026-10-02")["input"] == ["a"]
    assert with_evidence({"today": "mine"}, EVIDENCE, "2026-10-02")["input"] == {"today": "mine"}


def test_new_evidence_dedupes_and_respects_room():
    a = Evidence(title="a", url="https://a", content="", query="q")
    b = Evidence(title="b", url="https://b", content="", query="q")
    assert new_evidence([SearchPage([a, b]), SearchPage([b])], {"https://a"}, room=5) == [b]
    assert new_evidence([SearchPage([a, b])], set(), room=1) == [a]


def test_empty_round_reason():
    assert empty_round_reason([SearchPage(failed=True)]) == "search_unavailable"
    assert empty_round_reason([SearchPage(unresponsive=["google: CAPTCHA"])]) == "search_unavailable"
    assert empty_round_reason([SearchPage()]) == "no_new_results"
    assert empty_round_reason([SearchPage(EVIDENCE, ["google: CAPTCHA"])]) == "no_new_results"


def test_settings_defaults_and_env(monkeypatch):
    assert Settings().threshold == 0.5
    assert Settings().kev_url == "http://localhost:8010"
    monkeypatch.setenv("SEARXNG_URL", "http://search.internal:8080/")
    monkeypatch.setenv("SEARCH_THRESHOLD", "0.75")
    settings = Settings.from_env()
    assert settings.searxng_url == "http://search.internal:8080"
    assert settings.threshold == 0.75
