select
    table_id,
    row_code,
    col_code,
    cast(value as double) as value,
    source_sha256,
    source_sheet,
    cast(nullif(source_row, '') as integer) as source_row
from {{ ref('raw_transactions') }}
