select
    url,
    page_url,
    sha256,
    bytes,
    media_type,
    cast(retrieved_at as timestamptz) as retrieved_at,
    etag,
    last_modified,
    file
from {{ ref('raw_oecd_source_file') }}
