import logging
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    content: str
    query: str

    def line(self) -> str:
        url = f" ({self.url})" if self.url else ""
        return f"{self.title}{url}: {self.content}"


@dataclass
class SearchPage:
    results: list[Evidence] = field(default_factory=list)
    unresponsive: list[str] = field(default_factory=list)
    failed: bool = False


class SearxngClient:
    def __init__(self, http: httpx.AsyncClient, url: str, results_per_query: int, snippet_chars: int):
        self.http = http
        self.url = url
        self.results_per_query = results_per_query
        self.snippet_chars = snippet_chars

    async def search(self, query: str, page: int, language: str) -> SearchPage:
        """Never raises: an outage is a failed, empty page, and the question then needs review."""
        params = {"q": query, "format": "json", "language": language, "pageno": page}
        try:
            response = await self.http.get(f"{self.url}/search", params=params, timeout=20)
            if response.status_code == 403:
                log.warning("SearXNG refused format=json: enable json under search.formats in its settings.yml")
                return SearchPage(failed=True)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("search failed for %r: %r", query, e)
            return SearchPage(failed=True)

        unresponsive = [": ".join(map(str, engine)) for engine in data.get("unresponsive_engines") or []]
        results = [self._evidence(item, query) for item in data.get("results", [])[: self.results_per_query]]
        results = [r for r in results if r.title or r.content]
        if not results and unresponsive:
            log.warning("no results for %r; engines failing: %s", query, unresponsive)
        return SearchPage(results, unresponsive)

    def _evidence(self, item: dict, query: str) -> Evidence:
        return Evidence(
            title=(item.get("title") or "").strip(),
            url=item.get("url") or "",
            content=(item.get("content") or "").strip()[: self.snippet_chars],
            query=query,
        )
