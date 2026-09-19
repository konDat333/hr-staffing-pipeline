"""Writing validated DataFrames into DuckDB.

The `raw` schema is an append-only log of every load: each run appends
*all* rows of every source, stamped with one shared `_loaded_at` batch
timestamp. Nothing is updated or deleted here - resolving the current
state (latest batch) is done downstream in dbt staging models.
"""

import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

DEFAULT_DB_PATH = Path(os.environ.get("DUCKDB_PATH", Path(__file__).resolve().parents[1] / "warehouse" / "warehouse.duckdb"))
RAW_SCHEMA = "raw"


def connect(db_path: Path = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (and create if missing) the DuckDB database file."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def _qualified(schema: str, table: str) -> str:
    for name in (schema, table):
        if not name.isidentifier():
            raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f"{schema}.{table}"


def write_table(
    con: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
    table: str,
    loaded_at: datetime,
    schema: str = RAW_SCHEMA,
) -> int:
    """Append all rows of `df` to `schema.table` as one batch tagged `loaded_at`.

    Creates the table on first use. Returns the number of rows appended.
    """
    target = _qualified(schema, table)

    frame = df.copy()
    frame["_loaded_at"] = loaded_at

    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    # Transaction so a failure mid-write leaves the table as it was.
    con.execute("BEGIN")
    try:
        con.register("_incoming", frame)
        # First run: create an empty table with the incoming structure.
        con.execute(f"CREATE TABLE IF NOT EXISTS {target} AS SELECT * FROM _incoming LIMIT 0")
        appended = con.execute(f"INSERT INTO {target} BY NAME SELECT * FROM _incoming").fetchone()[0]
        con.unregister("_incoming")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    return appended


def count_rows(con: duckdb.DuckDBPyConnection, table: str, schema: str = RAW_SCHEMA) -> int:
    return con.execute(f"SELECT count(*) FROM {_qualified(schema, table)}").fetchone()[0]


def latest_batch(con: duckdb.DuckDBPyConnection, table: str, schema: str = RAW_SCHEMA) -> datetime | None:
    """Timestamp of the most recent batch in the table, or None if empty."""
    return con.execute(f"SELECT max(_loaded_at) FROM {_qualified(schema, table)}").fetchone()[0]
