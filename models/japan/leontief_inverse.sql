{# 逆行列係数。1 行が 1 表の (行部門, 列部門) 1 つ。pipelines/derive.py が計算する。 #}

with source as (
    select
        table_id,
        row_code,
        col_code,
        cast("open" as double) as "open",
        cast(closed as double) as closed
    from read_csv('data/japan/leontief_inverse.csv', header = true, quote = '"', all_varchar = true)
)

select
    source.table_id,
    source.row_code,
    r.name as row_name,
    source.col_code,
    c.name as col_name,
    source."open",
    source.closed
from source
join {{ ref('sectors') }} as r on r.table_id = source.table_id and r.side = 'row' and r.code = source.row_code
join {{ ref('sectors') }} as c on c.table_id = source.table_id and c.side = 'col' and c.code = source.col_code
