# 産業連関表

日本の産業連関表・接続産業連関表・延長産業連関表と、OECD の国際産業連関表（ICIO）を、SQL で集計できるテーブルにしたデータセットです。取引基本表を 1 行が 1 セルの縦長のテーブルにし、投入係数・逆行列係数・部門ごとの誘発係数も計算して収録しています。

## 出典と利用条件

総務省ほか 10 府省庁が作成する「産業連関表」と「接続産業連関表」、経済産業省が作成する「延長産業連関表」の取引基本表を、e-Stat・総務省・経済産業省のサイトが配布する Excel から取り込んでいます。

- [産業連関表（総務省）](https://www.soumu.go.jp/toukei_toukatsu/data/io/index.htm)
- [e-Stat 産業連関表](https://www.e-stat.go.jp/stat-search/files?toukei=00200603)
- [延長産業連関表（経済産業省）](https://www.meti.go.jp/statistics/tyo/entyoio/index.html)
- [e-Stat 延長産業連関表](https://www.e-stat.go.jp/stat-search/files?toukei=00550425)

どちらも[政府標準利用規約（第2.0版）](https://www.digital.go.jp/resources/open_data/)に準拠した利用条件で提供されています。使うときは出典として表の名前を書き、Queria が加工したものであることを明記してください。

`oecd` スキーマは、OECD の [Inter-Country Input-Output (ICIO) Tables](https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html) 2025 年版（small version）から作っています。[OECD の利用条件](https://www.oecd.org/en/about/terms-conditions.html)に従い、商用を含めて利用できます。使うときは「OECD (2025), Inter-Country Input-Output Database, http://oe.cd/icio」と出典を書いてください。

経済産業省のサイトと OECD の配布サーバーは自動の取得を受け付けないため、配布されているファイルをそのまま `https://assets.queria.io/sources/io_tables/` に置き、ビルドはそこから取得しています（パスとファイル名は出典と同じです。1 回でアップロードできない大きさの ICIO の zip は、分割した `.part00` などのファイルとして置いています）。

## 収録範囲

| 種類 | 年 | 部門分類 |
| --- | --- | --- |
| 産業連関表（`kind = 'national'`） | 1995・2000・2005・2011・2015・2020 | 13 部門から 190 部門までの統合分類、2011 年以降は基本分類も |
| 接続産業連関表（`kind = 'linked'`） | 1985〜2020（6 つの接続表、それぞれ 3 時点） | 13 部門から 184 部門、平成23-27-令和2年接続表は基本分類だけ |
| 延長産業連関表（`kind = 'extended'`） | 2000〜2022 の毎年 | 50〜54 部門と 71〜98 部門。2000〜2003・2008（平成12年基準）・2012（平成17年基準）は簡易延長表 |

- 価格の評価は生産者価格評価と購入者価格評価の両方を収録しています（購入者価格評価は出典にある表だけ）
- 接続表の古い 2 時点には、名目の表と実質（最新時点の価格）の表があります
- 延長表には名目の表と実質（基準年の価格）の表があります。`series` が延長表の基準年で、同じ基準年の延長表は部門分類が同じです
- 1990 年以前の産業連関表は、総務省が報告書の PDF だけで公表しているため収録していません。1985 年と 1990 年は接続表で使えます
- 2008 年と 2012 年は、基準年の違う 2 つの延長表があります（`series` で区別します）
- 1999 年以前の延長表は、経済産業省が基本分類の表だけを公表しているため、まだ収録していません
- OECD ICIO は 1995〜2022 年の毎年、81 の国・地域（80 か国と Rest of the World）× 50 産業です。金額は百万米ドル（名目）です

## テーブル

| テーブル | 内容 |
| --- | --- |
| `japan.tables` | 表の一覧。1 行が 1 表 |
| `japan.sectors` | 表ごとの行部門と列部門 |
| `japan.transactions` | 取引基本表の値。1 行が 1 表の (行部門, 列部門) 1 つ。単位は百万円 |
| `japan.input_coefficients` | 投入係数 |
| `japan.leontief_inverse` | 逆行列係数。`open` が [I-(I-M)A]^-1 型、`closed` が (I-A)^-1 型 |
| `japan.sector_multipliers` | 部門ごとの国内生産額・輸入係数・粗付加価値率・生産誘発係数・粗付加価値誘発係数 |
| `oecd.tables` | ICIO の年の一覧 |
| `oecd.areas` / `oecd.industries` / `oecd.final_demand_items` | 国・地域、産業、最終需要の項目 |
| `oecd.transactions` | ICIO の取引額。1 行が 1 年の (行, 列) 1 つ。単位は百万米ドル |
| `oecd.multipliers` | 国×産業ごとの産出額・付加価値と、全世界の逆行列 (I-A)^-1 から計算した誘発係数（全世界と国内） |

係数と逆行列は、生産者価格評価で行と列の部門が同じ表（`tables.sector_count` がある表）だけ計算しています。ICIO の逆行列は 1 年 4,050 × 4,050 と大きいため収録せず、誘発係数だけを収録しています。

## 使い方

2020 年表（37 部門）で、飲食料品の最終需要が 100 億円（10,000 百万円）増えたときの生産の増加:

```sql
SELECT row_name, round(sum("open" * d.amount)) AS induced
FROM io_tables.japan.leontief_inverse
JOIN (VALUES ('11', 10000.0)) AS d(code, amount) ON col_code = d.code
WHERE table_id = 'national_2020_37'
GROUP BY row_name
ORDER BY induced DESC;
```

取引基本表を横長の行列の形で見る（列は名前順に並びます）:

```sql
PIVOT (
    SELECT row_name, col_name, value
    FROM io_tables.japan.transactions
    WHERE table_id = 'national_2020_13'
)
ON col_name USING sum(value);
```

同じ部門分類で年を比べるときは、接続表か延長表（`series` が同じ表）を使います:

```sql
SELECT t.year, m.name, m.output_multiplier
FROM io_tables.japan.sector_multipliers AS m
JOIN io_tables.japan.tables AS t USING (table_id)
WHERE t.series = '2005-2011-2015' AND t.sector_count = 37 AND t.price = 'nominal'
ORDER BY m.name, t.year;
```

日本の自動車産業の最終需要 1 単位が、どれだけの付加価値を国内と海外で生むか（ICIO）:

```sql
SELECT year, value_added_multiplier, domestic_value_added_multiplier,
       value_added_multiplier - domestic_value_added_multiplier AS foreign
FROM io_tables.oecd.multipliers
WHERE area = 'JPN' AND industry = 'C29'
ORDER BY year;
```

2022 年に日本の産業が中間投入に使った輸入品を、輸入元の国ごとに集計する:

```sql
SELECT a.name, round(sum(value)) AS million_usd
FROM io_tables.oecd.transactions AS t
JOIN io_tables.oecd.areas AS a ON a.code = t.row_area
WHERE year = 2022 AND col_area = 'JPN' AND row_area <> 'JPN'
  AND col_item IN (SELECT code FROM io_tables.oecd.industries)
GROUP BY a.name
ORDER BY million_usd DESC;
```

## 注意

- 部門のコードは表ごとに違います。年をまたいで比べるときは接続表を使うか、部門名で確認してください
- 値の無いセルと 0 のセルは `transactions` に収録していません
- 輸入係数 M は 輸入計 ÷ (内生部門計 + 国内最終需要計) です。総務省の計算に合わせ、2011 年以降に作成された総務省の表（2011 年表と平成12-17-23年接続表以降）からは国内最終需要計から調整項を除いています。延長表は経済産業省の計算に合わせて調整項を含めています
- 計算した逆行列係数は、公表されている逆行列係数表と 1995〜2015 年の表で小数点以下 6 桁まで一致します。2020 年表は出典の取引額が 10 億円単位に丸められているため、最大で 0.002 ほど違います
- 延長表の逆行列係数は、出典の Excel にある逆行列と小数点以下 9 桁まで一致します（2012・2013 年の平成23年基準の実質の表など一部は最大 0.00006 違います）。ただし 2010 年の統合大分類（53 部門、名目）と、平成23年基準の 2012 年の統合大分類（54 部門、名目）は、出典の逆行列が同じ Excel の取引額から計算した値とそれぞれ最大 0.16 と 0.06 違います（2012 年の表には 2013 年の表の逆行列に近い値が載っています）。このデータセットは取引額から計算した値を収録しています
- 1995 年表の購入者価格評価表は、出典の国内生産額の列が生産者価格評価表と一致しません。出典のまま収録しています

## ビルド

```bash
git submodule update --init
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit
```

産業連関表は 5 年ごとに出るため、定期実行はしません。main への push と手動の実行（workflow_dispatch）で Sync が実行されます。
