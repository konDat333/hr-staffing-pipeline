"""Pandera schemas for the raw HR exports.

These are *row-level* contracts: every check here can be evaluated on a
single row in isolation (format, type, allowed values, consistency between
fields of the same row). That property is what makes quarantine possible -
a failing row can be set aside without affecting the verdict on any other.

Relational rules (uniqueness of ids, referential integrity between rows or
files, one project code -> one name) are deliberately NOT here: they are
properties of the data set, not of a row, and live in dbt tests instead.
"""

import pandera.pandas as pa
from pandera.typing.pandas import Series

EMPLOYEE_ID_PATTERN = r"^EMP-\d{4}$"
ASSIGNMENT_ID_PATTERN = r"^ASGN-\d{4}$"
PROJECT_CODE_PATTERN = r"^PROJ-\d{4}-\d{3}$"

EMPLOYEE_STATUSES = {"Active", "Inactive"}
ASSIGNMENT_ROLES = {"Lead", "Consultant", "Contributor", "Reviewer"}
# The export is inconsistent here (Y/Yes/N/No); we accept all spellings at
# the raw layer and normalise them downstream.
BILLABLE_RAW_VALUES = {"Y", "Yes", "N", "No"}


class EmployeeSchema(pa.DataFrameModel):
    employee_id: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN)
    first_name: Series[str]
    last_name: Series[str]
    email: Series[str] = pa.Field(str_matches=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    department: Series[str]
    job_title: Series[str]
    hire_date: Series[pa.DateTime]
    termination_date: Series[pa.DateTime] = pa.Field(nullable=True)
    status: Series[str] = pa.Field(isin=EMPLOYEE_STATUSES)
    reports_to: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN, nullable=True)

    class Config:
        strict = True
        coerce = True

    @pa.dataframe_check
    def termination_after_hire(cls, df) -> Series[bool]:
        terminated = df["termination_date"].notna()
        return ~terminated | (df["termination_date"] >= df["hire_date"])

    @pa.dataframe_check
    def status_matches_termination(cls, df) -> Series[bool]:
        """Inactive employees must have a termination date and vice versa."""
        return (df["status"] == "Inactive") == df["termination_date"].notna()


class AssignmentSchema(pa.DataFrameModel):
    assignment_id: Series[str] = pa.Field(str_matches=ASSIGNMENT_ID_PATTERN)
    employee_id: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN)
    project_code: Series[str] = pa.Field(str_matches=PROJECT_CODE_PATTERN)
    project_name: Series[str]
    assignment_role: Series[str] = pa.Field(isin=ASSIGNMENT_ROLES)
    start_date: Series[pa.DateTime]
    weekly_hours: Series[int] = pa.Field(gt=0, le=40)
    billable_raw: Series[str] = pa.Field(isin=BILLABLE_RAW_VALUES)

    class Config:
        strict = True
        coerce = True
