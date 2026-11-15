{# 部門ごとの国内生産額・輸入係数・粗付加価値率・誘発係数。1 行が 1 表の 1 部門。pipelines/derive.py が計算する（raw_sector_multipliers）。 #}

with source as (
    select * from {{ ref('stg_sector_multipliers') }}
)

select
    source.table_id,
    source.code,
    s.name,
    source.output,
    source.import_coefficient,
    source.value_added_ratio,
    source.output_multiplier,
    source.value_added_multiplier
from source
join {{ ref('stg_sectors') }} as s on s.table_id = source.table_id and s.side = 'col' and s.code = source.code
