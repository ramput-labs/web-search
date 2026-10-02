import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from .config import Settings
from .kev import KevClient, KevError
from .searxng import Evidence, SearchPage, SearxngClient

log = logging.getLogger(__name__)


@dataclass
class Services:
    kev: KevClient
    searxng: SearxngClient
    settings: Settings
    today: Callable[[], date] = date.today


@dataclass
class QuestionReport:
    initial_confidence: float
    confidence: float = 0.0
    searched: bool = False
    rounds: int = 0
    query: str | None = None
    needs_review: bool = False


def confidence(answer: dict) -> float:
    """Kev's confidence for choice and score answers; a noul has only p, so its distance from 0.5 is used."""
    if answer.get("type") == "noul":
        return abs(2 * float(answer["noul"]) - 1)
    return float(answer["confidence"])


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def search_query(state: Any, question: dict) -> str:
    """A short state is usually the subject itself, so it leads the query; a long one would drown the engine."""
    state_text = " ".join(as_text(state).split())
    instructions = " ".join(as_text(question.get("instructions")).split())
    if instructions and instructions in state_text:
        # the question is the state itself (a chat UI sends it as both); searching it twice adds nothing
        query = state_text if len(state_text) <= 300 else instructions
    elif len(state_text) <= 200:
        query = f"{state_text} {instructions}"
    else:
        query = instructions or state_text[:200]
    return query.strip()[:300]


def with_evidence(state: Any, evidence: list[Evidence], today: str) -> Any:
    """The date goes in because snippets say "2 days ago"; URLs because news URLs carry the date."""
    lines = [e.line() for e in evidence]
    if isinstance(state, str):
        results = "\n".join(f"- {line}" for line in lines)
        return f"{state}\n\nToday's date: {today}.\nWeb search results (untrusted, retrieved {today}):\n{results}"

    fields = {"today": today, "web_search_results_untrusted": lines}
    if isinstance(state, dict) and not fields.keys() & state.keys():
        return {**state, **fields}
    return {"input": state, **fields}


def new_evidence(pages: list[SearchPage], seen: set[str], room: int) -> list[Evidence]:
    fresh = []
    for result in (r for page in pages for r in page.results):
        key = result.url or result.line()
        if key not in seen and len(fresh) < room:
            seen.add(key)
            fresh.append(result)
    return fresh


def empty_round_reason(pages: list[SearchPage]) -> str:
    """search_unavailable: SearXNG or every engine failed; no_new_results: the engines answered, with nothing new."""
    nothing_found = not any(page.results for page in pages)
    something_failed = any(page.failed or page.unresponsive for page in pages)
    return "search_unavailable" if nothing_found and something_failed else "no_new_results"


async def answer(body: dict, services: Services, headers: dict[str, str], *, always: bool = False) -> dict:
    """Ask Kev; search for every question below the threshold, add the results to the state and ask again,
    re-asking only the unsure questions. `always` searches every question in the first round, however sure Kev
    is; later rounds still only take the unsure ones. Raises KevError only when the first call fails."""
    settings = services.settings
    started = time.perf_counter()
    questions = body["questions"]
    today = services.today().isoformat()

    first = await services.kev.systemone(body, headers)
    answers = dict(first["answers"])
    usage = dict(first.get("usage") or {})
    reports = {qid: QuestionReport(initial_confidence=confidence(a)) for qid, a in answers.items()}

    evidence: list[Evidence] = []
    seen: set[str] = set()
    unresponsive: set[str] = set()
    rounds = 0
    stopped = None

    for page in range(1, settings.max_rounds + 1):
        unsure = [qid for qid in questions if (always and page == 1) or confidence(answers[qid]) < settings.threshold]
        if not unsure:
            break
        if len(evidence) >= settings.max_evidence:
            stopped = "max_evidence"
            break

        queries = {qid: search_query(body["state"], questions[qid]) for qid in unsure}
        pages = await asyncio.gather(
            *(services.searxng.search(query, page, settings.language) for query in dict.fromkeys(queries.values()))
        )
        unresponsive.update(engine for p in pages for engine in p.unresponsive)
        fresh = new_evidence(pages, seen, room=settings.max_evidence - len(evidence))
        if not fresh:
            stopped = empty_round_reason(pages)
            break
        evidence += fresh

        retry = {
            **body,
            "state": with_evidence(body["state"], evidence, today),
            "questions": {qid: questions[qid] for qid in unsure},
        }
        try:
            response = await services.kev.systemone(retry, headers)
        except KevError as e:
            log.warning("Kev refused the request with search results (%s): %s", e.status, e.body)
            stopped = f"kev_error_{e.status}"
            break

        rounds = page
        answers.update(response["answers"])
        for key, value in (response.get("usage") or {}).items():
            usage[key] = usage.get(key, 0) + value
        for qid in unsure:
            reports[qid].searched = True
            reports[qid].rounds = page
            reports[qid].query = queries[qid]

    for qid, report in reports.items():
        final = confidence(answers[qid])
        report.needs_review = final < settings.threshold
        report.confidence = round(final, 4)
        report.initial_confidence = round(report.initial_confidence, 4)

    return {
        "model": first.get("model", body.get("model", "kev-latest")),
        "answers": {qid: answers[qid] for qid in questions},
        "usage": usage,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "search": {
            "threshold": settings.threshold,
            "rounds": rounds,
            "stopped": stopped,
            "questions": {qid: asdict(report) for qid, report in reports.items()},
            "evidence": [asdict(e) for e in evidence],
            "unresponsive_engines": sorted(unresponsive),
        },
    }
