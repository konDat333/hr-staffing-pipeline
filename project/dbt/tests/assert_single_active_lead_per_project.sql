-- The source should name one lead per project. When it names several we
-- pick one deterministically and warn here so the data owner can fix it.

{{ config(severity='warn') }}

select project_code, active_lead_count
from {{ ref('project_staffing') }}
where active_lead_count > 1
