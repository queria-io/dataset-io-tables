{# ICIO の取引額。pipelines/oecd.py が data/oecd/transactions/<year>.parquet に書き出す。 #}

{{ config(alias='transactions') }}

select
    cast(year as integer) as year,
    nullif(row_area, '') as row_area,
    row_item,
    nullif(col_area, '') as col_area,
    col_item,
    value
from read_parquet('data/oecd/transactions/*.parquet')
