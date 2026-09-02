# FastAPI Rate Limiting Demo

This is an intentionally unthrottled FastAPI baseline. It provides the API that a later demo change will modify by adding rate limiting.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `GET /hello` returns `{"message":"Hello, world!"}`.

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

The demo prints the `/health` and `/hello` JSON responses, then makes five repeated `GET /hello` requests and displays their HTTP status codes. It does not assert a rate-limit policy; baseline behavior is expected to print `200` for each repeated request because this baseline does not include rate limiting. A later change can add middleware and focused assertions for `429` responses and rate-limit headers.
