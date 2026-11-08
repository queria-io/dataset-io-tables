{# 収録している ICIO の年の一覧。pipelines/oecd.py が data/oecd/tables.csv に書き出す。 #}

{{ config(alias='tables') }}

select
    cast(year as integer) as year,
    cast(edition as integer) as edition,
    source_url,
    source_file
from read_csv('data/oecd/tables.csv', header = true, quote = '"', all_varchar = true)
