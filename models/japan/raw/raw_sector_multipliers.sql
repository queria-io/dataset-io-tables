{# 部門ごとの誘発係数（pipelines/derive.py が計算）。pipelines が書いた data/japan/sector_multipliers.csv をそのまま読む。 #}

select *
from read_csv('data/japan/sector_multipliers.csv', header = true, quote = '"', all_varchar = true)
