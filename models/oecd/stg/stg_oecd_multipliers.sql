select
    cast(r.year as integer) as year,
    area,
    industry,
    output,
    value_added,
    value_added_ratio,
    output_multiplier,
    domestic_output_multiplier,
    value_added_multiplier,
    domestic_value_added_multiplier,
    t.source_sha256
from {{ ref('raw_oecd_multipliers') }} as r
join {{ ref('stg_oecd_tables') }} as t on t.year = r.year
