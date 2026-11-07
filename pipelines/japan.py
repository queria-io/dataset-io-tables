"""総務省ほか「産業連関表」「接続産業連関表」と経済産業省「延長産業連関表」の取引基本表を縦長の CSV にする。

e-Stat と総務省のサイトが配る Excel は、表ごとに見出しの行数や位置が違うが、どれも
「列部門のコードの行 → 列部門の名前の行 → (行部門のコード, 行部門の名前, 値...) の行」
という形をしている。コードの行を探し、1 セル = 1 行 (行部門 × 列部門 × 値) にする。
空欄と 0 は書かない（値の無いセルは 0）。

接続産業連関表は 1 つの Excel に 3 時点 (古い 2 時点は名目と実質) がシートで分かれて入っている。
シート名から年と名目・実質を読む。

延長産業連関表は 1 年・1 分類・名目か実質ごとに 1 つの Excel で、取引額のシートの次に逆行列のシートがある。
取引額のシート (先頭) だけを読む。

出力:
  data/japan/tables.csv        1 行 = 1 表
  data/japan/sectors.csv       1 行 = 1 表の行部門または列部門 1 つ
  data/japan/transactions.csv  1 行 = 1 表の 1 セル
"""

import csv
import io
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from shared.fetch import fetch, replacing

logger = logging.getLogger("pipelines")

USER_AGENT = "dataset-io-tables (+https://github.com/queria-io/dataset-io-tables)"
OUTPUT_DIR = Path("data/japan")
CACHE_DIR = Path("data/raw")
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"


@dataclass(frozen=True)
class Source:
    kind: str  # national | linked | extended
    series: str  # 全国表は年、接続表は対象の 3 時点 (2011-2015-2020)、延長表は基準年
    price_basis: str  # producer | purchaser
    classification: str  # 部門分類の名前 (統合大分類 など)
    url: str
    year: int | None = None  # 延長表の対象年
    price: str = "nominal"  # 延長表の名目・実質

    @property
    def file_id(self) -> str:
        match = re.search(r"statInfId=(\d+)", self.url)
        return match.group(1) if match else self.url.rsplit("/", 1)[-1]


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

CODE = re.compile(r"^\d{1,7}$")
NUMBER = re.compile(r"^-?[\d.,]+$")
UNITS = {"100万円": 1, "百万円": 1, "10億円": 1000, "十億円": 1000}
# 年号の 2 桁 (シート名・タイトル) → 西暦
ERA_YEARS = {
    "60": 1985, "昭和60": 1985, "2": 1990, "平成2": 1990, "7": 1995, "H7": 1995, "平成7": 1995,
    "12": 2000, "H12": 2000, "平成12": 2000, "H17": 2005, "平成17": 2005,
    "H23": 2011, "平成23": 2011, "H27": 2015, "平成27": 2015, "R02": 2020, "令和2": 2020,
}


def norm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"[\s　]", "", text)


def number(value) -> float | None:
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = norm(value).replace(",", "")
    return float(text) if NUMBER.match(text) else None


def find_unit(cells: pd.DataFrame) -> str | None:
    for text in cells.iloc[:12].values.ravel():
        match = re.search(r"単位[:：]?(\d+万円|百万円|\d+億円|十億円)", text)
        if match:
            return match.group(1)
    return None


def sheet_year(name: str, series: str) -> tuple[int, str]:
    """接続表のシート名 (６０年名目・H7実質・統合大分類平成12年 名目・R02名目) から (年, nominal|real)。"""
    text = norm(name)
    price = "real" if "実質" in text else "nominal"
    match = re.search(r"(昭和60|平成\d+|令和2|H\d+|R02|\d+)年?", re.sub(r"^(統合[大中小]分類|ひな型)", "", text))
    if not match or match.group(1) not in ERA_YEARS:
        raise SystemExit(f"{series}: シート名 {name} から年を読めない")
    year = ERA_YEARS[match.group(1)]
    if str(year) not in series.split("-"):
        raise SystemExit(f"{series}: シート {name} の年 {year} が接続表の時点に無い")
    return year, price


