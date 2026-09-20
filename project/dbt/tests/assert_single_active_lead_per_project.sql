-- The source should name one lead per project. When it names several we
-- pick one deterministically (see int_project_leads) and warn here so the
-- data owner can fix it.

{{ config(severity='warn') }}

select project_code, active_lead_count
from {{ ref('int_project_leads') }}
where lead_rank = 1
  and active_lead_count > 1
