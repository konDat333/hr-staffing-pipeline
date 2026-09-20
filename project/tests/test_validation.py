from datetime import datetime

import pandas as pd
import pytest

from pipeline.schemas import AssignmentSchema, EmployeeSchema
from pipeline.validation import ERRORS_COLUMN, StructuralError, validate


def test_clean_frame_has_empty_quarantine_and_typed_output(employees_df, assignments_df):
    emp = validate(employees_df, EmployeeSchema)
    asg = validate(assignments_df, AssignmentSchema)

    assert emp.quarantine.empty and asg.quarantine.empty
    assert emp.invalid_share == 0
    assert pd.api.types.is_datetime64_any_dtype(emp.valid["hire_date"])
    assert pd.api.types.is_integer_dtype(asg.valid["weekly_hours"])
    assert list(emp.quarantine.columns) == list(employees_df.columns) + [ERRORS_COLUMN]


def test_bad_row_is_quarantined_with_check_name(employees_df):
    employees_df.loc[1, "email"] = "not-an-email"

    result = validate(employees_df, EmployeeSchema)

    assert list(result.valid["employee_id"]) == ["EMP-1000", "EMP-1002"]
    assert list(result.quarantine["employee_id"]) == ["EMP-1001"]
    assert "email=not-an-email" in result.quarantine.loc[0, ERRORS_COLUMN]
    assert result.invalid_share == pytest.approx(1 / 3)


def test_multiple_violations_on_one_row_are_all_reported(employees_df):
    employees_df.loc[0, "email"] = "broken"
    employees_df.loc[0, "reports_to"] = "EMP-1000"  # reports to themselves

    result = validate(employees_df, EmployeeSchema)

    errors = result.quarantine.loc[0, ERRORS_COLUMN]
    assert "email=broken" in errors
    assert "no_self_reporting" in errors
    assert "; " in errors


@pytest.mark.parametrize("status", ["ACTIVE", "active", "Active"])
def test_categorical_values_are_case_insensitive(employees_df, status):
    employees_df.loc[0, "status"] = status

    assert validate(employees_df, EmployeeSchema).quarantine.empty


def test_unknown_categorical_value_is_quarantined(employees_df, assignments_df):
    employees_df.loc[0, "status"] = "On leave"
    assignments_df.loc[0, "assignment_role"] = "Manager"
    assignments_df.loc[1, "billable_raw"] = "TRUE"

    emp = validate(employees_df, EmployeeSchema)
    asg = validate(assignments_df, AssignmentSchema)

    assert "status_in_domain" in emp.quarantine.loc[0, ERRORS_COLUMN]
    assert list(asg.quarantine["assignment_id"]) == ["ASGN-0001", "ASGN-0002"]


def test_status_must_match_termination_date(employees_df):
    employees_df.loc[0, "termination_date"] = datetime(2025, 1, 1)  # active but terminated
    employees_df.loc[2, "termination_date"] = None                  # inactive but no date

    result = validate(employees_df, EmployeeSchema)

    assert list(result.quarantine["employee_id"]) == ["EMP-1000", "EMP-1002"]
    assert all(result.quarantine[ERRORS_COLUMN].str.contains("status_matches_termination"))


def test_termination_before_hire_is_rejected(employees_df):
    employees_df.loc[2, "termination_date"] = datetime(2020, 1, 1)  # hired 2022

    result = validate(employees_df, EmployeeSchema)

    assert "termination_after_hire" in result.quarantine.loc[0, ERRORS_COLUMN]


@pytest.mark.parametrize("hours, accepted", [(0, False), (45, True), (168, True), (200, False)])
def test_weekly_hours_physical_bounds(assignments_df, hours, accepted):
    assignments_df.loc[0, "weekly_hours"] = hours

    result = validate(assignments_df, AssignmentSchema)

    assert result.quarantine.empty is accepted


def test_missing_column_is_structural_not_quarantine(employees_df):
    with pytest.raises(StructuralError):
        validate(employees_df.drop(columns=["status"]), EmployeeSchema)


def test_quarantine_keeps_original_values_as_text(assignments_df):
    assignments_df.loc[0, "weekly_hours"] = 0

    result = validate(assignments_df, AssignmentSchema)

    assert result.quarantine.loc[0, "weekly_hours"] == "0"
    assert pd.api.types.is_string_dtype(result.quarantine["weekly_hours"])
