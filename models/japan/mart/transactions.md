---
$schema: https://queria.io/schemas/table/v1.json
table: japan.transactions
title: 取引基本表
description: |-
  取引基本表の値です。1 行が 1 表の行部門と列部門の組み合わせ 1 つです。

  - 金額の単位は百万円です（2020 年表は出典が 10 億円単位なので、百万円に換算しています）
  - 値の無いセルと 0 のセルは収録していません。無い組み合わせは 0 です
  - 輸入などの控除項目は負の値です
primary_key: [table_id, row_code, col_code]
fields:
  - name: table_id
    title: 表 ID
  - name: row_code
    title: 行部門コード
  - name: row_name
    title: 行部門名
  - name: col_code
    title: 列部門コード
  - name: col_name
    title: 列部門名
  - name: value
    title: 金額
    description: 百万円
    semantic: {role: measure, agg: sum}
  - name: source_sha256
    title: 元のファイル
    description: 値を読んだファイルの sha256。source_file の sha256 を指す
  - name: source_sheet
    title: 元のシート
    description: 値を読んだ Excel のシート名
  - name: source_row
    title: 元の行番号
    description: 値を読んだ Excel の行番号（1 始まり）。1999 年以前の延長表の統合分類は、内生部門の行が基本分類の複数の行の和なので NULL。最終需要・粗付加価値の行は元の行（内生部門の列は、その行の基本分類の列の和）
---
