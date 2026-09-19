-- Total hours in project_staffing must equal the hours of active
-- assignments. A mismatch means the mart's joins dropped or multiplied rows.

with mart as (
    select sum(total_weekly_hours) as hours from {{ ref('project_staffing') }}
),

assignments as (
    select sum(weekly_hours) as hours
    from {{ ref('int_project_assignments') }}
    where is_active
)

select mart.hours as mart_hours, assignments.hours as assignment_hours
from mart, assignments
where mart.hours is distinct from assignments.hours
