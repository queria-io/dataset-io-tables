{# ICIO の取引額。pipelines/oecd.py が data/oecd/transactions/<year>.parquet に書き出す。 #}

{{ config(alias='transactions') }}

select
    cast(year as integer) as year,
    -- TLS・VA の行は国を持たない。主キーに NULL を置けないので、SDMX の「該当なし」の符号 _Z を入れる
    coalesce(nullif(row_area, ''), '_Z') as row_area,
    row_item,
    coalesce(nullif(col_area, ''), '_Z') as col_area,
    col_item,
    value
from read_parquet('data/oecd/transactions/*.parquet')
