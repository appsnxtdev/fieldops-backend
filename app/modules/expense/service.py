from decimal import Decimal
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.expense.schemas import ExpenseTransactionResponse, WalletBalanceResponse


def list_transactions(supabase: Client, project_id: str) -> list[ExpenseTransactionResponse]:
    r = supabase.schema(DB_SCHEMA).table("expense_transactions").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
    return [ExpenseTransactionResponse(**row) for row in (r.data or [])]


def get_balance(supabase: Client, project_id: str) -> float:
    r = supabase.schema(DB_SCHEMA).table("expense_transactions").select("type, amount").eq("project_id", project_id).execute()
    total = Decimal("0")
    for row in r.data or []:
        if row["type"] == "credit":
            total += Decimal(str(row["amount"]))
        else:
            total -= Decimal(str(row["amount"]))
    return float(total)


def add_credit(supabase: Client, project_id: str, amount: float, notes: str | None, created_by: str) -> ExpenseTransactionResponse:
    row = {"project_id": project_id, "type": "credit", "amount": amount, "notes": notes, "created_by": created_by}
    r = supabase.schema(DB_SCHEMA).table("expense_transactions").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    return ExpenseTransactionResponse(**data)


def add_debit(supabase: Client, project_id: str, amount: float, receipt_path: str, notes: str | None, created_by: str) -> ExpenseTransactionResponse:
    row = {
        "project_id": project_id,
        "type": "debit",
        "amount": amount,
        "receipt_storage_path": receipt_path,
        "notes": notes,
        "created_by": created_by,
    }
    r = supabase.schema(DB_SCHEMA).table("expense_transactions").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    return ExpenseTransactionResponse(**data)
