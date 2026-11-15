select
    table_id,
    row_code,
    col_code,
    cast("open" as double) as "open",
    cast(closed as double) as closed
from {{ ref('raw_leontief_inverse') }}
