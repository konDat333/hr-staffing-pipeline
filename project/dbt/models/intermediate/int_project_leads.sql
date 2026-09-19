-- Active leads per project, ranked. lead_rank = 1 is the lead shown in marts.

select
    project_code,
    employee_id                                     as lead_employee_id,
    employee_name                                   as lead_name,
    row_number() over (
        partition by project_code
        order by is_billable desc, weekly_hours desc, assignment_id
    )                                               as lead_rank,
    count(*) over (partition by project_code)       as active_lead_count,
    is_billable,
    weekly_hours,
    assignment_id
from {{ ref('int_project_assignments') }}
where assignment_role = 'lead'
  and is_active