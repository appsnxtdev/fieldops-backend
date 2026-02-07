from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.modules.attendance import routes as attendance_routes
from app.modules.constants import routes as constants_routes
from app.modules.daily_reports import routes as daily_reports_routes
from app.modules.expense import routes as expense_routes
from app.modules.health import routes as health_routes
from app.modules.master_materials import routes as master_materials_routes
from app.modules.materials import routes as materials_routes
from app.modules.projects import routes as projects_routes
from app.modules.tasks import routes as tasks_routes
from app.modules.tenant_members import routes as tenant_members_routes
from app.modules.tenants import routes as tenants_routes
from app.modules.users import routes as users_routes

def _sanitize_for_json(obj):
    """Replace bytes in validation errors so JSONResponse doesn't raise UnicodeDecodeError."""
    if isinstance(obj, bytes):
        return "<binary>"
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


app = FastAPI(title="FieldOps API", version="0.1.0")


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _sanitize_for_json(exc.errors())},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router, prefix="/health", tags=["health"])
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
