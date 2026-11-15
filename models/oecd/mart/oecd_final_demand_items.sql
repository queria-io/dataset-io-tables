{# ICIO の最終需要の項目。 #}

{{ config(alias='final_demand_items') }}

select * from {{ ref('stg_oecd_final_demand_items') }}
