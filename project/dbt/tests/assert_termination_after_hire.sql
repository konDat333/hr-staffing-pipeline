-- Nobody leaves before they were hired. Mirrors the loader's contract.

select employee_id, hire_date, termination_date
from {{ ref('stg_employees') }}
where termination_date < hire_date
