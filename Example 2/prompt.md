# Example 2

## Creating the spec

Credits Used: 1.3 AIC (Luna)

```
Create a specification for adding a rate limiting to the API in `./base application` that include both the `/health` and `/hello` endpoints. Should allow for 20 requests before being rate limited. Use Spec-Driven Development best practices
```

## Applying the spec

Credits Used: 3 AIC (Luna)

```
Using this specification, `./docs/rate-limiting-spec.md`, add rate limiting to the API
```

## Outcome

The specification showed ALL API endpoints should be rate limited, and specified 20 before it begins to rate limit. This is higher than the in Example 1. Example 1 also only did `/hello` endpoint, not `/health`.

This specification can also be used as reference in the future of what the behavior is, and what changes were performed.