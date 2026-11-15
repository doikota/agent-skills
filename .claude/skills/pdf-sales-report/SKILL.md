---
name: pdf-sales-report
description: Generate a Japanese monthly sales report PDF (概要/部門別売上/商品別ランキング sections) from a sales CSV file, using the embedded Noto Sans JP font. Use when the user asks to create a monthly sales report PDF from CSV sales data with Japanese fonts.
---

# PDF 月次売上レポート作成スキル

CSV形式の売上データから、日本語(Noto Sans JP)フォントを埋め込んだ月次売上レポートPDFを生成する。

## 対象CSVの形式

以下の列を持つCSVファイルを想定する。

```
日付,部門,商品名,販売数量,単価,売上金額,顧客区分,地域
```

## 使い方

```bash
python .claude/skills/pdf-sales-report/scripts/generate_sales_report.py \
  <入力CSVパス> <出力PDFパス> --title "2025年1月 売上レポート"
```

依存パッケージ: `reportlab`, `pandas`(未インストールの場合は `pip install reportlab pandas`)

## 生成されるレポートの構成

1. **概要** — 総売上金額、総販売数量、集計日数、1日あたり平均売上、部門数、取扱商品数、最多売上部門/商品
2. **部門別売上** — 部門ごとの売上金額・販売数量・構成比(売上降順)
3. **商品別ランキング** — 売上金額TOP10商品(順位・商品名・売上金額・販売数量)

## フォント

`assets/fonts/NotoSansJP-Regular.ttf`(Noto Sans JP)と`assets/fonts/NotoSansJP-Bold.ttf`(太字)を同梱している。いずれも Google Fonts 配布の静的 TrueType 版で、SIL Open Font License 1.1 に基づき再配布している(ライセンス文は `assets/fonts/OFL.txt`)。ReportLab は CFF 形式(.otf)を読み込めないため、Noto 公式配布の .otf には差し替えないこと。スクリプトは自身の場所からの相対パスでフォントを参照するため、どのディレクトリから実行しても動作する。

## サンプルデータ

`assets/sample-data/` に動作確認用のサンプルCSV(`sales_202412.csv`, `sales_202501.csv`)を同梱している。

## グラフ

生成されるレポートには、部門別の売上金額を示す棒グラフと、商品別の売上金額を示す円グラフが含まれる。
