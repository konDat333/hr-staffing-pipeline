"""Peek into the DuckDB warehouse from the command line.

    uv run show_db.py                       # tables, row counts, batches
    uv run show_db.py raw.employees         # dump a table (latest batch)
    uv run show_db.py raw.employees --all   # every batch
    uv run show_db.py raw.employees --cols employee_id,status,reports_to
    uv run show_db.py --sql "select ..."    # arbitrary query
"""

import argparse
import shutil
import sys

import duckdb

from pipeline.db import DEFAULT_DB_PATH


def show_overview(con: duckdb.DuckDBPyConnection) -> None:
    tables = con.execute(
        """
        select table_schema, table_name, table_type
        from information_schema.tables
        where table_schema not in ('information_schema', 'pg_catalog')
        order by 1, 2
        """
    ).fetchall()
    if not tables:
        print("database is empty")
        return
    print(f"{'table':<34}{'type':<7}{'rows':>7}{'batches':>9}  latest batch")
    for schema, table, table_type in tables:
        name = f"{schema}.{table}"
        rows = con.execute(f"select count(*) from {name}").fetchone()[0]
        if _has_column(con, schema, table, "_loaded_at"):
            batches, latest = con.execute(
                f"select count(distinct _loaded_at), max(_loaded_at)::varchar from {name}"
            ).fetchone()
        else:
            batches, latest = "", ""
        kind = "view" if table_type == "VIEW" else "table"
        print(f"{name:<34}{kind:<7}{rows:>7}{batches:>9}  {latest}")


def _has_column(con: duckdb.DuckDBPyConnection, schema: str, table: str, column: str) -> bool:
    return bool(
        con.execute(
            "select 1 from information_schema.columns where table_schema = ? and table_name = ? and column_name = ?",
            [schema, table, column],
        ).fetchone()
    )


def _show(rel: duckdb.DuckDBPyRelation, limit: int) -> None:
    rel.show(max_width=shutil.get_terminal_size().columns, max_rows=limit)


def show_table(
    con: duckdb.DuckDBPyConnection, name: str, all_batches: bool, limit: int, cols: str | None
) -> None:
    schema, _, table = name.partition(".")
    batched = _has_column(con, schema, table, "_loaded_at")
    if not batched:
        select, where = cols or "*", ""
    elif cols:
        select = cols + (", _loaded_at::timestamp(0)::varchar as _loaded_at" if all_batches else "")
        where = "" if all_batches else f"where _loaded_at = (select max(_loaded_at) from {name})"
    elif all_batches:
        # Keep the batch column but trim it to seconds so rows stay narrow.
        select, where = "* replace (_loaded_at::timestamp(0)::varchar as _loaded_at)", ""
    else:
        select, where = "* exclude (_loaded_at)", f"where _loaded_at = (select max(_loaded_at) from {name})"
    _show(con.sql(f"select {select} from {name} {where} limit {limit}"), limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("table", nargs="?", help="schema.table to dump")
    parser.add_argument("--all", action="store_true", help="show every batch, not only the latest")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--cols", help="comma-separated columns to show")
    parser.add_argument("--sql", help="run this query instead")
    args = parser.parse_args()

    if not DEFAULT_DB_PATH.exists():
        print(f"no database at {DEFAULT_DB_PATH} - run `uv run main.py` first", file=sys.stderr)
        return 1

    with duckdb.connect(str(DEFAULT_DB_PATH), read_only=True) as con:
        if args.sql:
            _show(con.sql(args.sql), args.limit)
        elif args.table:
            show_table(con, args.table, args.all, args.limit, args.cols)
        else:
            show_overview(con)
    return 0


if __name__ == "__main__":
    sys.exit(main())
