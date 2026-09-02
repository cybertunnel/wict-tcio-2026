import pytest
from fastapi.testclient import TestClient

from app import RATE_LIMIT, app, limiter


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    limiter.clear()


def test_health_returns_ok_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello_returns_greeting() -> None:
    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_hello_is_rate_limited_per_client() -> None:
    responses = [client.get("/hello") for _ in range(RATE_LIMIT + 1)]

    assert [response.status_code for response in responses] == [200] * RATE_LIMIT + [429]
    assert responses[-1].json() == {"detail": "Rate limit exceeded"}
    assert responses[-1].headers["X-RateLimit-Limit"] == str(RATE_LIMIT)
    assert responses[-1].headers["X-RateLimit-Remaining"] == "0"
    assert int(responses[-1].headers["Retry-After"]) > 0


def test_health_is_not_rate_limited() -> None:
    responses = [client.get("/health") for _ in range(RATE_LIMIT + 1)]

    assert all(response.status_code == 200 for response in responses)
