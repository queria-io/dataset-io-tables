select code, name, isic, source_sha256
from {{ ref('raw_oecd_industries') }}
