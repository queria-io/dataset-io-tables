{# 逆行列係数。1 行が 1 表の (行部門, 列部門) 1 つ。pipelines/derive.py が計算する（stg_japan_derived）。 #}

with source as (
    select * from {{ ref('stg_japan_derived') }} where part = 'inverse'
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
join {{ ref('stg_sectors') }} as r on r.table_id = source.table_id and r.side = 'row' and r.code = source.row_code
join {{ ref('stg_sectors') }} as c on c.table_id = source.table_id and c.side = 'col' and c.code = source.col_code
