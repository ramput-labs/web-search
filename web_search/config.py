import os
from dataclasses import dataclass


def _list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8009
    log_level: str = "info"
    reload: bool = False
    workers: int = 1
    cors_origins: tuple[str, ...] = ()
    kev_url: str = "http://localhost:8010"
    kev_timeout: float = 120.0
    searxng_url: str = "http://localhost:8888"
    threshold: float = 0.5
    max_rounds: int = 2
    results_per_query: int = 5
    max_evidence: int = 10
    snippet_chars: int = 500
    language: str = "auto"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        default = cls()
        return cls(
            host=env.get("HOST", default.host),
            port=int(env.get("PORT", default.port)),
            log_level=env.get("LOG_LEVEL", default.log_level).lower(),
            reload=env.get("RELOAD", "").lower() in {"1", "true", "yes"},
            workers=int(env.get("WORKERS", default.workers)),
            cors_origins=_list(env.get("CORS_ORIGINS", "")),
            kev_url=env.get("KEV_URL", default.kev_url).rstrip("/"),
            kev_timeout=float(env.get("KEV_TIMEOUT", default.kev_timeout)),
            searxng_url=env.get("SEARXNG_URL", default.searxng_url).rstrip("/"),
            threshold=float(env.get("SEARCH_THRESHOLD", default.threshold)),
            max_rounds=int(env.get("SEARCH_MAX_ROUNDS", default.max_rounds)),
            results_per_query=int(env.get("SEARCH_RESULTS", default.results_per_query)),
            max_evidence=int(env.get("SEARCH_MAX_EVIDENCE", default.max_evidence)),
            snippet_chars=int(env.get("SEARCH_SNIPPET_CHARS", default.snippet_chars)),
            language=env.get("SEARCH_LANGUAGE", default.language),
        )
