-- 表・部門・取引額の source_sha256 が、どれも source_file の sha256 を指す
select 'tables' as part, source_sha256 from {{ ref('tables') }}
where source_sha256 not in (select sha256 from {{ ref('japan_source_file') }})
union all
select distinct 'sectors', source_sha256 from {{ ref('sectors') }}
where source_sha256 not in (select sha256 from {{ ref('japan_source_file') }})
union all
select distinct 'transactions', source_sha256 from {{ ref('transactions') }}
where source_sha256 not in (select sha256 from {{ ref('japan_source_file') }})
