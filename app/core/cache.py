import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


# ── Key patterns ──────────────────────────────────────────────────────────────

class CacheKeys:
    @staticmethod
    def auth_user(token_hash: str) -> str:
        return f"au:{token_hash}"

    @staticmethod
    def tenant_member(tenant_id: str, user_id: str) -> str:
        return f"tm:{tenant_id}:{user_id}"

    @staticmethod
    def dashboard(tenant_id: str, user_id: str) -> str:
        return f"ds:{tenant_id}:{user_id}"

    @staticmethod
    def dashboard_period(tenant_id: str, user_id: str, from_date: str, to_date: str) -> str:
        return f"ds:p:{tenant_id}:{user_id}:{from_date}:{to_date}"

    @staticmethod
    def labour_trends(tenant_id: str, user_id: str, period_days: int) -> str:
        return f"ds:ltr:{tenant_id}:{user_id}:{period_days}"

    @staticmethod
    def material_alerts(tenant_id: str, user_id: str) -> str:
        return f"ds:ma:{tenant_id}:{user_id}"

    @staticmethod
    def projects_admin(tenant_id: str) -> str:
        return f"pj:{tenant_id}:all"

    @staticmethod
    def projects_member(tenant_id: str, user_id: str) -> str:
        return f"pj:{tenant_id}:{user_id}"

    @staticmethod
    def task_statuses(project_id: str) -> str:
        return f"ts:{project_id}"

    @staticmethod
    def tasks(project_id: str) -> str:
        return f"tk:{project_id}"

    @staticmethod
    def master_materials(tenant_id: str) -> str:
        return f"mm:{tenant_id}"

    @staticmethod
    def labour_types(tenant_id: str) -> str:
        return f"lt:{tenant_id}"

    @staticmethod
    def attendance(project_id: str, date: str) -> str:
        return f"att:{project_id}:{date}"

    @staticmethod
    def attendance_bulk(project_id: str, from_date: str, to_date: str) -> str:
        return f"att:b:{project_id}:{from_date}:{to_date}"

    @staticmethod
    def labour_bulk(project_id: str, from_date: str, to_date: str) -> str:
        return f"lab:b:{project_id}:{from_date}:{to_date}"

    @staticmethod
    def expense(project_id: str) -> str:
        return f"exp:{project_id}"

    @staticmethod
    def materials(project_id: str) -> str:
        return f"mat:{project_id}"

    @staticmethod
    def dr_recent_dates(project_id: str) -> str:
        return f"dr:rd:{project_id}"

    @staticmethod
    def dr_list(project_id: str, date: str) -> str:
        return f"dr:l:{project_id}:{date}"

    @staticmethod
    def dr_entries_all(project_id: str, date: str) -> str:
        return f"dr:ea:{project_id}:{date}"

    @staticmethod
    def dr_entries_member(project_id: str, user_id: str, date: str) -> str:
        return f"dr:em:{project_id}:{user_id}:{date}"

    @staticmethod
    def dr_latest_photos(project_id: str) -> str:
        return f"dr:lp:{project_id}"

    @staticmethod
    def bulk_sync(user_id: str, tenant_id: str) -> str:
        return f"bs:{tenant_id}:{user_id}"

    # ── Demo user persistent cache keys ──────────────────────────────────────
    # These keys use 'demo:' prefix and have very long TTL for demo UX
    @staticmethod
    def demo_dashboard(tenant_id: str) -> str:
        return f"demo:ds:{tenant_id}"

    @staticmethod
    def demo_dashboard_period(tenant_id: str, from_date: str, to_date: str) -> str:
        return f"demo:ds:p:{tenant_id}:{from_date}:{to_date}"

    @staticmethod
    def demo_labour_trends(tenant_id: str, period_days: int) -> str:
        return f"demo:ds:ltr:{tenant_id}:{period_days}"

    @staticmethod
    def demo_material_alerts(tenant_id: str) -> str:
        return f"demo:ds:ma:{tenant_id}"

    @staticmethod
    def demo_attendance_bulk(project_id: str, from_date: str, to_date: str) -> str:
        return f"demo:att:b:{project_id}:{from_date}:{to_date}"

    @staticmethod
    def demo_labour_bulk(project_id: str, from_date: str, to_date: str) -> str:
        return f"demo:lab:b:{project_id}:{from_date}:{to_date}"

    @staticmethod
    def demo_materials(project_id: str) -> str:
        return f"demo:mat:{project_id}"

    @staticmethod
    def demo_materials_summary(project_ids: str) -> str:
        """project_ids is comma-separated list of IDs"""
        return f"demo:mat:sum:{project_ids}"

    @staticmethod
    def demo_projects(tenant_id: str) -> str:
        return f"demo:pj:{tenant_id}"

    @staticmethod
    def demo_expense(project_id: str) -> str:
        return f"demo:exp:{project_id}"


# ── Token hashing ─────────────────────────────────────────────────────────────

def token_hash(token: str) -> str:
    """Return first 24 hex chars of sha256(token). Never store raw JWTs as cache keys."""
    return hashlib.sha256(token.encode()).hexdigest()[:24]


# ── Demo user TTL constant ────────────────────────────────────────────────────

# Demo users get persistent cache (7 days) for instant UX
DEMO_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_demo_user(tenant_role: str | None) -> bool:
    """Check if the current user is a demo user based on their tenant role."""
    return tenant_role == "demo"


def cache_get(redis: Any, key: str) -> Any:
    """Return deserialised cached value or None. Never raises."""
    if redis is None:
        return None
    try:
        value = redis.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as exc:
        logger.warning("cache_get error key=%s: %s", key, exc)
        return None


def cache_set(redis: Any, key: str, value: Any, ttl: int) -> None:
    """Serialise value to JSON and store with EX ttl. Never raises."""
    if redis is None:
        return
    try:
        redis.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:
        logger.warning("cache_set error key=%s: %s", key, exc)


def cache_delete(redis: Any, *keys: str) -> None:
    """Delete one or more keys in a single DEL command. Never raises."""
    if redis is None or not keys:
        return
    try:
        redis.delete(*keys)
    except Exception as exc:
        logger.warning("cache_delete error keys=%s: %s", keys, exc)


# ── Redis client singleton ────────────────────────────────────────────────────

@lru_cache()
def get_redis_client():
    """
    Return an upstash_redis.Redis singleton (or None if unconfigured).
    Decorated with @lru_cache so FastAPI's Depends returns the same instance
    on every request. Returns None gracefully when env vars are not set,
    making all cache operations no-ops in local development.
    """
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
        return None
    try:
        from upstash_redis import Redis
        return Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
    except Exception as exc:
        logger.warning("Redis client init failed: %s", exc)
        return None
