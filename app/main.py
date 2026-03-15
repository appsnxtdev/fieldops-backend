import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.core.config import get_settings
from app.core.errors import DEFAULT_MESSAGES, get_user_message
from app.modules.attendance import routes as attendance_routes
from app.modules.constants import routes as constants_routes
from app.modules.dashboard import routes as dashboard_routes
from app.modules.daily_reports import routes as daily_reports_routes
from app.modules.expense import routes as expense_routes
from app.modules.health import routes as health_routes
from app.modules.labour import labour_types_routes as labour_types_routes
from app.modules.labour import routes as labour_routes
from app.modules.master_materials import routes as master_materials_routes
from app.modules.materials import routes as materials_routes
from app.modules.projects import routes as projects_routes
from app.modules.storage import routes as storage_routes
from app.modules.tasks import routes as tasks_routes
from app.modules.tenant_members import routes as tenant_members_routes
from app.modules.tenants import routes as tenants_routes
from app.modules.users import routes as users_routes

logger = logging.getLogger(__name__)


def _sanitize_for_json(obj):
    """Replace bytes in validation errors so JSONResponse doesn't raise UnicodeDecodeError."""
    if isinstance(obj, bytes):
        return "<binary>"
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


_settings = get_settings()
logging.basicConfig(
    level=getattr(logging, _settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s %(name)s %(message)s",
)

_disable_docs = _settings.ENV == "production"
app = FastAPI(
    title="FieldOps API",
    version="0.1.0",
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)
_settings = get_settings()
logging.basicConfig(
    level=getattr(logging, _settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s %(name)s %(message)s",
)

_disable_docs = _settings.ENV == "production"
app = FastAPI(
    title="FieldOps API",
    version="0.1.0",
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized = _sanitize_for_json(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "detail": sanitized,
            "message": DEFAULT_MESSAGES[422],
        },
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    msg, code = get_user_message(exc.detail, exc.status_code)
    body = {"detail": exc.detail, "message": msg}
    if code:
        body["code"] = code
    logger.info("HTTP %s: %s", exc.status_code, code or msg)
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": DEFAULT_MESSAGES[500],
            "code": "INTERNAL_ERROR",
        },
    )


@app.on_event("startup")
def validate_env_on_startup():
    if _settings.ENV == "production":
        if not _settings.SUPABASE_URL or not _settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production")


_origins = [o.strip() for o in _settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router, prefix="/health", tags=["health"])
app.include_router(dashboard_routes.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(users_routes.router, prefix="/api/v1/users", tags=["users"])
app.include_router(tenants_routes.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(tenant_members_routes.router, prefix="/api/v1/tenant-members", tags=["tenant-members"])
app.include_router(projects_routes.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(attendance_routes.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(tasks_routes.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(daily_reports_routes.router, prefix="/api/v1/daily-reports", tags=["daily-reports"])
app.include_router(materials_routes.router, prefix="/api/v1/materials", tags=["materials"])
app.include_router(master_materials_routes.router, prefix="/api/v1/master-materials", tags=["master-materials"])
app.include_router(constants_routes.router, prefix="/api/v1/constants", tags=["constants"])
app.include_router(expense_routes.router, prefix="/api/v1/expense", tags=["expense"])
app.include_router(labour_routes.router, prefix="/api/v1/labour", tags=["labour"])
app.include_router(labour_types_routes.router, prefix="/api/v1/labour-types", tags=["labour-types"])
app.include_router(storage_routes.router, prefix="/api/v1/storage", tags=["storage"])
