{# 取引基本表のセル。pipelines が書いた data/japan/transactions.csv をそのまま読む。 #}

select *
from read_csv('data/japan/transactions.csv', header = true, quote = '"', all_varchar = true)
