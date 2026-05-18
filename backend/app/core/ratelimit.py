"""Per-IP rate limiting for the public /query endpoints.

The demo backend runs on a free-tier Gemini key with a 20-requests-per-day
cap. Without a limiter a single visitor refreshing the page — or a bot —
could burn the whole day's budget in under a minute. slowapi gives each
client IP a fixed-window quota.

The eval harness is unaffected: at the default concurrency of 1 it runs
latency-bound (~13s per /query → ~5 req/min), well under the limit.

Storage is in-memory — no Redis — which is correct for the single HF Space
instance and keeps the zero-budget constraint intact.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# 10 requests / minute / IP. The 11th request inside the window is rejected
# with a 429 — far above any realistic human pace, low enough to stop a
# burst from draining the daily LLM budget.
RATE_LIMIT = "10/minute"


def _client_ip(request: Request) -> str:
    """Resolve the real client IP behind Hugging Face Spaces' reverse proxy.

    HF fronts the container with a pool of internal router pods, so
    `request.client.host` (what slowapi's `get_remote_address` returns) is a
    rotating ``10.16.x.x`` proxy address — every request looks like a fresh
    client and the limiter never accumulates. The real client IP is the
    left-most entry of the ``X-Forwarded-For`` header.

    ``XFF[0]`` is client-supplied and therefore spoofable; that is an accepted
    tradeoff for a free-tier demo whose limiter exists to stop accidental
    hammering, not a determined adversary. Falls back to `get_remote_address`
    when the header is absent (local dev, the test suite).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


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
