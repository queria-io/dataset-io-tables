{# 部門ごとの国内生産額・輸入係数・粗付加価値率・誘発係数。1 行が 1 表の 1 部門。pipelines/derive.py が計算する。 #}

with source as (
    select
        table_id,
        code,
        cast(output as double) as output,
        cast(import_coefficient as double) as import_coefficient,
        cast(value_added_ratio as double) as value_added_ratio,
        cast(output_multiplier as double) as output_multiplier,
        cast(value_added_multiplier as double) as value_added_multiplier
    from read_csv('data/japan/sector_multipliers.csv', header = true, quote = '"', all_varchar = true)
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
join {{ ref('sectors') }} as s on s.table_id = source.table_id and s.side = 'col' and s.code = source.code
