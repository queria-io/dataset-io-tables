{# 収録している ICIO の年の一覧。pipelines が書いた data/oecd/tables.csv をそのまま読む。 #}

select *
from read_csv('data/oecd/tables.csv', header = true, quote = '"', all_varchar = true)
