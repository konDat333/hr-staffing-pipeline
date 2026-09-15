"""Load the HR Excel exports and validate them against the raw schemas."""

import logging
import sys
from pathlib import Path

import pandas as pd
import pandera.pandas as pa

from pipeline.excel import read_excel_source
from pipeline.schemas import AssignmentSchema, EmployeeSchema
from pipeline.sources import DEFAULT_DATA_DIR, assignments_source, employees_source

log = logging.getLogger("pipeline")


def load_employees(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    df = read_excel_source(employees_source(data_dir))
    return EmployeeSchema.validate(df, lazy=True)


def load_assignments(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    df = read_excel_source(assignments_source(data_dir))
    return AssignmentSchema.validate(df, lazy=True)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        employees = load_employees()
        assignments = load_assignments()
    except pa.errors.SchemaErrors as exc:
        # Dataframe-level checks report every column of a failing row;
        # collapse to one line per (check, row) to keep the log readable.
        failures = exc.failure_cases.drop_duplicates(subset=["check", "index"])
        log.error(
            "Schema validation failed (%d problems):\n%s",
            len(failures),
            failures[["check", "column", "index", "failure_case"]].to_string(index=False),
        )
        return 1
    except (FileNotFoundError, ValueError) as exc:
        log.error("Could not read source data: %s", exc)
        return 1

    log.info("employees: %d rows, %d columns", *employees.shape)
    log.info("assignments: %d rows, %d columns", *assignments.shape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
