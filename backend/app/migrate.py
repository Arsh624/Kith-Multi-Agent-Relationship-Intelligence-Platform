from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Additive, idempotent column additions so an already-deployed database
# (with existing rows) gains new columns without create_all or data loss.
# Each entry: (table, column, sql_type). All are nullable so existing rows
# are simply left null.
_ADDITIONS = [
    ("people", "color", "VARCHAR"),
    ("people", "favorite", "BOOLEAN"),
    ("companies", "color", "VARCHAR"),
]


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, sql_type in _ADDITIONS:
        if table not in tables:
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        if column in existing:
            continue
        with engine.begin() as conn:
            conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            )
