{# pipelines/japan.py が書いた data/japan/sources.parquet をそのまま読む。 #}

select * from read_parquet('data/japan/sources.parquet')
