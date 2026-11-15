select
    cast(year as integer) as year,
    cast(edition as integer) as edition,
    source_url,
    source_file
from {{ ref('raw_oecd_tables') }}
