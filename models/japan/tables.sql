{# 産業連関表の一覧。1 行が 1 表。pipelines/japan.py が data/japan/tables.csv に書き出す。 #}

select
    table_id,
    kind,
    nullif(series, '') as series,
    cast(year as integer) as year,
    price,
    cast(nullif(real_base_year, '') as integer) as real_base_year,
    price_basis,
    classification,
    cast(nullif(sector_count, '') as integer) as sector_count,
    concat_ws(' ',
        case kind when 'national' then year || '年 産業連関表' else series || '年 接続産業連関表 ' || year || '年' end,
        case price when 'real' then '実質（' || real_base_year || '年価格）' end,
        classification,
        case price_basis when 'producer' then '生産者価格評価' else '購入者価格評価' end
    ) as title,
    nullif(source_unit, '') as source_unit,
    source_url,
    source_sheet
from read_csv('data/japan/tables.csv', header = true, all_varchar = true)
