# Agent Skills Overview

## document-skills プラグイン pdfスキル：プロンプト例
- /pdf 以下のCSVデータを使って、月次売上レポートのPDFを作成してください。
- sales_202501.csv
- タイトル：「2025年1月 売上レポート」
- セクションは、「概要」「部門別売上」「商品別ランキング」の3つ
- 日本語フォントは、Meiryo UIを利用

## 自作スキル pdf-sales-report：入力例
- /pdf-sales-report sales_202501.csv

## document-skills プラグイン pptxスキル：プロンプト例
- /document-skills:pptx 「AIエージェントの未来」というテーマで5枚のスライドを作成してください。タイトルスライド、現状の課題、技術トレンド、ユースケース、まとめの構成でお願いします。

## 自作スキル pptx-ai-agent-deck：入力例
- cd .claude/skills/pptx-ai-agent-deck && node scripts/generate_deck.js assets/sample-content/ai-agent-future.json ../../../AIエージェントの未来.pptx
