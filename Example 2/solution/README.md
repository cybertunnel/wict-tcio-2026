# FastAPI Rate Limiting Demo

This FastAPI demo applies a process-local rate limit to its public endpoints.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `GET /hello` returns `{"message":"Hello, world!"}`.

Each client IP may make 20 accepted requests to `/health` and `/hello` combined
within a rolling 60-second window. The 21st request returns HTTP `429` with a
JSON `{"detail":"Rate limit exceeded"}` body and a `Retry-After` header. The
client IP comes from the ASGI connection; forwarded headers are not trusted.

The limiter stores timestamps in process memory. State is cleared on restart,
and each worker or replica has an independent limit. Use a shared store such
as Redis before running this policy across multiple workers or replicas. When
the ASGI client address is unavailable, requests use one shared fallback bucket
for the process.

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

## Demo

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

The demo prints the `/health` and `/hello` JSON responses, then makes five repeated `GET /hello` requests and displays their HTTP status codes. These requests are below the active limit and should each return `200`.
