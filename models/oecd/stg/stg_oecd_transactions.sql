select
    cast(r.year as integer) as year,
    -- TLS・VA の行は国を持たない。主キーに NULL を置けないので、SDMX の「該当なし」の符号 _Z を入れる
    coalesce(nullif(row_area, ''), '_Z') as row_area,
    row_item,
    coalesce(nullif(col_area, ''), '_Z') as col_area,
    col_item,
    value,
    t.source_sha256
from {{ ref('raw_oecd_transactions') }} as r
join {{ ref('stg_oecd_tables') }} as t on t.year = r.year
