-- A single assignment above 40 h/week is unusual but not impossible
-- (overtime, contractors), so this warns instead of failing the build.
-- The physical bound (0 < hours <= 168) is enforced by the Python loader.

{{ config(severity='warn') }}

select
    assignment_id,
    employee_id,
    project_code,
    weekly_hours
from {{ ref('stg_assignments') }}
where weekly_hours > 40
