-- A project code must map to exactly one project name. Two spellings would
-- split one project into two rows of project_staffing.

select
    project_code,
    count(distinct project_name) as names
from {{ ref('stg_assignments') }}
group by project_code
having count(distinct project_name) > 1
