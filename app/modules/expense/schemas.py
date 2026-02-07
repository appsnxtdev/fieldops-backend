from pydantic import BaseModel


class ExpenseCreditCreate(BaseModel):
    amount: float
    notes: str | None = None


class ExpenseDebitCreate(BaseModel):
    amount: float
    notes: str | None = None
    # receipt_storage_path set from uploaded file in route


class ExpenseTransactionResponse(BaseModel):
    id: str
    project_id: str
    type: str
    amount: float
    receipt_storage_path: str | None = None
    notes: str | None = None
    created_at: str | None = None
    created_by: str | None = None


class WalletBalanceResponse(BaseModel):
    balance: float
    transactions: list[ExpenseTransactionResponse]
