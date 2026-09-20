"""Shared fixtures: small valid frames and an Excel writer that mimics the
HR export layout (metadata rows above the header)."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from pipeline.excel import ExcelSource

EMPLOYEE_COLUMNS = {
    "Employee ID": "employee_id",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Email Address": "email",
    "Department": "department",
    "Job Title": "job_title",
    "Date of Hire": "hire_date",
    "Termination Date": "termination_date",
    "Status": "status",
    "Reports To": "reports_to",
}

ASSIGNMENT_COLUMNS = {
    "Assignment ID": "assignment_id",
    "Emp. ID": "employee_id",
    "Project Code": "project_code",
    "Project Name": "project_name",
    "Assignment Role": "assignment_role",
    "Start Date": "start_date",
    "Weekly Hours": "weekly_hours",
    "Billable?": "billable_raw",
}


@pytest.fixture
def employees_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "employee_id": ["EMP-1000", "EMP-1001", "EMP-1002"],
            "first_name": ["Angel", "Curtis", "Anna"],
            "last_name": ["Hill", "Yang", "Baldwin"],
            "email": ["angel@company.com", "curtis@company.com", "anna@company.com"],
            "department": ["Engineering", "Marketing", "Finance"],
            "job_title": ["Engineer", "Manager", "Analyst"],
            "hire_date": [datetime(2024, 4, 13), datetime(2021, 10, 13), datetime(2022, 4, 1)],
            "termination_date": [None, None, datetime(2024, 7, 23)],
            "status": ["Active", "Active", "Inactive"],
            "reports_to": ["EMP-1001", None, "EMP-1001"],
        }
    )


@pytest.fixture
def assignments_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "assignment_id": ["ASGN-0001", "ASGN-0002", "ASGN-0003"],
            "employee_id": ["EMP-1000", "EMP-1001", "EMP-1002"],
            "project_code": ["PROJ-2024-001", "PROJ-2024-001", "PROJ-2024-002"],
            "project_name": ["Platform Migration", "Platform Migration", "Mobile App"],
            "assignment_role": ["Lead", "Consultant", "Contributor"],
            "start_date": [datetime(2026, 2, 1)] * 3,
            "weekly_hours": [36, 8, 24],
            "billable_raw": ["Y", "Yes", "No"],
        }
    )


def write_excel(path: Path, columns: list[str], rows: list[list], metadata_rows: int = 3) -> Path:
    """Write an .xlsx with `metadata_rows` junk rows, then a header, then data."""
    wb = Workbook()
    ws = wb.active
    for i in range(metadata_rows):
        ws.append([f"Report line {i}"] if i < metadata_rows - 1 else [])
    ws.append(columns)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def frame_to_rows(df: pd.DataFrame) -> list[list]:
    return [[None if pd.isna(v) else v for v in row] for row in df.itertuples(index=False)]


@pytest.fixture
def employees_xlsx(tmp_path: Path, employees_df: pd.DataFrame) -> ExcelSource:
    path = write_excel(tmp_path / "employees.xlsx", list(EMPLOYEE_COLUMNS), frame_to_rows(employees_df))
    return ExcelSource(path=path, columns=EMPLOYEE_COLUMNS)


@pytest.fixture
def assignments_xlsx(tmp_path: Path, assignments_df: pd.DataFrame) -> ExcelSource:
    path = write_excel(tmp_path / "assignments.xlsx", list(ASSIGNMENT_COLUMNS), frame_to_rows(assignments_df))
    return ExcelSource(path=path, columns=ASSIGNMENT_COLUMNS)
