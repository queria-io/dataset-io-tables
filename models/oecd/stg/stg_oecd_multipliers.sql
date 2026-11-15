select
    cast(year as integer) as year,
    area,
    industry,
    output,
    value_added,
    value_added_ratio,
    output_multiplier,
    domestic_output_multiplier,
    value_added_multiplier,
    domestic_value_added_multiplier
from {{ ref('raw_oecd_multipliers') }}
