-- 生産者価格評価の正方の表では、内生部門ごとに行の国内生産額 (列の計) と列の国内生産額 (行の計) が等しい
with output_col as (
    select t.table_id, t.row_code as code, t.value
    from {{ ref('transactions') }} as t
    join {{ ref('sectors') }} as s on s.table_id = t.table_id and s.side = 'col' and s.code = t.col_code
    where s.sector_type = 'output'
),

output_row as (
    select t.table_id, t.col_code as code, t.value
    from {{ ref('transactions') }} as t
    join {{ ref('sectors') }} as s on s.table_id = t.table_id and s.side = 'row' and s.code = t.row_code
    where s.sector_type = 'output'
)

select table_id, code, c.value as row_total, r.value as col_total
from output_col as c
join output_row as r using (table_id, code)
join {{ ref('tables') }} using (table_id)
where price_basis = 'producer' and sector_count is not null and abs(c.value - r.value) > 1
