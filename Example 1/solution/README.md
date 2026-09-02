# FastAPI Rate Limiting Demo

This FastAPI API applies a per-client fixed-window rate limit to API requests.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `GET /hello` returns `{"message":"Hello, world!"}`.
- API clients can make five requests per 60-second window. The sixth request returns `429` with `Retry-After` and `X-RateLimit-*` headers.
- `/health` is excluded from rate limiting for liveness checks.

## Prerequisites

- Python 3.12 or newer
- Bash
- `curl` with support for `--fail-with-body`
- Docker for the container flow (optional when running local Uvicorn)

## Local Setup

Run these commands with `base application` as the working directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app:app --reload
```

The development server listens at `http://127.0.0.1:8000` by default.

## Docker

From the repository root:

```bash
docker build -t fastapi-rate-limit-demo "base application"
docker run --rm --name fastapi-rate-limit-demo -p 8000:8000 fastapi-rate-limit-demo
```

## Baseline Demo

Start either the local Uvicorn server or the Docker container before running the demo. From `base application/`, start local Uvicorn with:

```bash
python -m uvicorn app:app --reload
```

Alternatively, start the Docker container using the commands in the [Docker](#docker) section. In another terminal, from the repository root, run the demo script:

```bash
"base application/scripts/demo.sh"
```

To use another URL, pass it as the first argument:

```bash
"base application/scripts/demo.sh" http://127.0.0.1:8001
```

The demo prints the `/health` JSON response, then makes six repeated `GET /hello` requests. It displays five `200` responses followed by `429` when the per-client limit is reached.
