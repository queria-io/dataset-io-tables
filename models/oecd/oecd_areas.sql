{# ICIO の国・地域。pipelines/oecd.py が ReadMe から data/oecd/areas.csv に書き出す。 #}

{{ config(alias='areas') }}

select code, name
from read_csv('data/oecd/areas.csv', header = true, all_varchar = true)
