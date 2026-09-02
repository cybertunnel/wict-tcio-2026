# Rate Limiting for the Demo API

- **Status:** Draft
- **Owner:** API maintainers
- **Target:** `base application`
- **Change type:** Behavior and middleware change

## 1. Purpose

Protect the API from excessive repeated requests while preserving the existing response behavior for normal traffic. The rate-limit policy applies consistently to both public endpoints:

- `GET /health`
- `GET /hello`

This document is the implementation contract for the change. Code and tests should be written against the requirements and acceptance criteria below.

## 2. Problem Statement

The current FastAPI application is intentionally unthrottled. A caller can issue unlimited requests to either endpoint, which makes the demo unsuitable for demonstrating basic API protection and allows one caller to consume disproportionate application capacity.

## 3. Goals and Non-Goals

### Goals

- Limit each client to 20 accepted requests in a rolling 60-second window.
- Count requests to `/health` and `/hello` in the same client bucket.
- Return a standards-compatible, inspectable response when the limit is exceeded.
- Keep endpoint business logic unchanged.
- Make the policy deterministic and testable without external services.

### Non-goals

- Authentication, authorization, quotas by user or API key, or billing limits.
- Distributed rate limiting across multiple application processes or hosts.
- Limiting unrelated paths such as `/docs`, `/openapi.json`, or future admin endpoints unless explicitly added to the policy.
- Retrying, queueing, or delaying requests after the limit is reached.

## 4. Rate-Limit Policy

| Property | Requirement |
|---|---|
| Scope | `GET /health` and `GET /hello` |
| Identity key | Client IP address from the ASGI request connection |
| Limit | 20 requests per client |
| Window | Rolling 60 seconds |
| Counting | Every request reaching the protected middleware, including requests that later return an endpoint error |
| Boundary | Requests 1 through 20 are allowed; request 21 is rejected if it falls within the rolling window |
| Recovery | A request is allowed again as older requests leave the 60-second window |
| Sharing | Both endpoints consume the same per-client allowance |
| Failure mode | Reject immediately; do not queue or sleep |

A rejected request must not increase the client's request count.

### Identity and proxy handling

The first implementation must use the client address exposed by the ASGI request (`request.client.host`). It must not trust `X-Forwarded-For` or other client-supplied forwarding headers unless trusted-proxy configuration is added as a separate change. When the client address is unavailable, the implementation must use a stable fallback key for that application process and document the operational consequence in logs or deployment documentation.

### Storage and process model

The initial implementation may use process-local in-memory state because this is a single-process demo application and no datastore dependency currently exists. The implementation must:

- avoid unbounded growth by removing expired entries;
- use a monotonic time source for window calculations;
- protect shared state when requests can execute concurrently;
- clear state when the application process restarts;
- document that multiple workers or replicas each have an independent limit.

A shared store such as Redis is out of scope for this change but is the required direction before deploying the policy across multiple workers or replicas.

## 5. HTTP Contract

### Allowed response

The existing endpoint contracts remain unchanged:

```http
GET /health

HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok"}
```

```http
GET /hello

HTTP/1.1 200 OK
Content-Type: application/json

{"message":"Hello, world!"}
```

### Rate-limited response

When a client exceeds the limit, return:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: <integer seconds>

