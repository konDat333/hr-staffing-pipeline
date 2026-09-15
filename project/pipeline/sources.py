"""Registry of the HR exports this pipeline knows how to read."""

from pathlib import Path

from pipeline.excel import ExcelSource

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def employees_source(data_dir: Path = DEFAULT_DATA_DIR) -> ExcelSource:
    return ExcelSource(
        path=data_dir / "hr_employees_export.xlsx",
        columns={
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
        },
    )


def assignments_source(data_dir: Path = DEFAULT_DATA_DIR) -> ExcelSource:
    return ExcelSource(
        path=data_dir / "project_assignments_report.xlsx",
        columns={
            "Assignment ID": "assignment_id",
            "Emp. ID": "employee_id",
            "Project Code": "project_code",
            "Project Name": "project_name",
            "Assignment Role": "assignment_role",
            "Start Date": "start_date",
            "Weekly Hours": "weekly_hours",
            "Billable?": "billable_raw",
        },
    )
