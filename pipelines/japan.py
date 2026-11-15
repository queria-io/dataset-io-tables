"""総務省ほか「産業連関表」「接続産業連関表」と経済産業省「延長産業連関表」の取引基本表の Excel を取得し、
空でないセルを 1 行ずつの Parquet にする。表・部門・取引額の組み立ては dbt (stg_japan_parsed、
pipelines/japan_parse.py) が行う。

取得には shared.fetch.fetch_file を使い、取得の記録を source_file.parquet に書く。前回の記録と手元の
ファイルがあれば、ETag・Last-Modified が変わっていないときはダウンロードをスキップする。

出力:
  data/japan/source_file.parquet  1 行 = 取得した 1 ファイル (README「元のファイル」の source_file)
  data/japan/sources.parquet      1 行 = 1 つの配布物 (表の種類・時点・分類と、ファイルの sha256)
  data/japan/cells.parquet        1 行 = 1 つの空でないセル (ファイルの sha256・シート・行番号・列番号・値)
"""

import logging
from dataclasses import asdict
from pathlib import Path

import duckdb
import pandas as pd

from pipelines.japan_parse import Source
from shared.fetch import fetch_file, replacing

logger = logging.getLogger("pipelines")

USER_AGENT = "dataset-io-tables (+https://github.com/queria-io/dataset-io-tables)"
OUTPUT_DIR = Path("data/japan")
CACHE_DIR = Path("data/raw")
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"


def estat(stat_inf_id: str) -> str:
    return ESTAT.format(stat_inf_id)


def national(year: int, basis: str, files: dict[str, str]) -> list[Source]:
    return [Source("national", str(year), basis, c, estat(i)) for c, i in files.items()]


def linked(series: str, files: dict[str, str]) -> list[Source]:
    return [Source("linked", series, "producer", c, url if url.startswith("http") else estat(url)) for c, url in files.items()]


def extended(base: int, files: dict[int, dict[str, str]]) -> list[Source]:
    """延長表。files は 対象年 → {"中分類": 名目の statInfId, "中分類実質": 実質の statInfId, ...}。"""
    names = {"大分類": "統合大分類", "中分類": "統合中分類"}
    return [
        Source("extended", str(base), "producer", names[key.removesuffix("実質")], estat(i), year, "real" if key.endswith("実質") else "nominal")
        for year, ids in files.items()
        for key, i in ids.items()
    ]


METI = "https://www.meti.go.jp/statistics/tyo/"
# 経産省のサイトはプログラムからの取得を拒むので、同じパスで R2 に置いた写しから取る
METI_MIRROR = "https://assets.queria.io/sources/io_tables/meti/"


def meti(base: int, small: str, large: str, files: dict[int, tuple[str, str, str, str]], simple: bool = False) -> list[Source]:
    """経済産業省のサイトにだけある延長表 (2011 年以前と簡易延長表)。
    files は 対象年 → (小さい分類の名目, 実質, 大きい分類の名目, 実質) の METI からのパス。"""
    note = "（簡易延長表）" if simple else ""
    kinds = ((small, "nominal"), (small, "real"), (large, "nominal"), (large, "real"))
    return [
        Source("extended", str(base), "producer", classification + note, METI + path, year, price)
        for year, paths in files.items()
        for (classification, price), path in zip(kinds, paths)
        if path
    ]


def basic(base: int, prefix: str, years: list[int]) -> list[Source]:
    """1999 年以前の延長表 (基本分類、名目)。ファイル名の年は和暦 (s48 = 昭和48年、h04 = 平成4年)。"""
    era = lambda year: f"s{year - 1925}" if year < 1989 else f"h{year - 1988:02d}"
    return [Source("extended", str(base), "producer", "基本分類", f"{METI}entyoio/result/base_{prefix}/{prefix}_{era(year)}uio.xlsx", year) for year in years]


def ids(*values: str) -> dict[str, str]:
    """(大分類 名目, 大分類 実質, 中分類 名目, 中分類 実質) の statInfId。"""
    return dict(zip(("大分類", "大分類実質", "中分類", "中分類実質"), values))


