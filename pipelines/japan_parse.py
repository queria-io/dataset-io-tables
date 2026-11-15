"""産業連関表の Excel のセルから、表・部門・取引額を組み立てる。dbt の Python モデル (stg_japan_parsed) が使う。

e-Stat と総務省のサイトが配る Excel は、表ごとに見出しの行数や位置が違うが、どれも
「列部門のコードの行 → 列部門の名前の行 → (行部門のコード, 行部門の名前, 値...) の行」
という形をしている。コードの行を探し、1 セル = 1 行 (行部門 × 列部門 × 値) にする。
空欄と 0 は書かない（値の無いセルは 0）。

接続産業連関表は 1 つの Excel に 3 時点 (古い 2 時点は名目と実質) がシートで分かれて入っている。
シート名から年と名目・実質を読む。

延長産業連関表は 1 年・1 分類・名目か実質ごとに 1 つの Excel で、取引額のシートの次に逆行列のシートがある。
取引額のシート (先頭) だけを読む。

1999 年以前の延長表は基本分類 (名目) だけで、Excel には取引額の「Sheet1」と、基本分類から経済産業省の
統合分類 (小・中・大) への対応を書いた「分類表」がある。基本分類の表と、内生部門を分類表で統合分類に
集計した表を作る。最終需要と粗付加価値の部門は基本分類のまま残す。

Excel の行番号 (1 から) を source_row として部門と取引額に付ける。統合分類に集計した表の取引額は
複数の行の和なので source_row を持たない。
"""

import re
import unicodedata
from dataclasses import dataclass

import pandas as pd


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


