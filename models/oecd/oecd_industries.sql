{# ICIO の産業。pipelines/oecd.py が ReadMe から data/oecd/industries.csv に書き出す。 #}

{{ config(alias='industries') }}

select code, name, isic
from read_csv('data/oecd/industries.csv', header = true, quote = '"', all_varchar = true)
