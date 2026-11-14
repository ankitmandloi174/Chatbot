"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import conversations, datasets
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import create_db_engine, create_session_factory, init_db
from app.services.retrieval.vector_store import ColumnVectorStore

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Passing `settings` makes it easy to test in isolation."""
    settings = settings or Settings()
    configure_logging(settings.log_level)
    settings.ensure_directories()

    engine = create_db_engine(settings.database_url)
    init_db(engine)

    app = FastAPI(title="DataPilot", version="1.0.0")
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)
    app.state.vector_store = ColumnVectorStore(settings.chroma_dir)
    app.state.llm = None  # built lazily on first chat request

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(datasets.router)
    app.include_router(conversations.router)

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "llm_provider": settings.llm_provider}

    return app
