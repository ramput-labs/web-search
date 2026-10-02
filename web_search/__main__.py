import logging
from pathlib import Path

import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level.upper(), format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    uvicorn.run(
        "web_search.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.reload,
        reload_dirs=[str(Path(__file__).parent)] if settings.reload else None,
        workers=None if settings.reload else settings.workers,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
