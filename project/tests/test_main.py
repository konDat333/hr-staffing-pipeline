from pathlib import Path

import duckdb
import pandas as pd
import pytest

from conftest import ASSIGNMENT_COLUMNS, EMPLOYEE_COLUMNS, frame_to_rows, write_excel
from main import over_threshold, run
from pipeline.validation import ValidationResult


def _result(valid: int, quarantined: int) -> ValidationResult:
    return ValidationResult(
        valid=pd.DataFrame({"x": range(valid)}),
        quarantine=pd.DataFrame({"x": range(quarantined)}),
    )


@pytest.mark.parametrize(
    "valid, quarantined, expected",
    [(23, 2, False), (19, 7, True), (0, 3, True), (25, 0, False)],
)
def test_over_threshold_at_ten_percent(valid, quarantined, expected):
    assert over_threshold(_result(valid, quarantined), 0.10) is expected


def _write_sources(data_dir: Path, employees_df, assignments_df) -> None:
    write_excel(data_dir / "hr_employees_export.xlsx", list(EMPLOYEE_COLUMNS), frame_to_rows(employees_df))
    write_excel(
        data_dir / "project_assignments_report.xlsx", list(ASSIGNMENT_COLUMNS), frame_to_rows(assignments_df)
    )


def _tables(db: Path) -> set[str]:
    with duckdb.connect(str(db), read_only=True) as con:
        return {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}


def test_run_loads_clean_data(tmp_path, employees_df, assignments_df):
    _write_sources(tmp_path, employees_df, assignments_df)
    db = tmp_path / "w.duckdb"

    assert run(tmp_path, 0.10, db) == 0
    assert _tables(db) == {"employees", "assignments"}


def test_run_quarantines_bad_rows_when_under_threshold(tmp_path, employees_df, assignments_df):
    assignments_df.loc[0, "billable_raw"] = "TRUE"
    _write_sources(tmp_path, employees_df, assignments_df)
    db = tmp_path / "w.duckdb"

    assert run(tmp_path, max_invalid_share=0.5, db_path=db) == 0
    assert _tables(db) == {"employees", "assignments", "assignments_quarantine"}
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("select count(*) from raw.assignments").fetchone()[0] == 2
        assert con.execute("select _errors from raw.assignments_quarantine").fetchone()[0].startswith("billable_in_domain")


def test_run_aborts_and_writes_nothing_over_threshold(tmp_path, employees_df, assignments_df):
    assignments_df.loc[0, "billable_raw"] = "TRUE"  # 1 of 3 = 33% > 10%
    _write_sources(tmp_path, employees_df, assignments_df)
    db = tmp_path / "w.duckdb"

    assert run(tmp_path, 0.10, db) == 1
    assert not db.exists()


def test_run_fails_cleanly_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        run(tmp_path, 0.10, tmp_path / "w.duckdb")
