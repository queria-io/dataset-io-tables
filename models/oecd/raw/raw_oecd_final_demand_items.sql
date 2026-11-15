{# ICIO の最終需要の項目。pipelines が書いた data/oecd/final_demand.csv をそのまま読む。 #}

select *
from read_csv('data/oecd/final_demand.csv', header = true, quote = '"', all_varchar = true)
