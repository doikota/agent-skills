#!/usr/bin/env bash
# bundle.html を作る: Parcel でビルド → html-inline で 1 ファイル化 → 後処理
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist .parcel-cache
node_modules/.bin/parcel build index.html --dist-dir dist --no-source-maps
node_modules/.bin/html-inline dist/index.html > bundle.html
python3 scripts/postbundle.py bundle.html
