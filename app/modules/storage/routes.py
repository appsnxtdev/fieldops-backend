import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_current_user, get_supabase_client
from supabase import Client

router = APIRouter()
log = logging.getLogger(__name__)

ALLOWED_BUCKETS = frozenset({"daily_reports", "expense", "attendance", "material_receipts"})
SIGNED_URL_EXPIRY_SEC = 3600


def _extract_signed_url(res) -> str | None:
    if isinstance(res, dict):
        return res.get("signedUrl") or res.get("signedURL")
    return getattr(res, "signedUrl", None) or getattr(res, "signedURL", None)


def _create_signed_url(supabase: Client, bucket: str, path: str):
    res = supabase.storage.from_(bucket).create_signed_url(path, SIGNED_URL_EXPIRY_SEC)
    return _extract_signed_url(res)


@router.get("/signed-url")
def get_signed_url(
    bucket: str = Query(..., description="Storage bucket name"),
    path: str = Query(..., description="Object path within the bucket"),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Return a signed URL for a private storage object. Uses service role so RLS does not block."""
    if bucket not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=400, detail="Bucket not allowed")
    path = path.lstrip("/")
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Try path as given, then try without leading "bucket/" (handles old vs new stored paths)
    for try_path in (path, path.split("/", 1)[-1] if path.startswith(f"{bucket}/") else None):
        if try_path is None:
            continue
        try:
            url = _create_signed_url(supabase, bucket, try_path)
            if url:
                return {"url": url}
        except Exception as e:
            log.debug("create_signed_url %s/%s: %s", bucket, try_path, e)
            continue

    raise HTTPException(status_code=404, detail="Object not found")
