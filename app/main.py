import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from py_eureka_client.eureka_client import EurekaClient

from app.api.routes import health, reports
from app.database import Base, make_database
from app.cache import JsonCache, make_redis
from app.models_db import ReportRow
from app.repositories.report_repository_sql import ReportRepositorySql
from app.services.report_service import ReportService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db_url = getattr(app.state, "database_url", None) or os.getenv("DATABASE_URL", "sqlite:///./app.db")
    engine, sessions = make_database(db_url)
    Base.metadata.create_all(engine)

    redis_client = getattr(app.state, "redis_client", None)
    client = None
    
    eureka_client = getattr(app.state, "eureka_client", None)
    if eureka_client is None:
        eureka_client = EurekaClient(
            eureka_server=os.getenv("EUREKA_SERVER_URL", "http://127.0.0.1:8761"),
            eureka_context="/eureka",
            app_name=os.getenv("SERVICE_NAME", "REPORT-SERVICE"),
            instance_ip=os.getenv("INSTANCE_IP", "127.0.0.1"),
            instance_host=os.getenv("INSTANCE_HOST", "localhost"),
            instance_port=int(os.getenv("SERVICE_PORT", "8101")),
            strict_service_error_policy=False,
        )

    try:
        client = redis_client if redis_client is not None else make_redis(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        
        app.state.engine = engine
        app.state.redis = client
        app.state.eureka_client = eureka_client
        
        repo = ReportRepositorySql(sessions)
        app.state.report_repository = repo
        app.state.service = ReportService(repo)
        
        app.state.cache = JsonCache(
            client,
            prefix=os.getenv("CACHE_PREFIX", "lab2:report-service"),
            ttl=int(os.getenv("CACHE_TTL_SECONDS", "60")),
            resource_name="report",
        )
        
        await eureka_client.start()
        yield
    finally:
        try:
            if eureka_client is not None:
                await eureka_client.stop()
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                engine.dispose()


def create_app(database_url: str | None = None, redis_client=None, eureka_client=None) -> FastAPI:
    app = FastAPI(
        title="IT Report Service",
        description="A small IT reporting service with persistent SQLite storage, Redis cache-aside and Eureka discovery.",
        lifespan=lifespan,
    )
    app.state.database_url = database_url
    app.state.redis_client = redis_client
    app.state.eureka_client = eureka_client

    app.include_router(health.router)
    app.include_router(reports.router)
    return app


app = create_app()