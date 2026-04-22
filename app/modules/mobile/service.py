"""Business logic for mobile endpoints."""
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from supabase import Client

from .schemas import (
    BulkSyncResponse,
    MasterDataResponse,
    SyncQueueResponse,
    ProjectData,
    AttendanceToday,
    MyTask,
    TaskStatus,
    Material,
    LabourToday,
    LabourEntry,
    Wallet,
    WalletTransaction,
    DailyReportToday,
    Location,
    LabourType,
    MasterMaterial,
    SyncResult,
)


class MobileService:
    """Service for mobile-specific operations."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_bulk_sync_data(self, user_id: str, tenant_id: str) -> BulkSyncResponse:
        """Get all data for mobile app in one call."""
        from app.core.constants import DB_SCHEMA
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"get_bulk_sync_data called for user_id={user_id}, tenant_id={tenant_id}")

        # Get projects where user is a member
        members_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("project_members")
            .select("project_id")
            .eq("user_id", user_id)
            .execute()
        )
        project_ids = [row["project_id"] for row in (members_r.data or [])]

        logger.info(f"User {user_id} is member of {len(project_ids)} projects: {project_ids}")

        if not project_ids:
            return BulkSyncResponse(projects=[], last_sync=datetime.now(timezone.utc).isoformat())

        # Fetch project details
        projects_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("projects")
            .select("*")
            .eq("tenant_id", tenant_id)
            .in_("id", project_ids)
            .execute()
        )

        projects_data = []
        today = datetime.now(timezone.utc).date().isoformat()

        for project in (projects_r.data or []):
            project_id = project["id"]

            # Build location if available
            location = None
            if project.get("lat") is not None and project.get("lng") is not None:
                location = Location(lat=float(project["lat"]), lng=float(project["lng"]))

            # Fetch all data for this project (excluding attendance - fetched via separate endpoint)
            tasks = await self._get_my_tasks(project_id, user_id)
            task_statuses = await self._get_task_statuses(project_id)
            materials = await self._get_materials(project_id)
            labour = await self._get_labour_today(project_id, today, tenant_id)
            wallet = await self._get_wallet(project_id, today)
            daily_report = await self._get_daily_report_today(project_id, user_id, today)

            project_data = ProjectData(
                id=project_id,
                name=project["name"],
                location=location,
                attendance_today=None,  # Excluded from bulk-sync, use /attendance endpoint
                my_tasks=tasks,
                task_statuses=task_statuses,
                materials=materials,
                labour_today=labour,
                wallet=wallet,
                daily_report_today=daily_report,
            )
            projects_data.append(project_data)

        return BulkSyncResponse(
            projects=projects_data,
            last_sync=datetime.now(timezone.utc).isoformat()
        )

    async def _get_attendance_today(
        self, project_id: str, user_id: str, today: str
    ) -> Optional[AttendanceToday]:
        """Get today's attendance record for user.

        Note: We try to get today's record first, but if not found,
        we return the most recent record to handle timezone differences
        and ensure the mobile app always sees the latest attendance state.
        """
        from app.core.constants import DB_SCHEMA

        # First try to get today's record
        r = (
            self.supabase.schema(DB_SCHEMA)
            .table("attendance")
            .select("*")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .eq("date", today)
            .maybe_single()
            .execute()
        )

        # If today's record exists, return it
        if r and r.data:
            data = r.data
            return AttendanceToday(
                id=data["id"],
                project_id=data["project_id"],
                user_id=data["user_id"],
                date=data["date"],
                check_in_at=data.get("check_in_at"),
                check_out_at=data.get("check_out_at"),
                check_in_lat=data.get("check_in_lat"),
                check_in_lng=data.get("check_in_lng"),
                check_out_lat=data.get("check_out_lat"),
                check_out_lng=data.get("check_out_lng"),
                check_in_selfie_path=data.get("check_in_selfie_path"),
                check_out_selfie_path=data.get("check_out_selfie_path"),
            )

        # If no record for today, get the most recent attendance record
        # This handles timezone differences and ensures mobile app sees latest state
        recent = (
            self.supabase.schema(DB_SCHEMA)
            .table("attendance")
            .select("*")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .order("date", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )

        if not recent or not recent.data:
            return None

        data = recent.data
        return AttendanceToday(
            id=data["id"],
            project_id=data["project_id"],
            user_id=data["user_id"],
            date=data["date"],
            check_in_at=data.get("check_in_at"),
            check_out_at=data.get("check_out_at"),
            check_in_lat=data.get("check_in_lat"),
            check_in_lng=data.get("check_in_lng"),
            check_out_lat=data.get("check_out_lat"),
            check_out_lng=data.get("check_out_lng"),
            check_in_selfie_path=data.get("check_in_selfie_path"),
            check_out_selfie_path=data.get("check_out_selfie_path"),
        )

    async def _get_my_tasks(self, project_id: str, user_id: str) -> List[MyTask]:
        """Get tasks assigned to user in this project."""
        from app.core.constants import DB_SCHEMA
        import logging
        logger = logging.getLogger(__name__)

        r = (
            self.supabase.schema(DB_SCHEMA)
            .table("tasks")
            .select("*, project_task_statuses(id, name)")
            .eq("project_id", project_id)
            .eq("assignee_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        logger.info(f"_get_my_tasks for user {user_id} in project {project_id}: found {len(r.data or [])} tasks")

        tasks = []
        for row in (r.data or []):
            status_data = row.get("project_task_statuses")
            if not status_data:
                continue

            task_status = TaskStatus(
                id=status_data["id"],
                name=status_data["name"],
                color=status_data.get("color"),
            )

            tasks.append(
                MyTask(
                    id=row["id"],
                    project_id=row["project_id"],
                    title=row["title"],
                    description=row.get("description"),
                    status_id=row["status_id"],
                    status=task_status,
                    assigned_to=row["assignee_id"],
                    due_date=row.get("due_at"),
                )
            )

        return tasks

    async def _get_task_statuses(self, project_id: str) -> List[TaskStatus]:
        """Get task statuses for project."""
        from app.core.constants import DB_SCHEMA

        response = (
            self.supabase.schema(DB_SCHEMA)
            .table("project_task_statuses")
            .select("*")
            .eq("project_id", project_id)
            .order("sort_order")
            .execute()
        )

        return [
            TaskStatus(
                id=status["id"],
                name=status["name"],
                color=status.get("color", "#999999"),
            )
            for status in response.data
        ]

    async def _get_materials(self, project_id: str) -> List[Material]:
        """Get materials with current stock for project."""
        from app.core.constants import DB_SCHEMA
        from decimal import Decimal

        # Get materials for project with master_materials join
        materials_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("materials")
            .select("id, name, unit, master_material_id")
            .eq("project_id", project_id)
            .execute()
        )

        materials_list = []
        material_ids = [m["id"] for m in (materials_r.data or [])]

        if not material_ids:
            return []

        # Get ledger entries to calculate balance
        ledger_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("material_ledger")
            .select("material_id, type, quantity")
            .in_("material_id", material_ids)
            .execute()
        )

        # Calculate balances
        balances: Dict[str, Decimal] = {}
        for entry in (ledger_r.data or []):
            mid = entry["material_id"]
            delta = (
                Decimal(str(entry["quantity"]))
                if entry["type"] == "in"
                else -Decimal(str(entry["quantity"]))
            )
            balances[mid] = balances.get(mid, Decimal("0")) + delta

        # Build material list
        for mat in (materials_r.data or []):
            materials_list.append(
                Material(
                    id=mat["id"],
                    name=mat["name"],
                    current_stock=float(balances.get(mat["id"], Decimal("0"))),
                    unit=mat["unit"],
                )
            )

        return materials_list

    async def _get_labour_today(
        self, project_id: str, today: str, tenant_id: str
    ) -> Optional[LabourToday]:
        """Get today's labour entries for project."""
        from app.core.constants import DB_SCHEMA

        r = (
            self.supabase.schema(DB_SCHEMA)
            .table("labour_daily")
            .select("labour_type_id, count, labour_types!inner(id, name, rate_per_day)")
            .eq("project_id", project_id)
            .eq("date", today)
            .execute()
        )

        if not r.data:
            return None

        entries = []
        for row in r.data:
            type_data = row.get("labour_types", {})
            entries.append(
                LabourEntry(
                    id=row["labour_type_id"],
                    labour_type_id=row["labour_type_id"],
                    labour_type_name=type_data.get("name", ""),
                    quantity=float(row.get("count", 0)),
                    unit="workers",
                )
            )

        if not entries:
            return None

        return LabourToday(
            id=f"{project_id}_{today}",
            date=today,
            labour_entries=entries,
        )

    async def _get_wallet(
        self, project_id: str, today: str
    ) -> Optional[Wallet]:
        """Get wallet balance and today's transactions."""
        from app.core.constants import DB_SCHEMA
        from decimal import Decimal

        # Get all transactions to calculate balance
        all_txns_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("expense_transactions")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )

        total = Decimal("0")
        today_transactions = []

        for txn in (all_txns_r.data or []):
            # Calculate balance
            if txn["type"] == "credit":
                total += Decimal(str(txn["amount"]))
            else:
                total -= Decimal(str(txn["amount"]))

            # Filter today's transactions
            txn_date = txn.get("created_at", "")[:10] if txn.get("created_at") else ""
            if txn_date == today:
                today_transactions.append(
                    WalletTransaction(
                        id=txn["id"],
                        amount=float(txn["amount"]),
                        type=txn["type"],
                        description=txn.get("notes"),
                        date=txn.get("created_at", ""),
                    )
                )

        return Wallet(
            balance=float(total),
            currency="INR",
            recent_transactions=today_transactions,
        )

    async def _get_daily_report_today(
        self, project_id: str, user_id: str, today: str
    ) -> Optional[DailyReportToday]:
        """Get today's daily report for user."""
        from app.core.constants import DB_SCHEMA

        r = (
            self.supabase.schema(DB_SCHEMA)
            .table("daily_reports")
            .select("*")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .eq("report_date", today)
            .maybe_single()
            .execute()
        )

        if not r or not r.data:
            return None

        data = r.data
        # Check if report has entries
        entries_r = (
            self.supabase.schema(DB_SCHEMA)
            .table("daily_report_entries")
            .select("id")
            .eq("daily_report_id", data["id"])
            .execute()
        )

        status = "submitted" if (entries_r.data or []) else "draft"

        return DailyReportToday(
            id=data["id"],
            date=data["report_date"],
            status=status,
            submitted_at=data.get("created_at"),
        )

    async def get_master_data(self, tenant_id: str) -> MasterDataResponse:
        """Get master data (labour types, materials)."""
        from app.core.constants import DB_SCHEMA

        # Get labour types
        labour_response = (
            self.supabase.schema(DB_SCHEMA)
            .table("labour_types")
            .select("id, name, rate_per_day")
            .eq("tenant_id", tenant_id)
            .order("name")
            .execute()
        )

        labour_types = [
            LabourType(
                id=lt["id"],
                name=lt["name"],
                rate_per_day=lt.get("rate_per_day", 0.0),
            )
            for lt in (labour_response.data or [])
        ]

        # Get master materials
        materials_response = (
            self.supabase.schema(DB_SCHEMA)
            .table("master_materials")
            .select("id, name, unit")
            .eq("tenant_id", tenant_id)
            .order("name")
            .execute()
        )

        master_materials = [
            MasterMaterial(
                id=mat["id"],
                name=mat["name"],
                unit=mat["unit"],
            )
            for mat in (materials_response.data or [])
        ]

        return MasterDataResponse(
            labour_types=labour_types,
            master_materials=master_materials,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    async def process_sync_queue(
        self, user_id: str, tenant_id: str, changes: List[Dict[str, Any]]
    ) -> SyncQueueResponse:
        """Process batch of queued changes."""
        from app.core.constants import DB_SCHEMA

        results = []

        for change in changes:
            local_id = change["id"]
            entity_type = change["entity_type"]
            operation = change["operation"]
            project_id = change.get("project_id")
            payload = change["payload"]

            try:
                server_id = await self._process_single_change(
                    entity_type, operation, project_id, user_id, tenant_id, payload
                )

                results.append(
                    SyncResult(
                        local_id=local_id,
                        success=True,
                        server_id=server_id,
                        synced_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
            except Exception as e:
                results.append(
                    SyncResult(
                        local_id=local_id,
                        success=False,
                        error=str(e),
                    )
                )

        return SyncQueueResponse(results=results)

    async def _process_single_change(
        self,
        entity_type: str,
        operation: str,
        project_id: Optional[str],
        user_id: str,
        tenant_id: str,
        payload: Dict[str, Any],
    ) -> str:
        """Process a single queued change."""
        if entity_type == "attendance":
            return await self._process_attendance(operation, project_id, user_id, tenant_id, payload)
        elif entity_type == "task_update":
            return await self._process_task_update(project_id, user_id, tenant_id, payload)
        elif entity_type == "material_ledger":
            return await self._process_material_ledger(project_id, user_id, tenant_id, payload)
        elif entity_type == "labour_entry":
            return await self._process_labour_entry(project_id, user_id, tenant_id, payload)
        elif entity_type == "expense":
            return await self._process_expense(project_id, user_id, tenant_id, payload)
        elif entity_type == "daily_report":
            return await self._process_daily_report(operation, project_id, user_id, tenant_id, payload)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    async def _process_attendance(
        self, operation: str, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process attendance check-in/out."""
        from app.core.constants import DB_SCHEMA

        today = datetime.now(timezone.utc).date().isoformat()

        # Find or create today's attendance record
        existing = (
            self.supabase.schema(DB_SCHEMA)
            .table("attendance")
            .select("id")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .eq("date", today)
            .maybe_single()
            .execute()
        )

        if operation == "check_in":
            if existing.data:
                # Update existing
                response = (
                    self.supabase.schema(DB_SCHEMA)
                    .table("attendance")
                    .update({
                        "check_in_at": payload["check_in_at"],
                        "check_in_lat": payload.get("check_in_lat"),
                        "check_in_lng": payload.get("check_in_lng"),
                    })
                    .eq("id", existing.data["id"])
                    .execute()
                )
                if not response.data or len(response.data) == 0:
                    raise ValueError("Failed to update attendance check-in")
                return response.data[0]["id"]
            else:
                # Create new
                response = (
                    self.supabase.schema(DB_SCHEMA)
                    .table("attendance")
                    .insert({
                        "project_id": project_id,
                        "user_id": user_id,
                        "date": today,
                        "check_in_at": payload["check_in_at"],
                        "check_in_lat": payload.get("check_in_lat"),
                        "check_in_lng": payload.get("check_in_lng"),
                    })
                    .execute()
                )
                if not response.data or len(response.data) == 0:
                    raise ValueError("Failed to create attendance check-in")
                return response.data[0]["id"]

        elif operation == "check_out":
            if not existing.data:
                raise ValueError("No check-in found for today")

            response = (
                self.supabase.schema(DB_SCHEMA)
                .table("attendance")
                .update({
                    "check_out_at": payload["check_out_at"],
                    "check_out_lat": payload.get("check_out_lat"),
                    "check_out_lng": payload.get("check_out_lng"),
                })
                .eq("id", existing.data["id"])
                .execute()
            )
            if not response.data or len(response.data) == 0:
                raise ValueError("Failed to update attendance check-out")
            return response.data[0]["id"]

        raise ValueError(f"Unknown attendance operation: {operation}")

    async def _process_task_update(
        self, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process task status update."""
        from app.core.constants import DB_SCHEMA

        if not project_id:
            raise ValueError("project_id is required for task updates")

        response = (
            self.supabase.schema(DB_SCHEMA)
            .table("task_updates")
            .insert({
                "task_id": payload["task_id"],
                "project_id": project_id,
                "author_id": user_id,
                "status_id": payload.get("status_id"),
                "note": payload.get("note"),
                "photo_urls": payload.get("photo_urls", []),
            })
            .execute()
        )
        if not response.data or len(response.data) == 0:
            raise ValueError("Failed to create task update")

        # Also update task's current status
        if payload.get("status_id"):
            self.supabase.schema(DB_SCHEMA).table("tasks").update({
                "status_id": payload["status_id"],
            }).eq("id", payload["task_id"]).execute()

        return response.data[0]["id"]

    async def _process_material_ledger(
        self, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process material ledger entry."""
        from app.core.constants import DB_SCHEMA

        if not project_id:
            raise ValueError("project_id is required for material ledger")

        # Create ledger entry
        response = (
            self.supabase.schema(DB_SCHEMA)
            .table("material_ledger")
            .insert({
                "project_id": project_id,
                "material_id": payload["material_id"],
                "type": payload["type"],  # 'in' or 'out'
                "quantity": payload["quantity"],
                "notes": payload.get("notes"),
                "photo_url": payload.get("photo_url"),
                "created_by": user_id,
            })
            .execute()
        )
        if not response.data or len(response.data) == 0:
            raise ValueError("Failed to create material ledger entry")

        # Update material current stock
        delta = float(payload["quantity"])
        if payload["type"] == "out":
            delta = -delta

        self.supabase.rpc(
            "update_material_stock",
            {
                "material_id": payload["material_id"],
                "delta": delta,
            }
        ).execute()

        return response.data[0]["id"]

    async def _process_labour_entry(
        self, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process labour daily entry."""
        from app.core.constants import DB_SCHEMA

        if not project_id:
            raise ValueError("project_id is required for labour entry")

        response = (
            self.supabase.schema(DB_SCHEMA)
            .table("labour_daily")
            .insert({
                "project_id": project_id,
                "labour_type_id": payload["labour_type_id"],
                "date": payload.get("date", datetime.now(timezone.utc).date().isoformat()),
                "count": payload["count"],
                "created_by": user_id,
            })
            .execute()
        )
        if not response.data or len(response.data) == 0:
            raise ValueError("Failed to create labour entry")
        return response.data[0]["id"]

    async def _process_expense(
        self, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process expense transaction."""
        from app.core.constants import DB_SCHEMA

        if not project_id:
            raise ValueError("project_id is required for expense")

        response = (
            self.supabase.schema(DB_SCHEMA)
            .table("expense_transactions")
            .insert({
                "project_id": project_id,
                "type": "debit",  # Field worker expenses are always debits
                "amount": payload["amount"],
                "notes": payload.get("notes"),
                "category": payload.get("category"),
                "receipt_storage_path": payload.get("receipt_storage_path"),
                "created_by": user_id,
            })
            .execute()
        )
        if not response.data or len(response.data) == 0:
            raise ValueError("Failed to create expense transaction")

        # Update wallet balance
        self.supabase.rpc(
            "update_wallet_balance",
            {
                "project_id": project_id,
                "delta": -float(payload["amount"]),
            }
        ).execute()

        return response.data[0]["id"]

    async def _process_daily_report(
        self, operation: str, project_id: str, user_id: str, tenant_id: str, payload: Dict[str, Any]
    ) -> str:
        """Process daily report create/update."""
        from app.core.constants import DB_SCHEMA

        if not project_id:
            raise ValueError("project_id is required for daily report")

        report_date = payload.get("date", datetime.now(timezone.utc).date().isoformat())

        if operation == "create":
            response = (
                self.supabase.schema(DB_SCHEMA)
                .table("daily_reports")
                .insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "report_date": report_date,
                })
                .execute()
            )
            if not response.data or len(response.data) == 0:
                raise ValueError("Failed to create daily report")
            return response.data[0]["id"]

        elif operation == "update":
            # Mobile app won't update daily reports - they're append-only via entries
            raise ValueError("Daily report updates not supported from mobile app")

        raise ValueError(f"Unknown daily report operation: {operation}")
