from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic
from collections.abc import Callable

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


RATE_LIMIT = 20
RATE_WINDOW_SECONDS = 60.0
PROTECTED_ENDPOINTS = {("GET", "/health"), ("GET", "/hello")}
FALLBACK_CLIENT_KEY = "unknown-client"


class RateLimiter:
    def __init__(
        self,
        limit: int = RATE_LIMIT,
        window_seconds: float = RATE_WINDOW_SECONDS,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_key: str) -> tuple[bool, int]:
        now = self.clock()
        with self._lock:
            self._remove_expired(now)
            requests = self._requests[client_key]

            if len(requests) >= self.limit:
                retry_after = max(0, ceil(self.window_seconds - (now - requests[0])))
                return False, retry_after

            requests.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()

    def remove_expired(self) -> None:
        with self._lock:
            self._remove_expired(self.clock())

    def _remove_expired(self, now: float) -> None:
        expired_clients = []
        for client_key, requests in self._requests.items():
            while requests and now - requests[0] >= self.window_seconds:
                requests.popleft()
            if not requests:
                expired_clients.append(client_key)
        for client_key in expired_clients:
            del self._requests[client_key]


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, limiter: RateLimiter) -> None:
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        method = scope.get("method")
        path = scope.get("path")
        if scope["type"] != "http" or (method, path) not in PROTECTED_ENDPOINTS:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_key = client[0] if client else FALLBACK_CLIENT_KEY
        allowed, retry_after = self.limiter.allow(client_key)
        if not allowed:
            response = JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


app = FastAPI(title="Rate Limiting Demo API")
rate_limiter = RateLimiter()
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, world!"}
