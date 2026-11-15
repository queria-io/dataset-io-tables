{# 産業連関表の一覧。pipelines が書いた data/japan/tables.csv をそのまま読む。 #}

select *
from read_csv('data/japan/tables.csv', header = true, quote = '"', all_varchar = true)
