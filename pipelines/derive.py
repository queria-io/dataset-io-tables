"""取引基本表から投入係数・逆行列係数・部門ごとの誘発係数を計算する。

生産者価格評価の正方の表 (行と列の内生部門が同じ表) だけを計算する。基本分類の表は行と列の
部門が違うので計算しない。

- 投入係数 a_ij = x_ij / X_j (X_j は列部門 j の国内生産額)。内生部門の行に加えて粗付加価値の行も出す
- 逆行列係数は 2 種類
  - open: [I - (I - M)A]^-1。M は輸入係数の対角行列で、
    M_i = 輸入計_i / (内生部門計_i + 国内最終需要計_i)。総務省の計算に合わせて、2011 年表と
    平成12-17-23年接続表 (どちらも 2011 年の作成) 以降は国内最終需要計から調整項を除く。
    それより前の表と経産省の延長表は調整項を含めたまま計算する
    総務省が「逆行列係数表 [I-(I-M)A]-1」として公表しているのと同じ型
  - closed: (I - A)^-1。輸入を考えない型
- 部門ごとの値: 国内生産額・輸入係数・粗付加価値率と、open の逆行列から求めた生産誘発係数
  (列和) と粗付加価値誘発係数 (粗付加価値率 × 逆行列 の列和)

入力: data/japan/{tables,sectors,transactions}.csv
出力: data/japan/{input_coefficients,leontief_inverse,sector_multipliers}.csv
"""

import csv
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

from shared.fetch import replacing

logger = logging.getLogger("pipelines")

DIR = Path("data/japan")


def read(name: str) -> list[dict]:
    with (DIR / f"{name}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(names: dict[str, str], *candidates: str) -> str:
    """名前 → コードの表から、候補の名前のどれか 1 つのコードを返す。"""
    for name in candidates:
        if name in names:
            return names[name]
    raise KeyError(candidates)


def derive_table(table: dict, sectors: list[dict], cells: dict[tuple[str, str], float]):
    n = int(table["sector_count"])
    rows = [s for s in sectors if s["side"] == "row"]
    cols = [s for s in sectors if s["side"] == "col"]
    endo = [s["code"] for s in rows[:n]]
    row_names = {s["name"]: s["code"] for s in rows}
    col_names = {s["name"]: s["code"] for s in cols}

    output_row = one(row_names, "国内生産額", "生産額")  # 1970 年基準の延長表は「生産額」「付加価値部門計」
    va_total = one(row_names, "粗付加価値部門計", "付加価値部門計")
    endo_total = one(col_names, "内生部門計", "中間需要計")  # 古い延長表の列は「中間需要計」
    # 1985 年以前の延長表には国内最終需要計や輸入計の列が無い表がある。そのときは内訳の列を足す
    # (国内最終需要: 内生部門計の次から輸出の手前まで、輸入: 「(控除)」で始まる列。どちらも「計」の列は除く)
    names = [s["name"] for s in cols]
    start = names.index(one({n: n for n in names}, "内生部門計", "中間需要計")) + 1
    end = next(i for i in range(start, len(names)) if names[i].startswith("輸出") or names[i] == "特需")
    domestic_final = [col_names["国内最終需要計"]] if "国内最終需要計" in col_names else [cols[i]["code"] for i in range(start, end) if not names[i].endswith("計")]
    imports = [col_names["(控除)輸入計"]] if "(控除)輸入計" in col_names else [s["code"] for s in cols[start:] if s["name"].startswith("(控除)") and not s["name"].endswith("計")]
    edition = int((table["series"] or str(table["year"])).split("-")[-1])
    # 経産省の延長表は調整項を含めたまま計算している (公表の逆行列と一致する)
    adjustment = col_names.get("調整項") if edition >= 2011 and table["kind"] != "extended" else None

    # 粗付加価値の行: 内生部門計の次から粗付加価値部門計の手前まで
    positions = {s["code"]: int(s["position"]) for s in rows}
    va_rows = [s["code"] for s in rows if positions[one(row_names, "内生部門計")] < int(s["position"]) < positions[va_total]]

    get = lambda r, c: cells.get((r, c), 0.0)  # noqa: E731
    x = np.array([get(output_row, c) for c in endo])
    # 行の国内生産額 (列の計) と列の国内生産額 (行の計) が合わない表は係数を計算しない。
    # 1980 年基準の延長表 (1982〜1985 年) は、出典の事業用火力発電などの列に粗付加価値と国内生産額が無い
    output_col = one(col_names, "国内生産額", "生産額")
    unbalanced = [r for r, v in zip(endo, x) if abs(get(r, output_col) - v) > 1]
    if unbalanced:
        logger.warning("  %s: 行と列の国内生産額が合わない部門があるので係数を計算しない (%s)", table["table_id"], ", ".join(unbalanced[:5]))
        return [], [], []
    z = np.array([[get(r, c) for c in endo] for r in endo])
    with np.errstate(divide="ignore", invalid="ignore"):
        a = np.where(x > 0, z / x, 0.0)
        va = np.array([[get(r, c) for c in endo] for r in va_rows])
        va_coef = np.where(x > 0, va / x, 0.0)
        demand = np.array([get(r, endo_total) + sum(get(r, c) for c in domestic_final) - (get(r, adjustment) if adjustment else 0) for r in endo])
        m = np.where(demand != 0, -np.array([sum(get(r, c) for c in imports) for r in endo]) / demand, 0.0)
        va_ratio = np.where(x > 0, np.array([get(va_total, c) for c in endo]) / x, 0.0)

    eye = np.eye(n)
    open_inv = np.linalg.inv(eye - (eye - np.diag(m)) @ a)
    closed_inv = np.linalg.inv(eye - a)

    tid = table["table_id"]
    coefficients = [
        {"table_id": tid, "row_code": r, "col_code": c, "value": round(v, 10)}
        for codes, matrix in ((endo, a), (va_rows, va_coef))
        for i, r in enumerate(codes)
        for j, c in enumerate(endo)
        if (v := float(matrix[i, j])) != 0
    ]
    inverse = [
        {"table_id": tid, "row_code": r, "col_code": c, "open": round(float(open_inv[i, j]), 10), "closed": round(float(closed_inv[i, j]), 10)}
        for i, r in enumerate(endo)
        for j, c in enumerate(endo)
    ]
    multipliers = [
        {
            "table_id": tid,
            "code": c,
            "output": float(x[j]),
            "import_coefficient": round(float(m[j]), 10),
            "value_added_ratio": round(float(va_ratio[j]), 10),
            "output_multiplier": round(float(open_inv[:, j].sum()), 10),
            "value_added_multiplier": round(float(va_ratio @ open_inv[:, j]), 10),
        }
        for j, c in enumerate(endo)
    ]
    return coefficients, inverse, multipliers


def write_csv(path: Path, rows: list[dict]) -> None:
    with replacing(path) as partial, partial.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def derive_japan() -> None:
    tables = [t for t in read("tables") if t["sector_count"] and t["price_basis"] == "producer"]
    sectors = defaultdict(list)
    for s in read("sectors"):
        sectors[s["table_id"]].append(s)
    cells = defaultdict(dict)
    for c in read("transactions"):
        cells[c["table_id"]][(c["row_code"], c["col_code"])] = float(c["value"])

    out = ([], [], [])
    for table in tables:
        for rows, more in zip(out, derive_table(table, sectors[table["table_id"]], cells[table["table_id"]])):
            rows += more
    for name, rows in zip(("input_coefficients", "leontief_inverse", "sector_multipliers"), out):
        write_csv(DIR / f"{name}.csv", rows)
        logger.info("  %s: %d", name, len(rows))
