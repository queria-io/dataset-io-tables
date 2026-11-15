select
    table_id,
    side,
    cast(position as integer) as position,
    code,
    name
from {{ ref('raw_sectors') }}