SOURCES = [
    *national(1995, "producer", {"13部門": "000000750001", "大分類（32部門）": "000000750002", "中分類（94部門）": "000000750003"}),
    *national(1995, "purchaser", {"13部門": "000000750004", "大分類（32部門）": "000000750005", "中分類（94部門）": "000000750006"}),
    *national(2000, "producer", {"中分類（104部門）": "000004712755", "大分類（32部門）": "000004712756"}),
    *national(2000, "purchaser", {"中分類（104部門）": "000004712757", "大分類（32部門）": "000004712758"}),
    *national(2005, "producer", {"中分類（108部門）": "000002568523", "大分類（34部門）": "000002568524", "13部門": "000014890374"}),
    *national(2005, "purchaser", {"中分類（108部門）": "000002568525", "大分類（34部門）": "000002568526", "13部門": "000014890375"}),
    *national(2011, "producer", {
        "基本分類": "000030137963", "統合小分類（190部門）": "000030137964", "統合中分類（108部門）": "000030137965",
        "統合大分類（37部門）": "000030137966", "13部門分類": "000030137967",
    }),
    *national(2011, "purchaser", {"統合中分類（108部門）": "000030137968", "統合大分類（37部門）": "000030137969", "13部門分類": "000030137970"}),
    *national(2015, "producer", {
        "基本分類": "000031839445", "統合小分類（187部門）": "000031839446", "統合中分類（107部門）": "000031839447",
        "統合大分類（37部門）": "000031839448", "13部門分類": "000031839449",
    }),
    *national(2015, "purchaser", {"統合中分類（107部門）": "000031839450", "統合大分類（37部門）": "000031839451", "13部門分類": "000031839452"}),
    *national(2020, "producer", {
        "基本分類": "000040187024", "統合小分類（188部門）": "000040187025", "統合中分類（108部門）": "000040187026",
        "統合大分類（37部門）": "000040187027", "13部門分類": "000040187028",
    }),
    *national(2020, "purchaser", {
        "基本分類": "000040187029", "統合小分類（188部門）": "000040187030", "統合中分類（108部門）": "000040187031",
        "統合大分類（37部門）": "000040187032", "13部門分類": "000040187033",
    }),
    *linked("1985-1990-1995", {"13部門": "000000750032", "32部門": "000000750033", "184部門": "000000750034"}),
    *linked("1990-1995-2000", {"13部門": "000000750046", "32部門": "000000750047", "99部門": "000000750048"}),
    *linked("1995-2000-2005", {"102部門": "000007517197", "34部門": "000007517198"}),
    *linked("2000-2005-2011", {"統合中分類（105部門）": "000031413705", "統合大分類（37部門）": "000031413706", "13部門分類": "000031413707"}),
    *linked("2005-2011-2015", {"統合中分類（105部門）": "000031974825", "統合大分類（37部門）": "000031974826", "13部門分類": "000031974827"}),
    *linked("2011-2015-2020", {"基本分類": "https://www.soumu.go.jp/main_content/001019115.xlsx"}),
    *basic(1970, "s45", [1973, 1974, 1975, 1976]),
    *basic(1975, "s50", [1977, 1978, 1979, 1980, 1981]),
    *basic(1980, "s55", [1982, 1983, 1984, 1985]),
    *basic(1985, "s60", [1986, 1987, 1988, 1989, 1990, 1991]),
    *basic(1990, "h02", [1992, 1993, 1994, 1995]),
    *basic(1995, "h07", [1996, 1997, 1998, 1999]),
    *meti(1995, "50部門", "71部門", simple=True, files={
        year: tuple(f"entyoio/result/base_h07/h07_h{year - 1988}puio{n}{p}.xlsx" for n in (50, 71) for p in "nr")
        for year in (2000, 2001, 2002)
    }),
    *meti(2000, "50部門", "73部門", simple=True, files={
        2003: tuple(f"kanieio/result/result_4/xls/h2uio03{i}j.xls" for i in (4, 5, 6, 7)),
        2008: tuple(f"kanieio/result/result_9/xls/h2uio08{i}j.xls" for i in (1, 2, 3, 4)),
    }),
    *meti(2000, "50部門", "", files={
        year: (f"entyoio/result/base_h12/h12_h{year - 1988}uio50n.xlsx", f"entyoio/result/base_h12/h12_h{year - 1988}uio50r.xlsx", "", "")
        for year in (2004, 2005, 2006, 2007)
    }),
    *meti(2005, "統合大分類", "統合中分類", files={
        2008: tuple(f"entyoio/result/result_12/xls/h2eio08{i}j.xls" for i in (1, 2, 3, 4)),
        2009: tuple(f"entyoio/result/result_13/xls/h2eio09{i}j.xls" for i in (2, 3, 4, 5)),
        2010: tuple(f"entyoio/result/result_14/xls/h2eio10{i}j.xls" for i in (2, 3, 4, 5)),
        2011: tuple(f"entyoio/result/result_15/xls/H23eio{n}{p}pj.xls" for n in (53, 80) for p in "nr"),
    }),
    *meti(2005, "統合大分類", "統合中分類", simple=True, files={
        2012: tuple(f"kanieio/result/result_13/xls/h2uio12{i}j.xls" for i in (3, 4, 6, 7)),
    }),
    *extended(2011, {
        2012: ids("000031752546", "000031752547", "000031752548", "000031752549"),
        2013: ids("000031752556", "000031752557", "000031752558", "000031752559"),
        2014: ids("000031752566", "000031752567", "000031752568", "000031752569"),
        2015: ids("000031752576", "000031752577", "000031752578", "000031752579"),
    }),
    *extended(2015, {
        2016: ids("000031930676", "000031930677", "000031930678", "000031930679"),
        2017: ids("000032047342", "000032047343", "000032047344", "000032047345"),
        2018: ids("000032112537", "000032112538", "000032112539", "000032112540"),
        2019: ids("000032229143", "000032229144", "000032229141", "000032229142"),
        2020: ids("000040106266", "000040106267", "000040106264", "000040106265"),
    }),
    *extended(2020, {
        2021: ids("000040387832", "000040387833", "000040387830", "000040387831"),
        2022: ids("000040503552", "000040503773", "000040503550", "000040503551"),
    }),
]


