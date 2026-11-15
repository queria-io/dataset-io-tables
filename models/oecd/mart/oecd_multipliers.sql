{# ICIO の国×産業ごとの誘発係数。 #}

{{ config(alias='multipliers') }}

select
    m.year,
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
from {{ ref('stg_oecd_multipliers') }} as m
left join {{ ref('stg_oecd_areas') }} as a on a.code = m.area
left join {{ ref('stg_oecd_industries') }} as i on i.code = m.industry
