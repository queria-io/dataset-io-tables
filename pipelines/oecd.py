"""OECD「Inter-Country Input-Output (ICIO) Tables」を縦長の Parquet にし、部門ごとの誘発係数を計算する。

ICIO は 81 の国・地域 (80 か国と Rest of the World) × 50 産業の国際産業連関表で、1 年が 1 つの CSV。
行は「国_産業」(AGO_A01) と TLS (純生産物税)・VA (付加価値)・OUT (産出額)、列は「国_産業」と
「国_最終需要項目」(JPN_HFCE) と OUT。金額は百万米ドル (名目)。

- transactions: 取引額。値の 0 のセルと OUT の行・列は書かない (OUT は multipliers の output)
- multipliers: 国×産業ごとの産出額・付加価値と、全世界の逆行列 L = (I - A)^-1 から求めた誘発係数
  - output_multiplier: L の列和 (全世界の生産誘発)。domestic_ は同じ国の行だけの和
  - value_added_multiplier: 付加価値率 × L の列和 (全世界の付加価値誘発)。domestic_ は同じ国の行だけの和
  逆行列そのものは 1 年 4,050 × 4,050 で大きいので収録しない

入力: 年範囲ごとの zip (1995-2000_SML.zip など) と ReadMe。OECD の配布物と同じものを R2 に置いて取る
出力: data/oecd/{areas,industries,tables}.csv、data/oecd/{transactions,multipliers}/<year>.parquet
"""

import csv
import logging
import re
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from shared.fetch import download, replacing

logger = logging.getLogger("pipelines")

EDITION = 2025
BASE_URL = f"https://webfs-sti.oecd.org/files/STI-PIE/ICIO/{EDITION}/"
# OECD の配布サーバーはブラウザ以外からの取得を拒むので、同じファイル名で R2 に置いた写しから取る
MIRROR_URL = f"https://assets.queria.io/sources/io_tables/oecd/{EDITION}/"
ARCHIVES = ["1995-2000_SML.zip", "2001-2005_SML.zip", "2006-2010_SML.zip", "2011-2015_SML.zip", "2016-2022_SML.zip"]
README = "ReadMe_ICIO_small.xlsx"
USER_AGENT = "dataset-io-tables (+https://github.com/queria-io/dataset-io-tables)"
CACHE_DIR = Path("data/raw/oecd")
OUTPUT_DIR = Path("data/oecd")
FINAL_DEMAND = {
    "HFCE": "家計最終消費支出",
    "NPISH": "対家計民間非営利団体最終消費支出",
    "GGFC": "一般政府最終消費支出",
    "GFCF": "総固定資本形成",
    "INVNT": "在庫変動",
    "DPABR": "居住者の海外での直接購入",
}


