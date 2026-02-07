def get_tenant_details(tenant_id: str, app_metadata: dict | None = None) -> dict:
    """Return tenant id and name from FieldOps/JWT only (no core service)."""
    name = None
    if app_metadata:
        name = app_metadata.get("tenant_name") or app_metadata.get("name")
    return {"id": tenant_id, "name": name}
