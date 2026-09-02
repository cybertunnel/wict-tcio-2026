from collections import defaultdict
from math import ceil
from threading import Lock
from time import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


RATE_LIMIT = 5
RATE_LIMIT_WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: defaultdict[str, tuple[float, int]] = defaultdict(
            lambda: (0.0, 0)
        )
        self._lock = Lock()

    def check(self, client_id: str) -> tuple[bool, int, int]:
        now = time()
        with self._lock:
            window_start, request_count = self._requests[client_id]
            if now - window_start >= self.window_seconds:
                window_start, request_count = now, 0

            request_count += 1
            self._requests[client_id] = (window_start, request_count)
            remaining = max(0, self.limit - request_count)
            reset_at = ceil(window_start + self.window_seconds)

        return request_count <= self.limit, remaining, reset_at

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


app = FastAPI(title="Rate Limiting Demo API")
limiter = RateLimiter(RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_id = request.client.host if request.client else "unknown"
    allowed, remaining, reset_at = limiter.check(client_id)
    headers = {
        "X-RateLimit-Limit": str(limiter.limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_at),
    }
    if not allowed:
        headers["Retry-After"] = str(max(1, reset_at - ceil(time())))
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers=headers,
        )

    response = await call_next(request)
    for name, value in headers.items():
        response.headers[name] = value
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, world!"}
