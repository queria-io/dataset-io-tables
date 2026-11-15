{# pipelines/japan.py が書いた data/japan/cells.parquet をそのまま読む。 #}

select * from read_parquet('data/japan/cells.parquet')
