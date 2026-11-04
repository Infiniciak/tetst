import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response

from app.api.routes import health, reports
from app.database import Base, make_database
from app.cache import JsonCache, make_redis
from app.models_db import ReportRow
from app.repositories.report_repository_sql import ReportRepositorySql
from app.services.report_service import ReportService, ReportNotFoundError, DuplicateReportError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db_url = getattr(app.state, "database_url", None) or os.getenv("DATABASE_URL", "sqlite:///./app.db")
    engine, sessions = make_database(db_url)
    Base.metadata.create_all(engine)

    redis_client = getattr(app.state, "redis_client", None)
    client = None
    try:
        client = redis_client if redis_client is not None else make_redis(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        
        app.state.engine = engine
        app.state.redis = client
        
        repo = ReportRepositorySql(sessions)
        app.state.report_repository = repo
        app.state.service = ReportService(repo)
        
        app.state.cache = JsonCache(
            client,
            prefix=os.getenv("CACHE_PREFIX", "lab2:131534:report-service"),
            ttl=int(os.getenv("CACHE_TTL_SECONDS", "60")),
            resource_name="report",
        )
        yield
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            engine.dispose()


def create_app(database_url: str | None = None, redis_client=None) -> FastAPI:
    app = FastAPI(
        title="IT Report Service",
        description="A small IT reporting service with persistent SQLite storage and Redis cache-aside.",
        lifespan=lifespan,
    )
    app.state.database_url = database_url
    app.state.redis_client = redis_client

    app.include_router(health.router)
    app.include_router(reports.router)
    return app


app = create_app()