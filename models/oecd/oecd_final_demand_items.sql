{# ICIO の最終需要の項目。pipelines/oecd.py が data/oecd/final_demand.csv に書き出す。 #}

{{ config(alias='final_demand_items') }}

select code, name
from read_csv('data/oecd/final_demand.csv', header = true, quote = '"', all_varchar = true)
