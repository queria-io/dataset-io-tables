{# 産業連関表・接続産業連関表・延長産業連関表の一覧。1 行が 1 表。 #}

select * from {{ ref('stg_tables') }}
