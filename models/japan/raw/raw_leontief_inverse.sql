{# 逆行列係数（pipelines/derive.py が計算）。pipelines が書いた data/japan/leontief_inverse.csv をそのまま読む。 #}

select *
from read_csv('data/japan/leontief_inverse.csv', header = true, quote = '"', all_varchar = true)
