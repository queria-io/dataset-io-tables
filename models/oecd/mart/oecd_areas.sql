{# ICIO の国・地域。 #}

{{ config(alias='areas') }}

select * from {{ ref('stg_oecd_areas') }}
