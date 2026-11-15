{# ICIO の産業。 #}

{{ config(alias='industries') }}

select * from {{ ref('stg_oecd_industries') }}
