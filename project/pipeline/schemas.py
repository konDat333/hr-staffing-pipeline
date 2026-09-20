"""Pandera schemas for the raw HR exports.

These are *row-level* contracts: every check here can be evaluated on a
single row in isolation (format, type, allowed values, consistency between
fields of the same row). That property is what makes quarantine possible -
a failing row can be set aside without affecting the verdict on any other.

Categorical values (status, role, billable flag) are validated
case-insensitively: casing is formatting, not a data error. dbt staging
canonicalises them to lower case.

Relational rules (uniqueness of ids, referential integrity between rows or
files, one project code -> one name) are deliberately NOT here: they are
properties of the data set, not of a row, and live in dbt tests instead.
"""

import pandera.pandas as pa
from pandera.typing.pandas import Series

EMPLOYEE_ID_PATTERN = r"^EMP-\d{4}$"
ASSIGNMENT_ID_PATTERN = r"^ASGN-\d{4}$"
PROJECT_CODE_PATTERN = r"^PROJ-\d{4}-\d{3}$"

EMPLOYEE_STATUSES = {"active", "inactive"}
ASSIGNMENT_ROLES = {"lead", "consultant", "contributor", "reviewer"}
# The export is inconsistent here (Y/Yes/N/No); we accept all spellings at
# the raw layer and normalise them downstream.
BILLABLE_RAW_VALUES = {"y", "yes", "n", "no"}


class EmployeeSchema(pa.DataFrameModel):
    employee_id: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN)
    first_name: Series[str]
    last_name: Series[str]
    email: Series[str] = pa.Field(str_matches=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    department: Series[str]
    job_title: Series[str]
    hire_date: Series[pa.DateTime]
    termination_date: Series[pa.DateTime] = pa.Field(nullable=True)
    status: Series[str]
    reports_to: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN, nullable=True)

    class Config:
        strict = True
        coerce = True

    @pa.check("status")
    def status_in_domain(cls, status: Series[str]) -> Series[bool]:
        return status.str.lower().isin(EMPLOYEE_STATUSES)

    @pa.dataframe_check
    def termination_after_hire(cls, df) -> Series[bool]:
        terminated = df["termination_date"].notna()
        return ~terminated | (df["termination_date"] >= df["hire_date"])

    @pa.dataframe_check
    def status_matches_termination(cls, df) -> Series[bool]:
        """Inactive employees must have a termination date and vice versa."""
        return (df["status"].str.lower() == "inactive") == df["termination_date"].notna()

    @pa.dataframe_check
    def no_self_reporting(cls, df) -> Series[bool]:
        return df["reports_to"].isna() | (df["reports_to"] != df["employee_id"])


class AssignmentSchema(pa.DataFrameModel):
    assignment_id: Series[str] = pa.Field(str_matches=ASSIGNMENT_ID_PATTERN)
    employee_id: Series[str] = pa.Field(str_matches=EMPLOYEE_ID_PATTERN)
    project_code: Series[str] = pa.Field(str_matches=PROJECT_CODE_PATTERN)
    project_name: Series[str]
    assignment_role: Series[str]
    start_date: Series[pa.DateTime]
    # Hard bound is physical (hours in a week); "<= 40" is a business
    # expectation and a warn-level dbt test, not a reason to quarantine.
    weekly_hours: Series[int] = pa.Field(gt=0, le=168)
    billable_raw: Series[str]

    class Config:
        strict = True
        coerce = True

    @pa.check("assignment_role")
    def role_in_domain(cls, role: Series[str]) -> Series[bool]:
        return role.str.lower().isin(ASSIGNMENT_ROLES)

    @pa.check("billable_raw")
    def billable_in_domain(cls, billable: Series[str]) -> Series[bool]:
        return billable.str.lower().isin(BILLABLE_RAW_VALUES)