def parse_matrix(frame: pd.DataFrame) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str, float]]]:
    """(行部門, 列部門, セル) を返す。部門は (コード, 名前)、セルは (行コード, 列コード, 値)。"""
    cells = frame.map(norm)
    values = cells.values

    def is_name(text: str) -> bool:
        return bool(text) and not NUMBER.match(text)

    # 列部門のコードの行: 直下の行の同じ列に名前が並ぶコードが最も多い行
    def score(r: int) -> int:
        return sum(bool(CODE.match(a)) and is_name(b) for a, b in zip(values[r][2:], values[r + 1][2:]))

    head = max(range(min(30, len(values) - 1)), key=score)
    first = min(j for j in range(2, cells.shape[1]) if CODE.match(values[head][j]) and is_name(values[head + 1][j]))
    code_col = first - 2
    # コードの無い部門 (古い表の計の行・列など) は名前をコードの代わりにする
    columns = {
        j: (values[head][j] or values[head + 1][j], values[head + 1][j])
        for j in range(first, cells.shape[1])
        if is_name(values[head + 1][j]) and (CODE.match(values[head][j]) or not values[head][j])
    }
    if len(columns) < 10:
        raise SystemExit(f"列部門の見出しが見つからない (行 {head})")

    def has_values(i: int) -> bool:
        return any(number(frame.iat[i, j]) is not None for j in columns)

    rows = [
        (i, values[i][code_col] or values[i][code_col + 1], values[i][code_col + 1])
        for i in range(head + 2, len(values))
        if is_name(values[i][code_col + 1]) and (CODE.match(values[i][code_col]) or not values[i][code_col]) and has_values(i)
    ]
    data = [
        (rc, columns[j][0], v)
        for i, rc, _ in rows
        for j in columns
        if (v := number(frame.iat[i, j])) is not None and v != 0
    ]
    return [(c, n) for _, c, n in rows], list(columns.values()), data


def read_book(source: Source) -> dict[str, pd.DataFrame]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / source.file_id
    if not path.exists():
        logger.info("  %s", source.url)
        path.write_bytes(fetch(source.url, user_agent=USER_AGENT, timeout=300))
    return pd.read_excel(path, sheet_name=None, header=None, dtype=object)


def sector_count(rows: list[tuple[str, str]], cols: list[tuple[str, str]]) -> int | None:
    """内生部門の数。行と列で部門が同じ (正方の) 表だけ数える。"""
    def endogenous(seq):
        out = []
        for code, name in seq:
            if "内生部門計" in name:
                return out
            out.append(code)
        return None

    r, c = endogenous(rows), endogenous(cols)
    return len(r) if r is not None and r == c else None


def table_id(source: Source, year: int, price: str, sectors: int | None) -> str:
    size = "basic" if source.classification == "基本分類" else str(sectors or "")
    prefix = {"national": "national", "extended": "extended"}.get(source.kind) or f"linked{source.series.split('-')[-1]}"
    parts = [prefix, str(year), size]
    if price == "real":
        parts.append("real")
    if source.price_basis == "purchaser":
        parts.append("purchaser")
    return "_".join(parts)


def extract(source: Source):
    book = read_book(source)
    for sheet, frame in list(book.items())[:1] if source.kind == "extended" else book.items():
        if source.kind == "extended":
            year, price = source.year, source.price
        elif source.kind == "national":
            year, price = int(source.series), "nominal"
        else:
            year, price = sheet_year(sheet, source.series)
        rows, cols, data = parse_matrix(frame)
        unit = find_unit(frame.iloc[:12].map(norm))
        scale = UNITS.get(unit or "百万円")
        if scale is None:
            raise SystemExit(f"{source.url} {sheet}: 単位 {unit} を想定していない")
        sectors = sector_count(rows, cols)
        tid = table_id(source, year, price, sectors)
        table = {
            "table_id": tid,
            "kind": source.kind,
            "series": "" if source.kind == "national" else source.series,
            "year": year,
            "price": price,
            "real_base_year": source.series.split("-")[-1] if price == "real" else "",  # 延長表の実質は基準年の価格
            "price_basis": source.price_basis,
            "classification": source.classification,
            "sector_count": sectors or "",
            "source_unit": unit or "",
            "source_url": source.url,
            "source_sheet": sheet,
        }
        sector_rows = [
            {"table_id": tid, "side": side, "position": k, "code": code, "name": name}
            for side, seq in (("row", rows), ("col", cols))
            for k, (code, name) in enumerate(seq, 1)
        ]
        cells = [{"table_id": tid, "row_code": r, "col_code": c, "value": round(v * scale, 6)} for r, c, v in data]
        yield table, sector_rows, cells


def write_csv(path: Path, fields: list[str], rows) -> int:
    n = 0
    with replacing(path) as partial, partial.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            n += 1
    return n


def download_japan(output_dir: Path = OUTPUT_DIR) -> None:
    tables, sectors, cells = [], [], []
    for source in SOURCES:
        logger.info("%s %s %s %s", source.kind, source.series, source.price_basis, source.classification)
        for table, s, c in extract(source):
            if any(t["table_id"] == table["table_id"] for t in tables):
                raise SystemExit(f"table_id が重なった: {table['table_id']}")
            tables.append(table)
            sectors += s
            cells += c
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables.csv", list(tables[0]), tables)
    write_csv(output_dir / "sectors.csv", list(sectors[0]), sectors)
    n = write_csv(output_dir / "transactions.csv", list(cells[0]), cells)
    logger.info("  tables: %d, sectors: %d, transactions: %d", len(tables), len(sectors), n)
