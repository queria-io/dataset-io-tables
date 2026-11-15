{# ICIO の国×産業ごとの誘発係数。pipelines/oecd.py が書いた data/oecd/multipliers/<year>.parquet をそのまま読む。 #}

select * from read_parquet('data/oecd/multipliers/*.parquet')
