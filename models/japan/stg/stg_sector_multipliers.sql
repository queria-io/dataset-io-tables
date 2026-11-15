select
    table_id,
    code,
    cast(output as double) as output,
    cast(import_coefficient as double) as import_coefficient,
    cast(value_added_ratio as double) as value_added_ratio,
    cast(output_multiplier as double) as output_multiplier,
    cast(value_added_multiplier as double) as value_added_multiplier
from {{ ref('raw_sector_multipliers') }}
