-- 1 行が 1 表の行部門または列部門 1 つ
select table_id, side, code, count(*) as n
from {{ ref('sectors') }}
group by all
having count(*) > 1
