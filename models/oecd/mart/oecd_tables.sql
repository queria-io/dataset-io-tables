{# 収録している ICIO の年の一覧。 #}

{{ config(alias='tables') }}

select * from {{ ref('stg_oecd_tables') }}
