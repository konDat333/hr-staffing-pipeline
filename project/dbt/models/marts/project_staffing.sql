with assignments as (
    select * from {{ ref('int_project_assignments') }}
),

leads as (
    select * from {{ ref('int_project_leads') }}
    where lead_rank = 1
),

projects as (

    -- Grouping over all assignments (not only active ones) keeps projects
    -- whose whole team is inactive in the output.
    select
        project_code,
        project_name,
        count(distinct employee_id) filter (where is_active)              as team_size,
        coalesce(sum(weekly_hours)  filter (where is_active), 0)::integer as total_weekly_hours
    from assignments
    group by project_code, project_name

)

select
    p.project_code,
    p.project_name,
    l.lead_employee_id,
    l.lead_name,
    p.team_size,
    p.total_weekly_hours
from projects as p
left join leads as l
    on p.project_code = l.project_code
order by p.project_code