{"detail":"Rate limit exceeded"}
```

Requirements for the rejection response:

- status code is exactly `429`;
- `Retry-After` is present and contains a non-negative integer number of seconds until the earliest request in the active window expires;
- response is JSON and contains the exact `detail` value above;
- endpoint handlers are not invoked for the rejected request;
- the response must not expose internal state, client identifiers, or stack traces.

The implementation may also return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers, but their semantics must be documented and tested together if added. They are not required for acceptance of this change.

## 6. Functional Requirements

- **FR-1:** The application shall apply the policy to `GET /health`.
- **FR-2:** The application shall apply the policy to `GET /hello`.
- **FR-3:** The application shall identify limits by client IP, not by endpoint, so requests to both endpoints share one allowance.
- **FR-4:** The application shall allow the first 20 requests from a client during a rolling 60-second window.
- **FR-5:** The application shall reject the 21st request in that window with the HTTP contract in Section 5.
- **FR-6:** The application shall allow requests again as the rolling window expires.
- **FR-7:** The application shall leave successful endpoint payloads unchanged.
- **FR-8:** The application shall not increment the counter for a request rejected by the limiter.
- **FR-9:** The implementation shall be safe under concurrent request handling.
- **FR-10:** The implementation shall remove expired per-client request state.
- **FR-11:** The implementation shall document the process-local limitation.

## 7. Design Constraints

- Implement the policy at middleware or an equivalent request-boundary abstraction so both endpoints cannot accidentally diverge.
- Keep `/health` and `/hello` handlers focused on their existing response payloads.
- Do not add endpoint-specific counters or duplicate limiter logic.
- Use the existing FastAPI and pytest toolchain unless a dependency is necessary and its operational tradeoff is documented.
- Preserve the current application entry point (`app:app`) and existing endpoint paths.

## 8. Test-First Plan

Add focused tests in `base application/tests/test_app.py` or a nearby test module. Tests must isolate limiter state per test, either by constructing a fresh application/client or by using an explicit reset fixture.

Required scenarios:

1. `/health` returns its existing `200` response.
2. `/hello` returns its existing `200` response.
3. Twenty requests from one client, including a mix of both endpoints, are allowed.
4. The 21st request from that client returns exactly `429` with the required JSON body and `Retry-After` header.
5. A different client IP has an independent allowance.
6. Requests to `/health` and `/hello` share one allowance.
7. After the oldest request leaves the rolling window, the client can make another request.
8. A rejected request does not consume another allowance.
9. Concurrent requests cannot allow more than 20 requests for one client within the window.
10. Expired client state is removed.
11. A client-supplied `X-Forwarded-For` header does not change the identity key under the default configuration.

Time-dependent tests should inject or control the clock rather than sleep. Tests must assert exact status codes, response bodies, and relevant headers.

## 9. Acceptance Criteria

The change is ready when all of the following are true:

- [ ] The implementation satisfies FR-1 through FR-11.
- [ ] All existing tests pass without changing their endpoint payload assertions.
- [ ] The required rate-limit scenarios pass reliably and independently.
- [ ] A manual or scripted request sequence demonstrates 20 allowed responses followed by `429` for each client IP.
- [ ] `Retry-After` is present and mathematically consistent with the rolling window.
- [ ] No rate-limit state is shared accidentally between test cases.
- [ ] README documentation describes the active policy, including the 60-second window and process-local limitation.
- [ ] The test suite passes with the documented local command: `python -m pytest -q`.
- [ ] Any newly added dependency is pinned or constrained consistently with the existing requirements file and explained in the change notes.

## 10. Operational and Security Considerations

- Rate limiting is a resource-protection control, not authentication or authorization.
- Client IPs are potentially identifying operational data. Do not include raw IP addresses in normal response bodies or error messages. If logging is added, follow the application's logging policy and minimize retention.
- Behind a reverse proxy, connection-level client IPs may represent the proxy unless trusted-proxy handling is configured. Do not enable forwarded-header trust without an explicit trusted-proxy boundary.
- In-memory state can be lost on restart and bypassed across replicas. This limitation must be visible in deployment documentation before production use.
- The limiter should fail closed for requests when its own state operation cannot be completed, unless the application owner explicitly approves a fail-open policy and its risk.

## 11. Implementation Decision Record

### Decision: rolling window

A rolling 60-second window is specified because it avoids the sharp reset burst of a fixed wall-clock minute while remaining understandable in a demo.

### Decision: client IP key

No authentication or API-key identity exists in the current application. The ASGI connection IP is therefore the only available server-observed identity that does not require trusting a caller-controlled header.

### Open decisions before implementation

- Whether to add optional `X-RateLimit-*` headers for client visibility.
- Whether the demo should expose a configurable limit/window through environment variables, or keep `20` and `60` as application constants.
- Whether deployment will run one worker only. More than one worker requires a shared limiter store for a meaningful global policy.

## 12. Traceability

| Requirement | Primary verification |
|---|---|
| FR-1, FR-2, FR-7 | Existing endpoint response tests |
| FR-3, FR-4, FR-5 | Mixed endpoint burst test |
| FR-6 | Controlled-clock expiry test |
| FR-8 | Repeated rejection test |
| FR-9 | Concurrent request test |
| FR-10 | State cleanup test |
| FR-11 | README or deployment documentation review |
