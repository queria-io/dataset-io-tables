select
    table_id,
    side,
    cast(position as integer) as position,
    code,
    name,
    source_sha256,
    source_sheet,
    cast(nullif(source_row, '') as integer) as source_row
from {{ ref('raw_sectors') }}
