-- 逆行列 (open) と最終需要から国内生産額を計算し直すと、元の国内生産額に戻る。
--   X = L ((I - M) D + (F - D))
-- F は最終需要計 (輸出・調整項を含む)、D は輸入係数の分母に入れた国内最終需要
-- (2011 年作成の総務省の表からは国内最終需要計から調整項を除いたもの。pipelines/derive.py と同じ)。
-- 最終需要計か国内最終需要計の列が無い表 (1985 年以前の延長表の一部) は対象にしない。
-- 公表値の丸め (2020 年表は 10 億円単位) があるので、国内生産額の 0.1% か 1,000 百万円までの差は許す
with editions as (
    select table_id, kind, cast(split_part(coalesce(series, year::varchar), '-', -1) as integer) as edition
    from {{ ref('tables') }}
),

final_demand as (
    select t.table_id, t.row_code as code,
        sum(t.value) filter (where s.name = '最終需要計') as total,
        sum(t.value) filter (where s.name = '国内最終需要計') as domestic,
        sum(t.value) filter (where s.name = '調整項') as adjustment
    from {{ ref('transactions') }} as t
    join {{ ref('sectors') }} as s on s.table_id = t.table_id and s.side = 'col' and s.code = t.col_code
    group by all
),

demand as (
    select f.table_id, f.code,
        coalesce(f.domestic, 0) - case when e.edition >= 2011 and e.kind != 'extended' then coalesce(f.adjustment, 0) else 0 end as domestic,
        coalesce(f.total, 0) as total,
        m.import_coefficient
    from final_demand as f
    join editions as e using (table_id)
    join {{ ref('sector_multipliers') }} as m on m.table_id = f.table_id and m.code = f.code
    where f.table_id in (
        select s.table_id from {{ ref('sectors') }} as s where s.side = 'col'
        group by all having count(*) filter (where s.name in ('最終需要計', '国内最終需要計')) = 2
    )
),

induced as (
    select l.table_id, l.row_code as code,
        sum(l."open" * ((1 - d.import_coefficient) * d.domestic + (d.total - d.domestic))) as value
    from {{ ref('leontief_inverse') }} as l
    join demand as d on d.table_id = l.table_id and d.code = l.col_code
    group by all
)

select i.table_id, i.code, i.value as induced, m.output
from induced as i
join {{ ref('sector_multipliers') }} as m using (table_id, code)
where abs(i.value - m.output) > greatest(0.001 * abs(m.output), 1000)
