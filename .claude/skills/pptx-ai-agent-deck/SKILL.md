---
name: pptx-ai-agent-deck
description: Generate a themed 5-slide Japanese business presentation (title / 課題 / トレンド / ユースケース / まとめ) as a .pptx, using a navy-indigo tech palette with an icon-in-circle motif. Use when the user asks to create a PowerPoint deck about AI agents (or a similarly structured topic — current challenges, technology trends, use cases, summary) from JSON content.
---

# PPTX AIエージェント系デッキ作成スキル

「タイトル」「現状の課題」「技術トレンド」「ユースケース」「まとめ」の5枚構成で、紺色×インディゴのテック配色・アイコン円モチーフで統一したプレゼンテーションPPTXを生成する。

## 使い方

```bash
cd .claude/skills/pptx-ai-agent-deck
node scripts/generate_deck.js <content.json> <出力PPTXパス>
```

依存パッケージ: `pptxgenjs`, `react`, `react-dom`, `react-icons`, `sharp`(未インストールの場合は、このディレクトリで `npm install`)

## content.json の形式

`assets/sample-content/ai-agent-future.json` を参照。トップレベルは以下の構造。

- `title` / `titleEn` / `titleIcon` / `subtitle` / `date` — タイトルスライド
- `sections` — 中間3枚のスライド。各要素は `heading`, `subheading`, `layout`, `items`(2〜4件、各 `icon`/`title`/`body`) を持つ
  - `layout: "cards-2x2-light"` — 白背景に2x2カード、円アイコンは紺地に白抜き（例: 課題スライド）
  - `layout: "cards-2x2-dark"` — 白背景に紺色2x2カード、円アイコンはアクセント色地に白抜き（例: ユースケーススライド）
  - `layout: "icon-rows"` — 白背景に4行のアイコン+テキスト（例: トレンドスライド）
- `summary` — 最終スライド（紺背景）。`heading`, `subheading`, `pointIcon`, `points`(2〜3件、`title`/`body`), `taglineIcon`, `tagline`

`sections` はちょうど3件、`points` は最大3件を想定（超過分は描画されない）。

### 使えるアイコン名

`cpu`, `alert-triangle`, `shield`, `eye`, `dollar-sign`, `users`, `tool`, `database`, `target`, `headphones`, `code`, `settings`, `search`, `check-circle`, `arrow-up-right`, `zap`, `trending-up`, `globe`, `layers`, `clock`（`react-icons/fi` の Feather アイコン。未対応の名前を指定するとスクリプトがエラーで一覧を表示する）

## デザイン

- 配色: 紺（`141B4D`, 支配色）× 淡いアイスラベンダー（`E7EAF8`, 補助色）× 電光インディゴ（`4C63FF`, アクセント）
- タイトル/まとめスライドは紺背景（サンドイッチ構成）、中間3枚は白背景
- 全スライド共通で「アイコンを円形に収める」モチーフを反復
- フォント: 見出し Cambria、本文 Calibri（QAで幅が安定するセーフフォント）

## サンプル生成

```bash
cd .claude/skills/pptx-ai-agent-deck
node scripts/generate_deck.js assets/sample-content/ai-agent-future.json ../../../ai-agent-future.pptx
```

## QA

生成後は `document-skills:pptx` スキルの `scripts/office/validate.py` と `markitdown` によるQAを行うこと(このリポジトリの環境ではPython実行時に `PYTHONUTF8=1` を付与しないと日本語スライドXMLの読み込みで `cp932` デコードエラーになる点に注意)。
