-- Lead ranks must not repeat within a project: this is what guarantees the
-- mart's join on lead_rank = 1 yields exactly one lead. It fails if the
-- ranking window in int_project_leads loses its partition by project_code.

select project_code, lead_rank, count(*) as candidates
from {{ ref('int_project_leads') }}
group by project_code, lead_rank
having count(*) > 1
