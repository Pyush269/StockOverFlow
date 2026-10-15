import logging
from contextlib import asynccontextmanager

from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.exceptions import HTTPException

from .config import BACKEND_ROOT, Settings
from .db import build_engine, get_db
from .errors import DomainError
from .models import Product, StockMovement
from .routes import dashboard, movements, products

logger = logging.getLogger(__name__)


def error_response(status_code: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message, **extra}})


def create_app(settings: Settings | None = None, *, engine: Engine | None = None) -> FastAPI:
    settings = settings or Settings()
    owns_engine = engine is None
    database_engine = engine if engine is not None else build_engine(settings.database_url)
    expected_heads = set(ScriptDirectory(str(BACKEND_ROOT / "alembic")).get_heads())

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Schema creation belongs to Alembic, never API startup.
        try:
            yield
        finally:
            if owns_engine:
                database_engine.dispose()

    application = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    application.state.engine = database_engine
    application.state.session_factory = sessionmaker(bind=database_engine, expire_on_commit=False, autoflush=False)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware, allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"],
        )

    @application.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return error_response(exc.status_code, exc.code, exc.message)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(map(str, item["loc"])), "message": item["msg"], "type": item["type"]} for item in exc.errors()]
        return error_response(422, "validation_error", "Request validation failed", details=details)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(exc.status_code, "http_error", str(exc.detail))

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("Database request failed method=%s path=%s exception=%s", request.method, request.url.path, type(exc).__name__)
        return error_response(503, "database_unavailable", "Database operation could not be completed")

    @application.get("/", tags=["Operations"])
    def root():
        return {"service": settings.app_name, "version": "0.1.0", "docs": "/docs"}

    @application.get("/health", tags=["Operations"])
    def health():
        return {"status": "UP"}

    @application.get("/ready", tags=["Operations"], responses={503: {"description": "Database or schema not ready"}})
    def ready(db: Session = Depends(get_db)):
        try:
            actual_heads = set(db.scalars(text("SELECT version_num FROM alembic_version")))
            if actual_heads != expected_heads:
                return error_response(503, "schema_not_ready", "Database migrations are not current")
            # These selects validate table/column availability without scanning data.
            db.execute(select(Product).limit(1))
            db.execute(select(StockMovement).limit(1))
        except SQLAlchemyError:
            return error_response(503, "database_not_ready", "Database or schema is unavailable")
        return {"status": "READY"}

    application.include_router(products.router)
    application.include_router(movements.router)
    application.include_router(dashboard.router)
    Instrumentator(
        registry=CollectorRegistry(), excluded_handlers=["/health", "/ready", "/metrics"],
        should_ignore_untemplated=True,
    ).instrument(application).expose(application, endpoint="/metrics", include_in_schema=False)
    return application


app = create_app()
