-- 1 行が 1 表の (行部門, 列部門) 1 つ。部門表に無いコードは join で落ちるので、元の CSV と行数を比べる
select 'duplicate' as problem, table_id, row_code, col_code
from {{ ref('transactions') }}
group by all
having count(*) > 1
union all
select 'dropped', null, null, null
where (select count(*) from {{ ref('transactions') }})
    <> (select count(*) from read_csv('data/japan/transactions.csv', header = true, all_varchar = true))
