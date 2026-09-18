-- Project assignments as of the latest raw batch: renames, type casts and
-- value normalisation only. Derived columns live in the intermediate layer.
-- The source spells the billable flag four ways (Y/Yes/N/No); it becomes a
-- boolean here so nothing downstream has to know about that.

with latest_batch as (

    select *
    from {{ source('raw', 'assignments') }}
    where _loaded_at = (select max(_loaded_at) from {{ source('raw', 'assignments') }})

)

select
    assignment_id,
    employee_id,
    project_code,
    project_name,
    lower(assignment_role)          as assignment_role,
    cast(start_date as date)        as start_date,
    cast(weekly_hours as integer)   as weekly_hours,
    case lower(billable_raw)
        when 'y'   then true
        when 'yes' then true
        when 'n'   then false
        when 'no'  then false
    end                             as is_billable,
    _loaded_at                      as loaded_at
from latest_batch
