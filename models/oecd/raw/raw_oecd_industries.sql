{# ICIO の産業。pipelines が書いた data/oecd/industries.csv をそのまま読む。 #}

select *
from read_csv('data/oecd/industries.csv', header = true, quote = '"', all_varchar = true)
