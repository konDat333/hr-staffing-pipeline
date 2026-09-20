-- An employee cannot be their own manager. The relationships test would
-- accept it (the id exists), so it needs its own check.

select employee_id, manager_employee_id
from {{ ref('stg_employees') }}
where manager_employee_id = employee_id
