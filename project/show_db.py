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
        select table_schema, table_name
        from information_schema.tables
        where table_schema not in ('information_schema', 'pg_catalog')
        order by 1, 2
        """
    ).fetchall()
    if not tables:
        print("database is empty")
        return
    print(f"{'table':<28}{'rows':>8}{'batches':>10}  latest batch")
    for schema, table in tables:
        rows, batches, latest = con.execute(
            f"select count(*), count(distinct _loaded_at), max(_loaded_at)::varchar from {schema}.{table}"
        ).fetchone()
        print(f"{schema + '.' + table:<28}{rows:>8}{batches:>10}  {latest}")


def _show(rel: duckdb.DuckDBPyRelation, limit: int) -> None:
    rel.show(max_width=shutil.get_terminal_size().columns, max_rows=limit)


def show_table(
    con: duckdb.DuckDBPyConnection, name: str, all_batches: bool, limit: int, cols: str | None
) -> None:
    if cols:
        select = cols + (", _loaded_at::timestamp(0)::varchar as _loaded_at" if all_batches else "")
    elif all_batches:
        # Keep the batch column but trim it to seconds so rows stay narrow.
        select = "* replace (_loaded_at::timestamp(0)::varchar as _loaded_at)"
    else:
        select = "* exclude (_loaded_at)"
    where = "" if all_batches else f"where _loaded_at = (select max(_loaded_at) from {name})"
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
