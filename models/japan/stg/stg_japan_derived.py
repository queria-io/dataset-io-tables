"""取引基本表から投入係数・逆行列係数・部門ごとの値を計算する。

計算方法は pipelines/derive.py。1 つの Python モデルは 1 つのテーブルしか返せないので、
投入係数 (part = 'coefficient')・逆行列係数 ('inverse')・部門ごとの値 ('multiplier') を
1 つのテーブルに縦に並べて返し、mart の input_coefficients・leontief_inverse・sector_multipliers が part で分ける。
"""

import pandas as pd

from pipelines.derive import derive_all


def model(dbt, session):
    dbt.config(materialized="table")
    coefficients, inverse, multipliers = derive_all(
        dbt.ref("stg_tables").df(),
        dbt.ref("stg_sectors").df(),
        dbt.ref("stg_transactions").df(),
    )
    return pd.concat(
        [coefficients.assign(part="coefficient"), inverse.assign(part="inverse"), multipliers.assign(part="multiplier")],
        ignore_index=True,
    )
