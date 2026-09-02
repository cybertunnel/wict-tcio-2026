from concurrent.futures import ThreadPoolExecutor
from time import monotonic

from fastapi.testclient import TestClient

from app import RATE_LIMIT, RATE_WINDOW_SECONDS, RateLimiter, app, rate_limiter


client = TestClient(app)


def setup_function() -> None:
    rate_limiter.reset()
    rate_limiter.clock = monotonic


def test_health_returns_ok_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello_returns_greeting() -> None:
    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_mixed_endpoints_allow_twenty_requests() -> None:
    responses = [
        client.get("/health" if index % 2 else "/hello")
        for index in range(RATE_LIMIT)
    ]

    assert all(response.status_code == 200 for response in responses)


def test_twenty_first_request_returns_rate_limit_response() -> None:
    for _ in range(RATE_LIMIT):
        assert client.get("/hello").status_code == 200

    response = client.get("/health")

    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}
    assert response.headers["Retry-After"].isdigit()


def test_forwarded_for_header_does_not_change_client_identity() -> None:
    for _ in range(RATE_LIMIT):
        assert client.get("/hello", headers={"X-Forwarded-For": "198.51.100.99"}).status_code == 200

    response = client.get("/hello", headers={"X-Forwarded-For": "203.0.113.99"})

    assert response.status_code == 429


def test_rejected_requests_do_not_consume_allowance() -> None:
    clock = [0.0]
    rate_limiter.clock = lambda: clock[0]
    for _ in range(RATE_LIMIT):
        assert client.get("/hello").status_code == 200

    assert client.get("/hello").status_code == 429
    clock[0] = RATE_WINDOW_SECONDS
    assert client.get("/hello").status_code == 200


def test_expired_state_is_removed() -> None:
    clock = [0.0]
    limiter = RateLimiter(clock=lambda: clock[0])
    limiter.allow("client")

    clock[0] = RATE_WINDOW_SECONDS
    limiter.remove_expired()

    assert not limiter._requests


def test_different_client_ips_have_independent_allowances() -> None:
    limiter = RateLimiter()

    for _ in range(RATE_LIMIT):
        assert limiter.allow("198.51.100.1")[0]
    assert not limiter.allow("198.51.100.1")[0]
    assert limiter.allow("198.51.100.2")[0]


def test_concurrent_requests_allow_at_most_twenty() -> None:
    limiter = RateLimiter()
    with ThreadPoolExecutor(max_workers=40) as executor:
        results = list(executor.map(lambda _: limiter.allow("client")[0], range(40)))

    assert sum(results) == RATE_LIMIT
