"""産業連関表データパイプライン。

1. japan: 総務省ほかの産業連関表・接続産業連関表と経済産業省の延長産業連関表の Excel を取得し、セルを Parquet にする
2. oecd: OECD の国際産業連関表 (ICIO) を縦長の Parquet にし、誘発係数を計算する
3. dbt: dbt ビルド (Excel のセルから取引基本表を組み立て、投入係数・逆行列係数・誘発係数を計算する)
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines.japan import download_japan
from pipelines.oecd import download_oecd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("pipelines")


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        result = dbt.invoke(command)
        if not result.success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def extract():
    logger.info("1/3: japan (産業連関表・接続産業連関表・延長産業連関表)")
    download_japan()
    logger.info("2/3: oecd (ICIO)")
    download_oecd()


def main():
    extract()
    logger.info("3/3: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
