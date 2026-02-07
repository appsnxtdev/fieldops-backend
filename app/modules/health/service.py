from app.modules.health.schemas import HealthResponse


def get_health() -> HealthResponse:
    return HealthResponse()
