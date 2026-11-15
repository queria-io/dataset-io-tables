select code, name
from {{ ref('raw_oecd_final_demand_items') }}
