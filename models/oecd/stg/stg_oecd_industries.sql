select code, name, isic
from {{ ref('raw_oecd_industries') }}