def fetch_url(source: Source) -> str:
    return source.url.replace(METI, METI_MIRROR)


def previous_records(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    frame = duckdb.sql(f"SELECT * EXCLUDE (page_url) FROM read_parquet('{path}')").df()
    return {r["url"]: r for r in frame.astype(object).where(frame.notna(), None).to_dict("records")}


def cells(path: Path, sha256: str) -> pd.DataFrame:
    """Excel の空でないセル。行番号・列番号は 1 から (pandas の行・列の位置 + 1)。
    数値のセルは number に、それ以外は text に入れる。シートの順番も sheet_position に持つ。"""
    frames = []
    book = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    for position, (sheet, frame) in enumerate(book.items(), 1):
        stacked = frame.stack().dropna()
        values = stacked.to_list()
        is_number = [isinstance(v, (int, float)) and not isinstance(v, bool) for v in values]
        frames.append(
            pd.DataFrame(
                {
                    "source_sha256": sha256,
                    "source_sheet": sheet,
                    "sheet_position": position,
                    "source_row": stacked.index.get_level_values(0).to_numpy() + 1,
                    "source_col": stacked.index.get_level_values(1).to_numpy() + 1,
                    "text": [None if n else str(v) for v, n in zip(values, is_number)],
                    "number": [float(v) if n else None for v, n in zip(values, is_number)],
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    with replacing(path) as partial:
        duckdb.from_df(frame).write_parquet(str(partial), compression="zstd")


def download_japan(output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    previous = previous_records(output_dir / "source_file.parquet")
    records, sources, sheets = {}, [], {}
    for source in SOURCES:
        url = fetch_url(source)
        logger.info("%s %s %s %s", source.kind, source.series, source.price_basis, source.classification)
        record = fetch_file(url, CACHE_DIR / source.file_id, previous=previous.get(url), user_agent=USER_AGENT, timeout=300)
        records[url] = record
        sources.append({**asdict(source), "source_sha256": record["sha256"]})
        if record["sha256"] not in sheets:
            sheets[record["sha256"]] = cells(CACHE_DIR / source.file_id, record["sha256"])
    source_file = pd.DataFrame([{"page_url": None, **r} for r in records.values()])
    source_file["retrieved_at"] = pd.to_datetime(source_file["retrieved_at"], utc=True)
    write_parquet(output_dir / "source_file.parquet", source_file)
    write_parquet(output_dir / "sources.parquet", pd.DataFrame(sources))
    all_cells = pd.concat(sheets.values(), ignore_index=True)
    write_parquet(output_dir / "cells.parquet", all_cells)
    logger.info("  files: %d, sources: %d, cells: %d", len(records), len(sources), len(all_cells))
