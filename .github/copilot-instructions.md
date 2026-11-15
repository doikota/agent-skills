# リポジトリの指示

## アーキテクチャ

このリポジトリには、`.claude/skills/` 配下に独立した 2 つの Claude スキルが含まれています。各スキルは `SKILL.md` と、スタンドアロンのコマンドラインジェネレーター、独自の依存関係、サンプルアセットで構成されています。`README.md` には Dev Container のセットアップ手順とコマンド例が記載されています。

- `pdf-sales-report` は CSV を読み込み、日本語の月次売上 PDF を生成します。必須カラム、レポートのセクション構成、同梱の Noto Sans JP フォントについては `.claude/skills/pdf-sales-report/SKILL.md` に記載されています。フォントのパスは Python スクリプトからの相対パスで解決されます。
- `pptx-ai-agent-deck` は JSON を読み込み、テーマ付きの 5 枚構成のプレゼンテーションを生成します。コンテンツのスキーマ、レイアウト、対応するアイコン名については `.claude/skills/pptx-ai-agent-deck/SKILL.md` に記載されています。サンプル JSON は完全な入力例です。
- PDF ジェネレーターはルートの `.venv` と、そのスキルの `requirements.txt` を使用します。プレゼンテーションジェネレーターは、自身のスキルディレクトリにある Node の依存関係と lockfile を使用します。Dev Container は Python 3.12 と Node 22 を対象としており、作成時に両方の依存関係をインストールします。

## セットアップとコマンド

リポジトリのルートで実行します。

```bash
python -m venv .venv
.venv/bin/python -m pip install -r .claude/skills/pdf-sales-report/requirements.txt
npm --prefix .claude/skills/pptx-ai-agent-deck ci
```

サンプル出力を生成します。

```bash
.venv/bin/python .claude/skills/pdf-sales-report/scripts/generate_sales_report.py \
  .claude/skills/pdf-sales-report/assets/sample-data/sales_202501.csv \
  monthly-report.pdf --title "2025年1月 売上レポート"

node .claude/skills/pptx-ai-agent-deck/scripts/generate_deck.js \
  .claude/skills/pptx-ai-agent-deck/assets/sample-content/ai-agent-future.json \
  ai-agent-future.pptx
```

共通のテストランナーや設定済みの lint コマンドはありません。各ジェネレーターの構文チェックだけを行う場合は、次を実行します。

```bash
.venv/bin/python -m py_compile .claude/skills/pdf-sales-report/scripts/generate_sales_report.py
node --check .claude/skills/pptx-ai-agent-deck/scripts/generate_deck.js
```

サンプル生成コマンドは、エンドツーエンドのスモークチェックとして利用できます。生成された `.pdf` と `.pptx` ファイルは Git の管理対象外です。

## リポジトリ固有の規約

- 各ジェネレーターの依存関係は、それぞれのマニフェストで管理してください。PPTX スキルでは lockfile を使って `npm ci` を実行してください。
- `SKILL.md` に記載されている PDF の入力カラム名と日本語のレポートラベルは変更しないでください。スクリプトは同梱フォントをスクリプトからの相対パスで読み込みます。
- PPTX のコンテンツは、ドキュメント化された JSON スキーマおよび `generate_deck.js` 内の `ICON_MAP` との互換性を保ってください。デッキのセクションスライドはちょうど 3 枚です。各セクションに表示される項目は最大 4 つ、まとめに表示されるポイントは最大 3 つです。
- 日本語テキストを扱うため、Dev Container で `PYTHONUTF8=1` が設定されています。
