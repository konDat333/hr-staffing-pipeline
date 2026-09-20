-- An active employee reporting to an inactive manager is valid data (the
-- org chart just lags behind HR) but worth surfacing - warn only.

{{ config(severity='warn') }}

select
    e.employee_id,
    e.manager_employee_id,
    m.status as manager_status
from {{ ref('stg_employees') }} as e
join {{ ref('stg_employees') }} as m
    on e.manager_employee_id = m.employee_id
where e.status = 'active'
  and m.status = 'inactive'
