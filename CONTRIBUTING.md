# ビルドと更新

データセットの概要は [README.md](README.md) にあります。ここにはこのリポジトリでデータセットをビルド・更新する手順を書きます。

## ビルド

```bash
git clone https://github.com/queria-io/dataset-shared.git shared  # 更新は git -C shared pull
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit
```

産業連関表は 5 年ごとに出るため、定期実行はしません。main への push と手動の実行（workflow_dispatch）で Sync が実行されます。
