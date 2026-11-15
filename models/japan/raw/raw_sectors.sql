{# 表ごとの行部門と列部門。pipelines が書いた data/japan/sectors.csv をそのまま読む。 #}

select *
from read_csv('data/japan/sectors.csv', header = true, quote = '"', all_varchar = true)
