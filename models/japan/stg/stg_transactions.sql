select
    table_id,
    row_code,
    col_code,
    cast(value as double) as value,
    source_sha256,
    source_sheet,
    cast(source_row as integer) as source_row
from {{ ref('stg_japan_parsed') }}
where part = 'cell'
