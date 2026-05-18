from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.ratelimit import limiter, rate_limit_handler
from app.routers import query, schema


def create_app() -> FastAPI:
    app = FastAPI(title="Querymancer", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Per-IP rate limiting on /query. The limiter object is shared with the
    # query router, which decorates the endpoints; the app only needs the
    # state reference and the 429 handler. See app/core/ratelimit.py.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(query.router)
    app.include_router(schema.router)
    return app


app = create_app()
