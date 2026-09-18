-- An employee must appear at most once per project. A duplicate would be
-- counted twice in team_size and its hours summed twice.

select
    employee_id,
    project_code,
    count(*) as assignments
from {{ ref('stg_assignments') }}
group by employee_id, project_code
having count(*) > 1
