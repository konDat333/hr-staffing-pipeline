-- Assignments enriched with the assigned employee: same grain as
-- stg_assignments, plus whether the employee is active and their name.

with employees as (
    select * from {{ ref('stg_employees') }}
),

assignments as (
    select * from {{ ref('stg_assignments') }}
)

select
    a.assignment_id,
    a.project_code,
    a.project_name,
    a.employee_id,
    e.first_name || ' ' || e.last_name  as employee_name,
    e.status = 'active'                 as is_active,
    a.assignment_role,
    a.start_date,
    a.weekly_hours,
    a.is_billable
from assignments as a
left join employees as e
    on e.employee_id = a.employee_id