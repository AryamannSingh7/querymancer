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

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger("querymancer.ratelimit")

# 10 requests / minute / IP. The 11th request inside the window is rejected
# with a 429 — far above any realistic human pace, low enough to stop a
# burst from draining the daily LLM budget.
RATE_LIMIT = "10/minute"

# Candidate client-IP headers, in priority order. HF Spaces fronts the
# container with a pool of internal router pods, so `request.client.host`
# (what slowapi's `get_remote_address` returns) is a rotating 10.16.x.x
# proxy address — useless as a limiter key. The real client IP is in a
# forwarded header; which one is proxy-specific, so we check the common set.
_FORWARDED_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "true-client-ip",
    "cf-connecting-ip",
)


def _client_ip(request: Request) -> str:
    """Resolve the real client IP behind a reverse proxy for the limiter key.

    Walks `_FORWARDED_HEADERS` and returns the first match's left-most entry.
    That value is client-supplied and therefore spoofable — an accepted
    tradeoff for a free-tier demo whose limiter stops accidental hammering,
    not a determined adversary. Falls back to `get_remote_address` (local
    dev, the test suite — neither sends a forwarded header).

    Logs the resolution once per request so the deployed environment's
    actual header set is visible in the container logs.
    """
    host = request.client.host if request.client else None
    for header in _FORWARDED_HEADERS:
        value = request.headers.get(header)
        if value:
            ip = value.split(",")[0].strip()
            logger.info("ratelimit key via %s: %s (client.host=%s)", header, ip, host)
            return ip
    fallback = get_remote_address(request)
    logger.info(
        "ratelimit key: no forwarded header (client.host=%s) -> %s; headers=%s",
        host, fallback, sorted(request.headers.keys()),
    )
    return fallback


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
