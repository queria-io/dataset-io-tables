{# ICIO の国・地域。pipelines が書いた data/oecd/areas.csv をそのまま読む。 #}

select *
from read_csv('data/oecd/areas.csv', header = true, quote = '"', all_varchar = true)