def cached(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    if not path.exists():
        logger.info("  %s", MIRROR_URL + name)
        download(MIRROR_URL + name, path, user_agent=USER_AGENT)
    return path


def read_readme() -> tuple[list[dict], list[dict]]:
    """ReadMe の Area_Activities シートから国・地域と産業の一覧を読む。

    見出しの行は「Code, Country, …, Code2, Country2, …, Code, Industry, ISIC Rev.4」。"""
    sheet = pd.read_excel(cached(README), sheet_name="Area_Activities", header=None, dtype=str)
    head = next(i for i, row in sheet.iterrows() if "Industry" in row.values)
    columns = list(sheet.iloc[head])
    pos = {name: [j for j, c in enumerate(columns) if c == name] for name in ("Code", "Country", "Code2", "Country2", "Industry", "ISIC Rev.4")}
    body = sheet.iloc[head + 1 :]
    pairs = [(pos["Code"][0], pos["Country"][0]), (pos["Code2"][0], pos["Country2"][0])]
    areas = {
        row[c]: row[n].strip()
        for _, row in body.iterrows()
        for c, n in pairs
        if isinstance(row[c], str) and re.fullmatch(r"[A-Z]{3}", row[c]) and isinstance(row[n], str)
    }
    code, name, isic = pos["Code"][1], pos["Industry"][0], pos["ISIC Rev.4"][0]
    industries = {
        row[code]: (row[name].strip(), str(row[isic]).strip())
        for _, row in body.iterrows()
        if isinstance(row[code], str) and isinstance(row[name], str)
    }
    return (
        [{"code": c, "name": n} for c, n in sorted(areas.items())],
        [{"code": c, "name": n, "isic": i} for c, (n, i) in industries.items()],
    )


def split(label: str) -> tuple[str, str]:
    """AGO_A01 → (AGO, A01)。TLS・VA・OUT は国が無い。"""
    area, _, item = label.partition("_")
    return (area, item) if item else ("", label)


def years() -> dict[int, tuple[str, str]]:
    """対象年 → (zip, CSV のファイル名)。"""
    out = {}
    for archive in ARCHIVES:
        first, last = map(int, re.match(r"(\d{4})-(\d{4})", archive).groups())
        for year in range(first, last + 1):
            out[year] = (archive, f"{year}_SML.csv")
    return out


def derive(frame: pd.DataFrame, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = [split(c) for c in frame.columns]
    rows = [split(r) for r in frame.index]
    endo = [i for i, (area, _) in enumerate(rows) if area]
    n = len(endo)
    if [frame.columns[j] for j in range(n)] != [frame.index[i] for i in endo]:
        raise SystemExit(f"{year}: 行と列の国×産業の並びが違う")
    values = frame.to_numpy(dtype=float)
    x = values[frame.index.get_loc("OUT"), :n]
    va = values[frame.index.get_loc("VA"), :n]
    with np.errstate(divide="ignore", invalid="ignore"):
        a = np.where(x > 0, values[:n, :n] / x, 0.0)
        va_ratio = np.where(x > 0, va / x, 0.0)
    inverse = np.linalg.inv(np.eye(n) - a)
    same = np.array([[ra == ca for ca, _ in labels[:n]] for ra, _ in rows[:n]])
    multipliers = pd.DataFrame({
        "year": year,
        "area": [a_ for a_, _ in labels[:n]],
        "industry": [i for _, i in labels[:n]],
        "output": x,
        "value_added": va,
        "value_added_ratio": va_ratio,
        "output_multiplier": inverse.sum(axis=0),
        "domestic_output_multiplier": (inverse * same).sum(axis=0),
        "value_added_multiplier": va_ratio @ inverse,
        "domestic_value_added_multiplier": va_ratio @ (inverse * same),
    })

    out_col = frame.columns.get_loc("OUT")
    keep_rows = [i for i, r in enumerate(frame.index) if r != "OUT"]
    keep_cols = [j for j in range(len(labels)) if j != out_col]
    sub = values[np.ix_(keep_rows, keep_cols)]
    ri, ci = np.nonzero(sub)
    transactions = pd.DataFrame({
        "year": year,
        "row_area": [rows[keep_rows[i]][0] for i in ri],
        "row_item": [rows[keep_rows[i]][1] for i in ri],
        "col_area": [labels[keep_cols[j]][0] for j in ci],
        "col_item": [labels[keep_cols[j]][1] for j in ci],
        "value": sub[ri, ci],
    })
    return transactions, multipliers


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with replacing(path) as partial:
        duckdb.from_df(frame).write_parquet(str(partial), compression="zstd")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with replacing(path) as partial, partial.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def download_oecd(output_dir: Path = OUTPUT_DIR) -> None:
    areas, industries = read_readme()
    write_csv(output_dir / "areas.csv", areas)
    write_csv(output_dir / "industries.csv", industries)
    write_csv(output_dir / "final_demand.csv", [{"code": c, "name": n} for c, n in FINAL_DEMAND.items()])
    tables = []
    for year, (archive, name) in years().items():
        with zipfile.ZipFile(cached(archive)) as z, z.open(name) as f:
            frame = pd.read_csv(f, index_col=0)
        transactions, multipliers = derive(frame, year)
        write_parquet(transactions, output_dir / "transactions" / f"{year}.parquet")
        write_parquet(multipliers, output_dir / "multipliers" / f"{year}.parquet")
        tables.append({"year": year, "edition": EDITION, "source_url": BASE_URL + archive, "source_file": name})
        logger.info("  %d: transactions %d", year, len(transactions))
    write_csv(output_dir / "tables.csv", tables)
