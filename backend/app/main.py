from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import query, schema


def create_app() -> FastAPI:
    app = FastAPI(title="Querymancer", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(query.router)
    app.include_router(schema.router)
    return app


app = create_app()
