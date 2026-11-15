{# ICIO の元のファイル。 #}

{{ config(alias='source_file') }}

select url, page_url, sha256, bytes, media_type, retrieved_at, etag, last_modified, file
from {{ ref('stg_oecd_source_file') }}
order by file
