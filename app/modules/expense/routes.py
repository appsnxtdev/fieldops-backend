from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

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
):
    balance = get_balance(supabase, project_id)
    transactions = list_transactions(supabase, project_id)
    return WalletBalanceResponse(balance=balance, transactions=transactions)


@router.post("/{project_id}/credit", response_model=ExpenseTransactionResponse, status_code=201)
def create_credit(
    project_id: str,
    payload: ExpenseCreditCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_EXPENSE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    return add_credit(supabase, project_id, payload.amount, payload.notes, current_user["id"])


@router.post("/{project_id}/debit", response_model=ExpenseTransactionResponse, status_code=201)
async def create_debit(
    project_id: str,
    amount: float = Form(...),
    notes: str | None = Form(None),
    receipt: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_MANAGE_EXPENSE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    import uuid
    key = str(uuid.uuid4())
    path = upload_receipt(supabase, project_id, key, receipt)
    return add_debit(supabase, project_id, amount, path, notes, current_user["id"])
