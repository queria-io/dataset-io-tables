{# pipelines/japan.py が書いた data/japan/source_file.parquet をそのまま読む。 #}

select * from read_parquet('data/japan/source_file.parquet')
