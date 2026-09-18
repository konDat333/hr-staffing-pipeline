-- Employee master as of the latest raw batch: renames, type casts and
-- value normalisation only. Derived columns live in the intermediate layer.
-- `email` is deliberately not selected: it is PII and nothing downstream
-- needs it (duplicates are tested on the source instead).

with latest_batch as (

    select *
    from {{ source('raw', 'employees') }}
    where _loaded_at = (select max(_loaded_at) from {{ source('raw', 'employees') }})

)

select
    employee_id,
    first_name,
    last_name,
    department,
    job_title,
    cast(hire_date as date)         as hire_date,
    cast(termination_date as date)  as termination_date,
    lower(status)                   as status,
    reports_to                      as manager_employee_id,
    _loaded_at                      as loaded_at
from latest_batch
