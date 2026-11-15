{{ config(alias='source_file') }}

select url, page_url, sha256, bytes, media_type, retrieved_at, etag, last_modified
from {{ ref('stg_japan_source_file') }}
order by url, retrieved_at
