{# 取引基本表のセル。1 行が 1 表の (行部門, 列部門) 1 つ。値の無いセルと 0 のセルは持たない。
   単位はどの表も百万円にそろえている。 #}

with source as (
    select * from {{ ref('stg_transactions') }}
)

select
    source.table_id,
    source.row_code,
    r.name as row_name,
    source.col_code,
    c.name as col_name,
    source.value,
    source.source_sha256,
    source.source_sheet,
    source.source_row
from source
join {{ ref('stg_sectors') }} as r on r.table_id = source.table_id and r.side = 'row' and r.code = source.row_code
join {{ ref('stg_sectors') }} as c on c.table_id = source.table_id and c.side = 'col' and c.code = source.col_code
