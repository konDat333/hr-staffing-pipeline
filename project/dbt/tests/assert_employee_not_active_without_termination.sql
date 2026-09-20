-- Active employees must not have a termination date and inactive ones must.
-- Mirrors the loader's row-level contract so the rule holds even if raw is
-- populated some other way.

with employees as (
    select * from {{ ref('stg_employees') }}
)

select employee_id, status, termination_date
from employees
where (status = 'active') <> (termination_date is null)
