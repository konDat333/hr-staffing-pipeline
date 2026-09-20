from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from conftest import EMPLOYEE_COLUMNS, employees_df, frame_to_rows, write_excel
from pipeline.excel import ExcelLayoutError, ExcelSource, read_excel_source


def test_reads_export_with_metadata_rows_above_header(employees_xlsx):
    df = read_excel_source(employees_xlsx)

    assert list(df.columns) == list(EMPLOYEE_COLUMNS.values())
    assert len(df) == 3
    assert df.loc[0, "employee_id"] == "EMP-1000"


@pytest.mark.parametrize("metadata_rows", [0, 1, 6])
def test_header_is_found_regardless_of_metadata_row_count(tmp_path, employees_df, metadata_rows):
    path = write_excel(tmp_path / "e.xlsx", list(EMPLOYEE_COLUMNS), frame_to_rows(employees_df), metadata_rows)

    df = read_excel_source(ExcelSource(path=path, columns=EMPLOYEE_COLUMNS))

    assert len(df) == 3


def test_header_beyond_scan_window_is_an_error(tmp_path, employees_df):
    path = write_excel(tmp_path / "e.xlsx", list(EMPLOYEE_COLUMNS), frame_to_rows(employees_df), metadata_rows=25)

    with pytest.raises(ExcelLayoutError):
        read_excel_source(ExcelSource(path=path, columns=EMPLOYEE_COLUMNS, max_header_scan_rows=20))


def test_missing_expected_column_is_a_layout_error(tmp_path, employees_df):
    columns = [c for c in EMPLOYEE_COLUMNS if c != "Reports To"]
    rows = frame_to_rows(employees_df.drop(columns=["reports_to"]))
    path = write_excel(tmp_path / "e.xlsx", columns, rows)

    with pytest.raises(ExcelLayoutError, match="Reports To"):
        read_excel_source(ExcelSource(path=path, columns=EMPLOYEE_COLUMNS))


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_excel_source(ExcelSource(path=tmp_path / "nope.xlsx", columns=EMPLOYEE_COLUMNS))


def test_strings_are_stripped_and_blank_rows_dropped(tmp_path, employees_df):
    rows = frame_to_rows(employees_df)
    rows[0][0] = "  EMP-1000 "          # padded id
    rows[1][1] = "   "                  # whitespace-only first name -> NA
    rows.append([None] * len(rows[0]))  # trailing empty row
    path = write_excel(tmp_path / "e.xlsx", list(EMPLOYEE_COLUMNS), rows)

    df = read_excel_source(ExcelSource(path=path, columns=EMPLOYEE_COLUMNS))

    assert len(df) == 3
    assert df.loc[0, "employee_id"] == "EMP-1000"
    assert pd.isna(df.loc[1, "first_name"])


def test_extra_columns_in_file_are_ignored(tmp_path, employees_df):
    columns = list(EMPLOYEE_COLUMNS) + ["Internal Note"]
    rows = [r + ["ignore me"] for r in frame_to_rows(employees_df)]
    path = write_excel(tmp_path / "e.xlsx", columns, rows)

    df = read_excel_source(ExcelSource(path=path, columns=EMPLOYEE_COLUMNS))

    assert "Internal Note" not in df.columns
    assert list(df.columns) == list(EMPLOYEE_COLUMNS.values())
