# dataset-io-tables

Queria のデータセット `io_tables`（産業連関表）のリポジトリです。データセットの説明は [docs/index.md](docs/index.md) にあります。

## ビルド

```bash
git submodule update --init
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit
```

産業連関表は 5 年ごとに出るため、定期実行はしません。main への push と手動の実行（workflow_dispatch）で Sync が実行されます。
