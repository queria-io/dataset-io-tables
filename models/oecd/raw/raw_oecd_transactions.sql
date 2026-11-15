{# ICIO の取引額。pipelines/oecd.py が書いた data/oecd/transactions/<year>.parquet をそのまま読む。 #}

select * from read_parquet('data/oecd/transactions/*.parquet')
