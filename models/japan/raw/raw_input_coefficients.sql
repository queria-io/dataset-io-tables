{# 投入係数（pipelines/derive.py が計算）。pipelines が書いた data/japan/input_coefficients.csv をそのまま読む。 #}

select *
from read_csv('data/japan/input_coefficients.csv', header = true, quote = '"', all_varchar = true)
