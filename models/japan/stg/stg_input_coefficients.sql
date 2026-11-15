select
    table_id,
    row_code,
    col_code,
    cast(value as double) as value
from {{ ref('raw_input_coefficients') }}
