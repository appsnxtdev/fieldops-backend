"""App-wide constants."""

DB_SCHEMA = "fieldops"

MATERIAL_UNITS = (
    "kg",
    "L",
    "pieces",
    "m",
    "m²",
    "bags",
    "tonnes",
    "cubic m",
    "boxes",
    "rolls",
)

# Task status names that count as "done" for ROI / dashboard metrics.
DONE_TASK_STATUS_NAMES = ("Done", "Complete")

# Material low stock threshold for alerts
MATERIAL_LOW_STOCK_THRESHOLD = 20.0