def parse_matrix(frame: pd.DataFrame):
    """(行部門, 列部門, セル, 行部門の Excel の行番号, 列部門の見出しの Excel の行番号) を返す。
    部門は (コード, 名前)、セルは (行コード, 列コード, 値)。行番号は frame の行の位置 + 1。"""
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
    # 列部門の名前が 2 行に分かれている表 (延長表の「(控除)」の下に「輸入計」) は、続きの行を名前につなげる
    below = values[head + 2] if head + 2 < len(values) else [""] * cells.shape[1]
    names = [a + b if a == "(控除)" and is_name(b) else a for a, b in zip(values[head + 1], below)]
    # コードの無い部門 (古い表の計の行・列など) は名前をコードの代わりにする
    columns = {
        j: (values[head][j] or names[j], names[j])
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
    lines = {}
    for i, c, _ in rows:
        lines.setdefault(c, i + 1)
    return [(c, n) for _, c, n in rows], list(columns.values()), data, lines, head + 1


def classification_levels(frame: pd.DataFrame) -> list[tuple[str, dict, dict]]:
    """分類表から、統合分類ごとに (分類の名前, 行コード → (コード, 名前), 列コード → (コード, 名前)) を返す。

    分類表は「列コード, 列部門名, 行コード, 行部門名, (統合分類のコード, 統合名) ...」の形。1 つの列部門が
    複数の行部門に分かれるので、列コードは最初の行だけ書かれている表もある。大分類だけ列用と行用に分かれた
    表 (統合大分類(47部門)列・統合大分類(47部門)行) もある。コードの末尾の P (屑・副産物の行) は除く。
    分類表のコードが取引額のシートと違う部門 (1970 年基準の不動産賃貸料) があるので、部門名でも引けるようにする。"""
    values = frame.map(norm).values
    head = next(i for i in range(10) if any(v.startswith("統合") for v in values[i]))
    groups: dict[str, list[int]] = {}
    for j, v in enumerate(values[head]):
        if v.startswith("統合"):
            groups.setdefault(re.sub(r"[列行]$", "", v), []).append(j)
    digits = lambda text: re.sub(r"\D", "", text)
    levels = []
    for name, columns in groups.items():
        rows, cols = {}, {}
        for line in values[head + 2 :]:
            # 列用と行用がある分類は、行部門には最後 (行用)、列部門には最初 (列用) を使う
            row_j = next((j for j in reversed(columns) if line[j]), None)
            col_j = next((j for j in columns if line[j]), None)
            if line[2] and row_j is not None:
                rows[digits(line[2])] = rows[line[3]] = (line[row_j], line[row_j + 1])
            if line[0] and col_j is not None:
                cols.setdefault(digits(line[0]), (line[col_j], line[col_j + 1]))
                cols.setdefault(line[1], (line[col_j], line[col_j + 1]))
        levels.append((name.replace("(", "（").replace(")", "）"), rows, cols))
    return levels


def aggregate(rows, cols, data, row_map: dict, col_map: dict):
    """内生部門 (内生部門計より前) を統合分類に集計する。それ以外の部門はそのまま。"""
    def split(seq, mapping, side):
        names = [n for _, n in seq]
        k = names.index("内生部門計")
        missing = [(c, n) for c, n in seq[:k] if c not in mapping and n not in mapping]
        if missing:
            raise SystemExit(f"分類表に無い{side}部門: {missing[:5]}")
        return {c: mapping.get(c) or mapping[n] for c, n in seq[:k]}, seq[k:]

    row_to, row_rest = split(rows, row_map, "行")
    col_to, col_rest = split(cols, col_map, "列")
    # 同じコードの統合部門は名前の書き方が行ごとに違うことがあるので、コードでまとめ、名前は分類表で最初のもの
    names = dict(reversed(list(row_map.values()) + list(col_map.values())))
    order = list(dict.fromkeys(code for code, _ in row_map.values()))  # 分類表の並び
    used_rows = {code for code, _ in row_to.values()}
    used_cols = {code for code, _ in col_to.values()}
    new_rows = [(c, names[c]) for c in order if c in used_rows] + row_rest
    new_cols = [(c, names[c]) for c in order if c in used_cols] + col_rest
    sums: dict[tuple[str, str], float] = {}
    for r, c, v in data:
        key = (row_to[r][0] if r in row_to else r, col_to[c][0] if c in col_to else c)
        sums[key] = sums.get(key, 0.0) + v
    return new_rows, new_cols, [(r, c, v) for (r, c), v in sums.items() if v != 0]


def sector_count(rows: list[tuple[str, str]], cols: list[tuple[str, str]]) -> int | None:
    """内生部門の数。行と列で部門が同じ (正方の) 表だけ数える。"""
    def endogenous(seq):
        out = []
        for code, name in seq:
            if "内生部門計" in name or name == "中間需要計":  # 古い延長表の列は「中間需要計」
                return out
            out.append(code)
        return None

    r, c = endogenous(rows), endogenous(cols)
    return len(r) if r is not None and r == c else None


def table_id(source: Source, classification: str, year: int, price: str, sectors: int | None) -> str:
    # 行と列の部門が違う統合小分類 (屑の行がある) は、分類の名前の部門数を使う
    named = re.search(r"（(\d+)部門）", classification)
    size = "basic" if classification == "基本分類" else str(sectors or (named.group(1) if named else ""))
    prefix = {"national": "national", "extended": f"extended{source.series}"}.get(source.kind) or f"linked{source.series.split('-')[-1]}"
    parts = [prefix, str(year), size]
    if price == "real":
        parts.append("real")
    if source.price_basis == "purchaser":
        parts.append("purchaser")
    return "_".join(parts)


def matrices(source: Source, book: dict[str, pd.DataFrame]):
    """(シート, 分類の名前, 行部門, 列部門, セル, 行部門の行番号, 列部門の見出しの行番号) を表ごとに返す。
    統合分類に集計した表の内生部門は複数の行の和なので、行番号を持たない (最終需要・粗付加価値の部門は元の行)。"""
    if "分類表" in book:  # 1999 年以前の延長表
        rows, cols, data, lines, head = parse_matrix(book["Sheet1"])
        yield "Sheet1", source.classification, rows, cols, data, lines, head
        for name, row_map, col_map in classification_levels(book["分類表"]):
            k = [n for _, n in rows].index("内生部門計")
            rest = {c: lines[c] for c, _ in rows[k:]}
            yield "Sheet1", name, *aggregate(rows, cols, data, row_map, col_map), rest, head
        return
    for sheet, frame in list(book.items())[:1] if source.kind == "extended" else book.items():
        yield sheet, source.classification, *parse_matrix(frame)


def extract(source: Source, book: dict[str, pd.DataFrame], sha256: str):
    """1 つの Excel から (表, 部門, 取引額) を表ごとに返す。各行に元のファイル・シート・行番号を付ける。"""
    for sheet, classification, rows, cols, data, lines, head in matrices(source, book):
        if source.kind == "extended":
            year, price = source.year, source.price
        elif source.kind == "national":
            year, price = int(source.series), "nominal"
        else:
            year, price = sheet_year(sheet, source.series)
        unit = find_unit(book[sheet].iloc[:12].map(norm))
        scale = UNITS.get(unit or "百万円")
        if scale is None:
            raise SystemExit(f"{source.url} {sheet}: 単位 {unit} を想定していない")
        sectors = sector_count(rows, cols)
        tid = table_id(source, classification, year, price, sectors)
        table = {
            "table_id": tid,
            "kind": source.kind,
            "series": "" if source.kind == "national" else source.series,
            "year": year,
            "price": price,
            "real_base_year": source.series.split("-")[-1] if price == "real" else "",  # 延長表の実質は基準年の価格
            "price_basis": source.price_basis,
            "classification": classification,
            "sector_count": sectors or "",
            "source_unit": unit or "",
            "source_url": source.url,
            "source_sha256": sha256,
            "source_sheet": sheet,
        }
        origin = {"source_sha256": sha256, "source_sheet": sheet}
        sector_rows = [
            {"table_id": tid, "side": side, "position": k, "code": code, "name": name, **origin,
             "source_row": lines.get(code) if side == "row" else head}
            for side, seq in (("row", rows), ("col", cols))
            for k, (code, name) in enumerate(seq, 1)
        ]
        cells = [
            {"table_id": tid, "row_code": r, "col_code": c, "value": round(v * scale, 6), **origin, "source_row": lines.get(r)}
            for r, c, v in data
        ]
        yield table, sector_rows, cells


