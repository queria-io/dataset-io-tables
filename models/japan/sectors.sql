{# 表ごとの行部門と列部門。1 行が 1 表の 1 部門。pipelines/japan.py が data/japan/sectors.csv に書き出す。 #}

with source as (
    select
        table_id,
        side,
        cast(position as integer) as position,
        code,
        name
    from read_csv('data/japan/sectors.csv', header = true, quote = '"', all_varchar = true)
),

marks as (
    select
        table_id,
        side,
        -- 古い延長表は列の内生部門計を「中間需要計」と書いている
        min(position) filter (where name in ('内生部門計', '中間需要計')) as endogenous_total,
        -- 1970 年基準の延長表は行の国内生産額を「生産額」と書いている
        coalesce(min(position) filter (where name = '国内生産額'), min(position) filter (where name = '生産額')) as output
    from source
    group by table_id, side
)

select
    source.table_id,
    source.side,
    source.position,
    source.code,
    source.name,
    case
        when source.position < marks.endogenous_total then 'intermediate'
        when source.position = marks.endogenous_total then 'intermediate_total'
        when source.position = marks.output then 'output'
        when source.position > marks.output then 'reference'
        when source.side = 'col' then 'final_demand'
        else 'value_added'
    end as sector_type,
    source.name like '%計' or source.name like '%合計' as is_total
from source
join marks using (table_id, side)
