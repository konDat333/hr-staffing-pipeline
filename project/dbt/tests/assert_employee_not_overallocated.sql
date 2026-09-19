-- An active employee assigned more than 40 h/week across all projects is
-- over-allocated. Valid data, but worth surfacing to whoever plans staffing.

{{ config(severity='warn') }}

select
    employee_id,
    employee_name,
    sum(weekly_hours) as total_weekly_hours
from {{ ref('int_project_assignments') }}
where is_active
group by employee_id, employee_name
having sum(weekly_hours) > 40
