{# pipelines/oecd.py が書いた data/oecd/source_file.ndjson をそのまま読む。 #}

select *
from read_json(
    'data/oecd/source_file.ndjson',
    format = 'newline_delimited',
    columns = {
        file: 'varchar', url: 'varchar', page_url: 'varchar', sha256: 'varchar', bytes: 'bigint',
        media_type: 'varchar', retrieved_at: 'varchar', etag: 'varchar', last_modified: 'varchar'
    }
)
