-- oecd スキーマのテーブルの source_sha256 が、どれも source_file の sha256 を指す
-- (transactions と multipliers は tables と同じ年の zip を指すので、tables で確認する)
select 'tables' as part, source_sha256 from {{ ref('oecd_tables') }}
where source_sha256 not in (select sha256 from {{ ref('oecd_source_file') }})
union all
select 'areas', source_sha256 from {{ ref('oecd_areas') }}
where source_sha256 not in (select sha256 from {{ ref('oecd_source_file') }})
union all
select 'industries', source_sha256 from {{ ref('oecd_industries') }}
where source_sha256 not in (select sha256 from {{ ref('oecd_source_file') }})
