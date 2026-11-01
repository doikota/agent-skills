# Open-Meteo 天気 MCP サーバー (`open_meteo_mcp`)

[Open-Meteo](https://open-meteo.com/) の API (APIキー不要) を使い、日本語の都市名から天気情報を取得して日本語で返す MCP サーバーです。Python (FastMCP) で実装しています。

## ツール

| ツール | 内容 |
|---|---|
| `weather_search_locations` | 日本語の地名から候補地点 (都道府県・国・緯度経度・標高・人口) を検索 |
| `weather_get_current` | 現在の天気・気温・体感温度・湿度・降水量・雲量・気圧・風向/風速 |
| `weather_get_forecast` | 日別予報 (既定 7 日 = 週間予報、1〜16 日)。天気・最高/最低気温・降水確率・降水量・湿度 (平均/最小〜最大)・最大風速 |

共通の引数:

- `city` … 都市名 (日本語可。例: `東京`, `大阪市`, `京都府`, `津`, `ロンドン`)
- `latitude` / `longitude` … 緯度経度で直接指定 (都市名検索を省略)
- `country_code` … 同名地名を国で絞り込む (例: `JP`)
- `response_format` … `markdown` (既定・日本語表示) / `json` (構造化データ)

### 日本語の地名の扱い

- Geocoding API に `language=ja` で問い合わせるため、結果の地名・都道府県名・国名は日本語で返ります。
- 見つからない場合は「市・区・町・村・都・道・府・県」を外して再検索します (`大阪市` → `大阪`)。
- それでも見つからない場合、都道府県名・主要都市名はローマ字の別名で再検索します。Geocoding API が 1 文字の検索語 (例: `津`) に結果を返さないことへの対策です。都道府県名は県庁所在地の天気になります (`北海道` → 札幌)。
- 同名の地点が複数ある場合 (例: `府中`) は最も有力な地点を採用し、他の候補を併記します。

## セットアップ

```bash
cd /workspaces/agent-skills
.venv/bin/pip install -r mcp/open-meteo-weather/requirements-dev.txt
```

## Claude Code への登録 (stdio)

```bash
claude mcp add open-meteo -- /workspaces/agent-skills/.venv/bin/python /workspaces/agent-skills/mcp/open-meteo-weather/open_meteo_mcp.py
```

Claude Desktop などの `mcpServers` 設定例:

```json
{
  "mcpServers": {
    "open-meteo": {
      "command": "/workspaces/agent-skills/.venv/bin/python",
      "args": ["/workspaces/agent-skills/mcp/open-meteo-weather/open_meteo_mcp.py"]
    }
  }
}
```

MCP Inspector での動作確認:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python mcp/open-meteo-weather/open_meteo_mcp.py
```

## テスト

テストは `httpx.MockTransport` で応答を差し替えるため、Open-Meteo には接続しません。

```bash
.venv/bin/python -m pytest mcp/open-meteo-weather/tests -q
```

## 出力例 (`weather_get_current`, markdown)

```
## 東京 (東京都, 日本) の現在の天気
観測時刻: 2026年10月31日(土) 23:45 (現地時間 / Asia/Tokyo)

- **天気**: ☁️ 曇り
- **気温**: 15.3℃ (体感 14.1℃)
- **湿度**: 72%
- **降水量**: 0.0mm
- **雲量**: 90%
- **気圧 (海面)**: 1015.2hPa
- **風**: 北の風 2.4m/s (最大瞬間 5.1m/s)
```

## 注意

- 風速は m/s、気温は ℃、時刻・日付は対象地点の現地時間です。
- Open-Meteo の無料 API は非商用利用向けです (1 日 10,000 リクエストまで)。データのライセンスは CC BY 4.0 です。
