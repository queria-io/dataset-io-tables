select code, name, source_sha256
from {{ ref('raw_oecd_areas') }}
