-- Every project should have an active lead. Known exceptions in the
-- sample data (inactive lead, no lead at all) are reported, not fatal.

{{ config(severity='warn') }}

select project_code, project_name
from {{ ref('project_staffing') }}
where lead_employee_id is null
