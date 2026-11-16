{# ICIO の取引額。 #}

{{ config(alias='transactions') }}

select
    r.year,
    r.row_area,
    r.row_item,
    r.col_area,
    r.col_item,
    r.value,
    t.source_sha256
from {{ ref('stg_oecd_transactions') }} as r
join {{ ref('stg_oecd_tables') }} as t on t.year = r.year
