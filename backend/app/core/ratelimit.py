"""Rate limiting for the public /query endpoints.

The demo backend runs on free-tier LLM keys (Gemini 20 requests/day, Groq
100K tokens/day). Without a limiter a single visitor refreshing the page —
or a bot — could drain the whole day's budget in under a minute. slowapi
enforces a fixed-window 10/minute quota.

**Keying.** Per-client-IP would be ideal, but Hugging Face Spaces routes the
container behind a pool of internal proxies and forwards no usable client-IP
header — `request.client.host` is only ever a rotating ``10.16.x.x`` address,
and `X-Forwarded-For` / `X-Real-IP` / etc. are absent. So the limiter degrades
to a single shared bucket: a **global** 10/minute cap. That still does the
job — it caps total burst load on the shared free-tier quota, which is the
limiter's whole purpose. On a platform that *does* expose the client IP via a
standard forwarded header, `_client_ip` keys per-IP automatically.

Storage is in-memory — no Redis — correct for the single HF Space instance
and keeps the zero-budget constraint intact.

The eval harness is unaffected: at the default concurrency of 1 it runs
latency-bound (~13s per /query → ~5 req/min), well under the limit.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

# 10 requests / minute. The 11th request inside the window is rejected with a
# 429 — far above any realistic human pace, low enough to stop a burst from
# draining the daily LLM budget.
RATE_LIMIT = "10/minute"

# Standard client-IP headers, in priority order. Used when the platform
# exposes the real client IP; HF Spaces does not (see module docstring).
_FORWARDED_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "true-client-ip",
    "cf-connecting-ip",
)

# Shared bucket used when no client IP is available — makes the limit global.
_SHARED_KEY = "querymancer-shared"


def _client_ip(request: Request) -> str:
    """Limiter key: the real client IP, or a shared global key as a fallback.

    Returns the left-most entry of the first present forwarded header. That
    value is client-supplied and spoofable — an accepted tradeoff for a
    free-tier demo whose limiter stops accidental hammering, not a determined
    adversary. When no forwarded header is present (HF Spaces, local dev, the
    test suite) every request maps to `_SHARED_KEY`, making the limit global.
    """
    for header in _FORWARDED_HEADERS:
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return _SHARED_KEY


limiter = Limiter(key_func=_client_ip)


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a 429 in the same {detail: {message, attempts, errors}} shape the
    other /query failure paths use, so the frontend can render it cleanly."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": {
                "message": (
                    "Too many requests — the public demo is rate-limited to keep "
                    "the shared free-tier quota fair. Wait a minute and try again."
                ),
                "attempts": 0,
                "errors": [f"rate limit exceeded: {exc.detail}"],
            }
        },
        headers={"Retry-After": "60"},
    )
