import csv
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_delete, cache_get, cache_set, get_redis_client, is_demo_user
from app.core.dependencies import get_current_user, get_project_access, get_supabase_client
from app.core.permissions import CAN_MANAGE_EXPENSE, CAN_VIEW_EXPENSE
from app.modules.expense.schemas import ExpenseCreditCreate, ExpenseTransactionResponse, WalletBalanceResponse
from app.modules.expense.service import add_credit, add_debit, get_balance, list_transactions
from supabase import Client

router = APIRouter()


def upload_receipt(supabase: Client, project_id: str, txn_id_placeholder: str, file: UploadFile) -> str:
    path = f"expense/{project_id}/{txn_id_placeholder}_{file.filename or 'receipt.jpg'}"
    content = file.file.read()
    supabase.storage.from_("expense").upload(path, content, file_options={"content-type": file.content_type or "image/jpeg"})
    return path


@router.get("/{project_id}", response_model=WalletBalanceResponse)
def get_wallet(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_EXPENSE)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    # Check if demo user for persistent caching
    tenant_role = access.get("tenant_role")
    is_demo = is_demo_user(tenant_role)

    if is_demo:
        key = CacheKeys.demo_expense(project_id)
        ttl = DEMO_CACHE_TTL
    else:
        key = CacheKeys.expense(project_id)
        ttl = 30

    cached = cache_get(redis, key)
    if cached is not None:
        return WalletBalanceResponse(**cached)

    balance = get_balance(supabase, project_id)
    transactions = list_transactions(supabase, project_id)
    result = WalletBalanceResponse(balance=balance, transactions=transactions)
    cache_set(redis, key, result.model_dump(), ttl=ttl)
    return result


@router.get("/{project_id}/export")
def export_expense_route(
    project_id: str,
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
    access: dict = Depends(get_project_access(CAN_VIEW_EXPENSE)),
    supabase: Client = Depends(get_supabase_client),
):
    """Export expense transactions for a site as CSV (created_at date range inclusive)."""
    from app.modules.users.service import get_profiles_by_ids

    transactions = list_transactions(supabase, project_id)
    filtered = [
        t for t in transactions
        if t.created_at and from_date <= (t.created_at[:10] if len(t.created_at) >= 10 else t.created_at) <= to_date
    ]
    user_ids = list({t.created_by for t in filtered if t.created_by})
    profiles = get_profiles_by_ids(supabase, user_ids)
    profile_map = {p.id: p for p in profiles}

    def format_datetime(iso: str | None) -> str:
        if not iso:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            return iso or ""

    def created_by_name(uid: str | None) -> str:
        if not uid:
            return ""
        p = profile_map.get(uid)
        if p and (p.full_name or p.email):
            return (p.full_name or p.email or "").strip()
        return uid[:8] if uid else ""

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["type", "amount", "notes", "date_time", "created_by_name"])
    for t in filtered:
        w.writerow([t.type, t.amount, t.notes or "", format_datetime(t.created_at), created_by_name(t.created_by)])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expense_{project_id}_{from_date}_{to_date}.csv"},
    )


@router.post("/{project_id}/credit", response_model=ExpenseTransactionResponse, status_code=201)
def create_credit(
    project_id: str,
    payload: ExpenseCreditCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_EXPENSE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    result = add_credit(supabase, project_id, payload.amount, payload.notes, current_user["id"])
    cache_delete(
        redis,
        CacheKeys.expense(project_id),
        CacheKeys.dashboard(access["tenant_id"], current_user["id"]),
    )
    return result


@router.post("/{project_id}/debit", response_model=ExpenseTransactionResponse, status_code=201)
async def create_debit(
    project_id: str,
    amount: float = Form(...),
    notes: str | None = Form(None),
    receipt: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_MANAGE_EXPENSE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    import uuid
    key = str(uuid.uuid4())
    path = upload_receipt(supabase, project_id, key, receipt)
    result = add_debit(supabase, project_id, amount, path, notes, current_user["id"])
    cache_delete(
        redis,
        CacheKeys.expense(project_id),
        CacheKeys.dashboard(access["tenant_id"], current_user["id"]),
    )
    return result
