{# ICIO の国×産業ごとの誘発係数。pipelines/oecd.py が data/oecd/multipliers/<year>.parquet に書き出す。 #}

{{ config(alias='multipliers') }}

select
    cast(m.year as integer) as year,
    m.area,
    a.name as area_name,
    m.industry,
    i.name as industry_name,
    m.output,
    m.value_added,
    m.value_added_ratio,
    m.output_multiplier,
    m.domestic_output_multiplier,
    m.value_added_multiplier,
    m.domestic_value_added_multiplier
from read_parquet('data/oecd/multipliers/*.parquet') as m
left join {{ ref('oecd_areas') }} as a on a.code = m.area
left join {{ ref('oecd_industries') }} as i on i.code = m.industry
