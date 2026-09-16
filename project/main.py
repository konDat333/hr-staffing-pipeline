"""Load the HR Excel exports into DuckDB.

Rows that violate the row-level contract are quarantined instead of
failing the load; the run is aborted (nothing written) when the share
of quarantined rows in any source exceeds the threshold.
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandera.pandas as pa

from pipeline.db import DEFAULT_DB_PATH, connect, count_rows, write_table
from pipeline.excel import ExcelLayoutError, ExcelSource, read_excel_source
from pipeline.schemas import AssignmentSchema, EmployeeSchema
from pipeline.sources import DEFAULT_DATA_DIR, assignments_source, employees_source
from pipeline.validation import StructuralError, ValidationResult, validate

log = logging.getLogger("pipeline")

DEFAULT_MAX_INVALID_SHARE = float(os.environ.get("MAX_INVALID_SHARE", "0.10"))
QUARANTINE_SUFFIX = "_quarantine"


@dataclass(frozen=True)
class Source:
    table: str
    excel: ExcelSource
    schema: type[pa.DataFrameModel]


def sources(data_dir: Path) -> list[Source]:
    return [
        Source("employees", employees_source(data_dir), EmployeeSchema),
        Source("assignments", assignments_source(data_dir), AssignmentSchema),
    ]


def load_source(source: Source) -> ValidationResult:
    return validate(read_excel_source(source.excel), source.schema)


def over_threshold(result: ValidationResult, max_share: float) -> bool:
    return result.invalid_share > max_share or len(result.valid) == 0


def run(data_dir: Path, max_invalid_share: float, db_path: Path) -> int:
    # Validate every source before writing anything: the batch is all-or-nothing.
    results: dict[str, ValidationResult] = {}
    for source in sources(data_dir):
        result = load_source(source)
        results[source.table] = result
        log.info(
            "%s: %d rows read, %d valid, %d quarantined (%.1f%%)",
            source.table, result.total, len(result.valid), len(result.quarantine), result.invalid_share * 100,
        )
        for row in result.quarantine.itertuples(index=False):
            log.warning("  quarantined %s: %s", row[0], row[-1])

    failing = [t for t, r in results.items() if over_threshold(r, max_invalid_share)]
    if failing:
        log.error(
            "aborting: invalid share above %.0f%% (or no valid rows) in %s - nothing written",
            max_invalid_share * 100, ", ".join(failing),
        )
        return 1

    loaded_at = datetime.now(timezone.utc)
    with connect(db_path) as con:
        for table, result in results.items():
            write_table(con, result.valid, table, loaded_at=loaded_at)
            if not result.quarantine.empty:
                write_table(con, result.quarantine, table + QUARANTINE_SUFFIX, loaded_at=loaded_at)
            log.info("raw.%s: %d rows appended, %d total", table, len(result.valid), count_rows(con, table))
    log.info("batch %s written to %s", loaded_at.isoformat(timespec="seconds"), db_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="folder with the Excel exports")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="DuckDB file to write to")
    parser.add_argument(
        "--max-invalid-share", type=float, default=DEFAULT_MAX_INVALID_SHARE,
        help="abort when quarantined rows exceed this share of a source (default %(default)s)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        return run(args.data_dir, args.max_invalid_share, args.db)
    except (FileNotFoundError, ExcelLayoutError, StructuralError) as exc:
        log.error("could not read source data: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
