{# ICIO の取引額。 #}

{{ config(alias='transactions') }}

select * from {{ ref('stg_oecd_transactions') }}
