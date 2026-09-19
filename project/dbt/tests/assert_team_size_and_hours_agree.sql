-- A project with active people must have hours and vice versa.

select project_code, team_size, total_weekly_hours
from {{ ref('project_staffing') }}
where (team_size = 0) <> (total_weekly_hours = 0)
