select
    cast(year as integer) as year,
    cast(edition as integer) as edition,
    source_url,
    source_file,
    source_sha256
from {{ ref('raw_oecd_tables') }}
