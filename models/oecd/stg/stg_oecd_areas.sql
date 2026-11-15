select code, name
from {{ ref('raw_oecd_areas') }}
