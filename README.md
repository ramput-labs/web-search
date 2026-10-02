# web-search

Kev with web search.

[Kev](https://github.com/jaredpalmer/kev) answers questions from what is in the state you send it, and nothing
else. Ask it "When was OpenAI Dots announced?" and it can only guess: 2024, at confidence 0.27.

web-search sits in front of Kev on Kev's usual port. You send the same requests as before. When Kev's confidence in
an answer is below 0.5, web-search searches the web through [SearXNG](https://docs.searxng.org), adds the results to
the state and asks Kev again. The same question then comes back as 2026, at confidence 0.97.

```
client ──> web-search :8009 ──> Kev :8010
                │
                └──> SearXNG :8888  (only for answers below the threshold)
```

## Requirements

- Python 3.12+ for the server
- [Bun](https://bun.sh) and Node 22+ for the UI
- Kev, running on port 8010
- SearXNG on port 8888, with JSON output enabled in its `settings.yml`:

  ```yaml
  search:
    formats: [html, json]
  ```

  Without it SearXNG answers 403 and every search fails. Google, Yandex and DuckDuckGo web are the most reliable
  engines.

## Getting Started

Start Kev on port 8010 (in the kev repo):

```bash
uv run --extra serve python -m kev.serve --run jaredpalmer/kev-4b --port 8010
```

Then, in this repo:

```bash
make install   # .venv from requirements.txt, and the UI's packages
make env       # optional: .env from .env.example
make dev       # server on :8009 and UI on :5173, both reloading on change
```

Without make: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then
`.venv/bin/python -m web_search`.

Open http://localhost:5173.

Send a request to the server directly:

```bash
curl -s localhost:8009/v1/systemone -H 'content-type: application/json' -d '{
  "state": "When was OpenAI Dots announced?",
  "questions": {
    "announcement_date": {
      "type": "choice",
      "instructions": "Which date range corresponds to when OpenAI announced Dots?",
      "criteria": {
        "2024": "During 2024",
        "2026": "During 2026",
        "before_2024": "Before 2024"
      }
    }
  }
}'
```

The TypeSafe SDK works unchanged with `base_url="http://127.0.0.1:8009"`. Every other Kev route (`/v1/models`,
`/v1/systemone/permute`, `/v1/systemone/separate`) is forwarded to Kev as it is.

### Make targets

| Target | What it does |
| --- | --- |
| `make dev` | Server and UI with live reload; `dev-server` and `dev-ui` run one of them |
| `make build` | UI bundle into `ui/build`; the server runs from source |
| `make start` | Server and built UI in production mode; `server` and `ui` run one of them |
| `make test` | Server tests (pytest) and UI tests (bun test) |
| `make lint` / `make format` | ruff for the server, prettier and eslint for the UI |
| `make check` | Lint, test and type-check the UI |
| `make clean` | Build output and caches; `distclean` also removes `.venv` and `node_modules` |

## How It Works

1. Kev answers the request as sent. If every answer's confidence is at or above the threshold, that is the response.
2. Each question below the threshold is searched on SearXNG. The query is the state followed by the question when
   the state is short (up to 200 characters), and the question alone when it is long.
3. The results (title, URL, snippet) and today's date are added to the state, and Kev is asked again, only the
   unsure questions. Answers that were already confident are kept.
4. A question that is still unsure gets the next page of results, up to `SEARCH_MAX_ROUNDS` rounds. After that it is
   returned with `needs_review: true`.

Confidence is Kev's `confidence` for choice and score answers. A noul answer has only a probability `p`, so its
confidence is `|2p - 1|`: 0 at p = 0.5, 1 at p = 0 or 1.

## Response

Kev's response (`model`, `answers`, `usage` summed over the Kev calls, `latency_ms`), plus a `search` object that
shows what happened. The Dots request above, shortened:

```json
{
  "model": "kev-latest",
  "answers": {
    "announcement_date": {"type": "choice", "choice": "2026", "confidence": 0.97, "probabilities": {"...": 0.0}}
  },
  "usage": {"input_tokens": 683, "output_tokens": "..."},
  "latency_ms": 1712.5,
  "search": {
    "threshold": 0.5,
    "rounds": 1,
    "stopped": null,
    "questions": {
      "announcement_date": {
        "initial_confidence": 0.27,
        "confidence": 0.97,
        "searched": true,
        "rounds": 1,
        "query": "When was OpenAI Dots announced? Which date range corresponds to when OpenAI announced Dots?",
        "needs_review": false
      }
    },
    "evidence": [
      {"title": "OpenAI launches Dots, its bubbly agentic avatar | TechCrunch", "url": "https://techcrunch.com/...",
       "content": "At OpenAI's DevDay event on Tuesday, ...", "query": "..."}
    ],
    "unresponsive_engines": []
  }
}
```

| `stopped` | Meaning |
| --- | --- |
| `null` | Every question became confident, or all rounds ran |
| `no_new_results` | SearXNG answered, but with nothing that was not already used |
| `search_unavailable` | SearXNG was down, or every engine failed; `unresponsive_engines` says which and why |
| `max_evidence` | `SEARCH_MAX_EVIDENCE` results are already in the state |
| `kev_error_<status>` | Kev refused the request with the results (for example 422, state too long); earlier answers are kept |

Errors: Kev's errors on the first call are returned unchanged, and Kev being unreachable is a 502. A search failure
never fails a request; the question is returned with `needs_review: true`.

## Chat UI

A SvelteKit chat in `ui/`. You type a **question** and its **options** (press Enter after each; leave them empty
for a yes / no question), and Kev picks one. The question is sent as the state, with one question whose criteria are
your options. Answers show the chosen option and its confidence: green for high (80% and over), amber for medium, red
for below the search threshold. Searched answers list their sources.

The **Search** button sets the `x-web-search` header:

| `x-web-search` | Behaviour |
| --- | --- |
| `auto` (or no header) | Search only the questions below the threshold, as described above |
| `always` | Search every question in the first round, however sure Kev is; later rounds only the unsure ones. The UI sends this when Search is on |
| `off` | Kev's answer, without searching. The UI sends this when Search is off |

The browser only talks to the UI: `/api/health` and `/api/v1/systemone` are forwarded to the server
at `WEB_SEARCH_URL`, so the server needs no CORS. Chats are kept in the browser's localStorage. The UI is served by
Node (adapter-node) with a strict Content Security Policy and security headers, and uses the self-hosted Chirp font.

## Configuration

All settings are environment variables. The Makefile also reads them from `.env` (see `.env.example`).

| Variable | Default | Description |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Address the server listens on |
| `PORT` | `8009` | Port the server listens on |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` |
| `WORKERS` | `1` | Server worker processes |
| `CORS_ORIGINS` | | Comma-separated origins allowed to call the server from a browser |
| `UI_HOST` / `UI_PORT` | `127.0.0.1` / `5173` | Where the UI listens (Makefile) |
| `KEV_URL` | `http://localhost:8010` | Kev |
| `KEV_TIMEOUT` | `120` | Seconds to wait for Kev |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG |
| `SEARCH_THRESHOLD` | `0.5` | Answers below this confidence are searched |
| `SEARCH_MAX_ROUNDS` | `2` | Search rounds per request at most |
| `SEARCH_RESULTS` | `5` | Results per query per round |
| `SEARCH_MAX_EVIDENCE` | `10` | Results added to the state at most |
| `SEARCH_SNIPPET_CHARS` | `500` | Characters kept from each result's snippet |
| `SEARCH_LANGUAGE` | `auto` | SearXNG search language (`auto`, `en`, `ru`, ...) |

## Project Structure

The Python server is the repo root; the web search chat interface is `ui/`.

```
Makefile              make dev, build, start, test, ...
.env.example          every setting, with its default
requirements.txt      server dependencies, with pytest and ruff
ruff.toml             Python lint settings
web_search/           FastAPI server
├── __main__.py       entry point: python -m web_search
├── app.py            POST /v1/systemone, GET /health; every other route is forwarded to Kev
├── pipeline.py       ask Kev, search when unsure, ask again
├── kev.py            Kev client
├── searxng.py        SearXNG client
└── config.py         settings from environment variables
tests/                server tests: a fake Kev and SearXNG, no network needed
ui/                   SvelteKit chat interface
├── src/routes/
│   ├── +page.svelte              the chat
│   └── api/[...path]/+server.ts  forwards /api/* to the server
├── src/lib/
│   ├── app.svelte.ts  chats and settings
│   ├── api.ts         calls to the server
│   ├── fragment.ts    source links that highlight the passage on the page (+ tests)
│   ├── theme.svelte.ts light, dark or system theme
│   ├── presets.ts     example questions
│   └── components/    composer, replies, answers, sources, sidebar, theme select
├── src/hooks.server.ts  security headers
└── src/assets/fonts/    Chirp
```

## Testing

```bash
make test    # server and UI tests
make check   # plus lint and the UI type check
```

The tests need neither Kev nor SearXNG: both are replaced by a fake network.

## Limitations

- Search helps with facts that are missing from the state. A question about the text itself (tone, urgency) that
  comes back unsure is searched too, and web results can only distract from the text.
- Low confidence can mean the question is ambiguous rather than that facts are missing. That is what `needs_review`
  is for.
- The default query works when the state names the subject. "Какой MCC-код у магазина «Глобус»?" finds MCC-code
  directories rather than the store.
- SearXNG scrapes the search engines. A burst of queries from one IP gets engines blocked for minutes
  (`search_unavailable`).
- Search results are untrusted text in Kev's state; a web page can be written to steer the answer.
- 0.5 is a starting point. Choose the threshold from a few hundred labelled requests of your own.
