"""Excel のセル (raw_japan_cells) から、表・部門・取引額を組み立てる。

組み立て方は pipelines/japan_parse.py。1 つの Python モデルは 1 つのテーブルしか返せないので、
表 (part = 'table')・部門 ('sector')・取引額 ('cell') を 1 つのテーブルに縦に並べて返し、
stg_tables・stg_sectors・stg_transactions が part で分ける。
"""

import numpy as np
import pandas as pd

from pipelines.japan_parse import Source, extract


def book(cells: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """1 つのファイルのセルから、pandas.read_excel(header=None, dtype=object) と同じ形のシートを作る。"""
    sheets = {}
    for (_, sheet), group in cells.sort_values("sheet_position").groupby(["sheet_position", "source_sheet"], sort=True):
        frame = np.full((group["source_row"].max(), group["source_col"].max()), np.nan, dtype=object)
        values = group["number"].astype(object).where(group["number"].notna(), group["text"])
        frame[group["source_row"].to_numpy() - 1, group["source_col"].to_numpy() - 1] = values.to_numpy()
        sheets[sheet] = pd.DataFrame(frame)
    return sheets


def model(dbt, session):
    dbt.config(materialized="table")
    cells = dbt.ref("raw_japan_cells").df()
    sources = dbt.ref("raw_japan_sources").df()
    books = {sha: book(group) for sha, group in cells.groupby("source_sha256")}
    parts = []
    for row in sources.to_dict("records"):
        year = None if pd.isna(row["year"]) else int(row["year"])
        source = Source(row["kind"], row["series"], row["price_basis"], row["classification"], row["url"], year, row["price"])
        for table, sectors, transactions in extract(source, books[row["source_sha256"]], row["source_sha256"]):
            parts += [{"part": "table", **table}]
            parts += [{"part": "sector", **s} for s in sectors]
            parts += [{"part": "cell", **c} for c in transactions]
    frame = pd.DataFrame(parts)
    for column in ("year", "sector_count", "position", "source_row"):
        frame[column] = pd.to_numeric(frame[column].replace("", None), errors="coerce").astype("Int64")
    for column in frame.columns.difference(["year", "sector_count", "position", "source_row", "value"]):
        frame[column] = frame[column].astype("string")
    return frame
