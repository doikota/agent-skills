#!/usr/bin/env python3
"""Open-Meteo 天気情報 MCP サーバー.

Open-Meteo (https://open-meteo.com/) の Geocoding API と Forecast API を使い、
日本語の都市名から現在の天気・気温・湿度や週間予報を取得して日本語で返す。
API キーは不要。

提供ツール:
    - weather_search_locations: 日本語の地名から候補地点 (緯度経度) を検索
    - weather_get_current:      現在の天気・気温・体感温度・湿度・風などを取得
    - weather_get_forecast:     日別予報 (既定 7 日間 = 週間予報) を取得
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 20.0
USER_AGENT = "open-meteo-mcp/1.0"

CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
]

# 日別の湿度は hourly の relative_humidity_2m から集計する
HOURLY_VARIABLES = ["relative_humidity_2m"]

# WMO 天気コード → (日本語表記, 絵文字)
WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("快晴", "☀️"),
    1: ("晴れ", "🌤️"),
    2: ("晴れ時々曇り", "⛅"),
    3: ("曇り", "☁️"),
    45: ("霧", "🌫️"),
    48: ("着氷性の霧", "🌫️"),
    51: ("弱い霧雨", "🌦️"),
    53: ("霧雨", "🌦️"),
    55: ("強い霧雨", "🌧️"),
    56: ("弱い着氷性の霧雨", "🌧️"),
    57: ("強い着氷性の霧雨", "🌧️"),
    61: ("弱い雨", "🌦️"),
    63: ("雨", "🌧️"),
    65: ("強い雨", "🌧️"),
    66: ("弱い着氷性の雨", "🌧️"),
    67: ("強い着氷性の雨", "🌧️"),
    71: ("弱い雪", "🌨️"),
    73: ("雪", "🌨️"),
    75: ("強い雪", "❄️"),
    77: ("霧雪", "🌨️"),
    80: ("弱いにわか雨", "🌦️"),
    81: ("にわか雨", "🌧️"),
    82: ("激しいにわか雨", "⛈️"),
    85: ("弱いにわか雪", "🌨️"),
    86: ("強いにわか雪", "❄️"),
    95: ("雷雨", "⛈️"),
    96: ("雷雨 (弱いひょうを伴う)", "⛈️"),
    99: ("雷雨 (強いひょうを伴う)", "⛈️"),
}

WIND_DIRECTIONS_16 = [
    "北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
    "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西",
]

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]

# Geocoding API は 1 文字の検索語に結果を返さず、2 文字は完全一致のみとなる。
# 日本語の都道府県名・主要都市名で確実に引けるよう、ローマ字の検索語を用意しておき、
# 日本語のままで見つからなかった場合のフォールバックとして使う。
# 都道府県名は県庁所在地 (北海道は札幌) の天気として扱う。
JAPANESE_ALIASES: dict[str, str] = {
    # 都道府県 → 県庁所在地
    "北海道": "Sapporo", "青森県": "Aomori", "岩手県": "Morioka", "宮城県": "Sendai",
    "秋田県": "Akita", "山形県": "Yamagata", "福島県": "Fukushima", "茨城県": "Mito",
    "栃木県": "Utsunomiya", "群馬県": "Maebashi", "埼玉県": "Saitama", "千葉県": "Chiba",
    "東京都": "Tokyo", "神奈川県": "Yokohama", "新潟県": "Niigata", "富山県": "Toyama",
    "石川県": "Kanazawa", "福井県": "Fukui", "山梨県": "Kofu", "長野県": "Nagano",
    "岐阜県": "Gifu", "静岡県": "Shizuoka", "愛知県": "Nagoya", "三重県": "Tsu",
    "滋賀県": "Otsu", "京都府": "Kyoto", "大阪府": "Osaka", "兵庫県": "Kobe",
    "奈良県": "Nara", "和歌山県": "Wakayama", "鳥取県": "Tottori", "島根県": "Matsue",
    "岡山県": "Okayama", "広島県": "Hiroshima", "山口県": "Yamaguchi",
    "徳島県": "Tokushima", "香川県": "Takamatsu", "愛媛県": "Matsuyama",
    "高知県": "Kochi", "福岡県": "Fukuoka", "佐賀県": "Saga", "長崎県": "Nagasaki",
    "熊本県": "Kumamoto", "大分県": "Oita", "宮崎県": "Miyazaki",
    "鹿児島県": "Kagoshima", "沖縄県": "Naha",
    # 県庁所在地・主要都市
    "札幌": "Sapporo", "函館": "Hakodate", "旭川": "Asahikawa", "釧路": "Kushiro",
    "帯広": "Obihiro", "青森": "Aomori", "盛岡": "Morioka", "仙台": "Sendai",
    "秋田": "Akita", "山形": "Yamagata", "福島": "Fukushima", "水戸": "Mito",
    "宇都宮": "Utsunomiya", "前橋": "Maebashi", "さいたま": "Saitama", "千葉": "Chiba",
    "東京": "Tokyo", "横浜": "Yokohama", "川崎": "Kawasaki", "相模原": "Sagamihara",
    "新潟": "Niigata", "富山": "Toyama", "金沢": "Kanazawa", "福井": "Fukui",
    "甲府": "Kofu", "長野": "Nagano", "松本": "Matsumoto", "岐阜": "Gifu",
    "静岡": "Shizuoka", "浜松": "Hamamatsu", "名古屋": "Nagoya", "津": "Tsu",
    "大津": "Otsu", "京都": "Kyoto", "大阪": "Osaka", "堺": "Sakai", "神戸": "Kobe",
    "姫路": "Himeji", "奈良": "Nara", "和歌山": "Wakayama", "鳥取": "Tottori",
    "松江": "Matsue", "岡山": "Okayama", "倉敷": "Kurashiki", "広島": "Hiroshima",
    "福山": "Fukuyama", "山口": "Yamaguchi", "下関": "Shimonoseki", "徳島": "Tokushima",
    "高松": "Takamatsu", "松山": "Matsuyama", "高知": "Kochi", "福岡": "Fukuoka",
    "北九州": "Kitakyushu", "佐賀": "Saga", "長崎": "Nagasaki", "熊本": "Kumamoto",
    "大分": "Oita", "宮崎": "Miyazaki", "鹿児島": "Kagoshima", "那覇": "Naha",
    "沖縄": "Naha",
}

# 末尾から取り除いて再検索する行政区分の接尾辞
ADMIN_SUFFIX_PATTERN = re.compile(r"(都|道|府|県|市|区|町|村)$")


class ResponseFormat(str, Enum):
    """ツールの出力形式."""

    MARKDOWN = "markdown"
    JSON = "json"


class WeatherToolError(Exception):
    """利用者 (LLM) に提示する、対処方法付きのエラー."""


# ---------------------------------------------------------------------------
# HTTP 共通処理
# ---------------------------------------------------------------------------

# テストで httpx.MockTransport を差し込めるようにするためのフック
_transport: Optional[httpx.AsyncBaseTransport] = None


async def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET リクエストを送り JSON を返す。Open-Meteo のエラー応答も例外に変換する."""
    async with httpx.AsyncClient(
        transport=_transport,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url, params=params)

    if response.status_code >= 400:
        reason = ""
        try:
            reason = response.json().get("reason", "")
        except (ValueError, AttributeError):
            pass
        if response.status_code == 429:
            raise WeatherToolError(
                "Open-Meteo の利用回数制限に達しました。しばらく待ってから再度お試しください。"
            )
        if response.status_code == 400:
            raise WeatherToolError(
                f"Open-Meteo がリクエストを受け付けませんでした (理由: {reason or '不明'})。"
                "緯度・経度や日数の指定を見直してください。"
            )
        raise WeatherToolError(
            f"Open-Meteo API がエラーを返しました (HTTP {response.status_code}"
            f"{': ' + reason if reason else ''})。時間をおいて再度お試しください。"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise WeatherToolError("Open-Meteo から不正な応答が返されました。再度お試しください。") from exc
    if isinstance(data, dict) and data.get("error"):
        raise WeatherToolError(f"Open-Meteo がエラーを返しました: {data.get('reason', '不明なエラー')}")
    return data


def _format_exception(exc: Exception) -> str:
    """例外を日本語のエラーメッセージに変換する."""
    if isinstance(exc, WeatherToolError):
        return f"エラー: {exc}"
    if isinstance(exc, httpx.TimeoutException):
        return "エラー: Open-Meteo への接続がタイムアウトしました。時間をおいて再度お試しください。"
    if isinstance(exc, httpx.HTTPError):
        return f"エラー: Open-Meteo に接続できませんでした ({type(exc).__name__})。ネットワーク接続を確認してください。"
    return f"エラー: 予期しないエラーが発生しました ({type(exc).__name__}: {exc})"


# ---------------------------------------------------------------------------
# 地点検索
# ---------------------------------------------------------------------------


def _candidate_queries(name: str) -> list[tuple[str, Optional[str]]]:
    """検索語の候補を (検索語, 強制する国コード) の形で優先順に返す."""
    candidates: list[tuple[str, Optional[str]]] = [(name, None)]

    stripped = ADMIN_SUFFIX_PATTERN.sub("", name)
    if stripped and stripped != name:
        candidates.append((stripped, None))

    for key in (name, stripped):
        alias = JAPANESE_ALIASES.get(key)
        if alias:
            candidates.append((alias, "JP"))
            break

    # 重複除去 (順序は維持)
    seen: set[tuple[str, Optional[str]]] = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _simplify_location(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "admin1": raw.get("admin1"),
        "admin2": raw.get("admin2"),
        "country": raw.get("country"),
        "country_code": raw.get("country_code"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "elevation": raw.get("elevation"),
        "timezone": raw.get("timezone"),
        "population": raw.get("population"),
    }


async def _search_locations(
    name: str, count: int, country_code: Optional[str]
) -> list[dict[str, Any]]:
    """日本語の地名で検索し、見つからなければ接尾辞除去・ローマ字別名で再検索する."""
    for query, forced_country in _candidate_queries(name):
        params: dict[str, Any] = {
            "name": query,
            "count": count,
            "language": "ja",
            "format": "json",
        }
        cc = country_code or forced_country
        if cc:
            params["countryCode"] = cc
        data = await _get_json(GEOCODING_URL, params)
        results = data.get("results") or []
        if results:
            return [_simplify_location(r) for r in results]
    return []


def _location_label(loc: dict[str, Any]) -> str:
    parts = [p for p in (loc.get("admin1"), loc.get("country")) if p and p != loc.get("name")]
    return f"{loc.get('name')}" + (f" ({', '.join(parts)})" if parts else "")


async def _resolve_location(
    city: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    country_code: Optional[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """都市名または緯度経度から地点を 1 つ決める。戻り値は (採用地点, 他の候補)."""
    if latitude is not None and longitude is not None:
        loc = {
            "name": city or f"緯度 {latitude:.4f}, 経度 {longitude:.4f}",
            "latitude": latitude,
            "longitude": longitude,
        }
        return loc, []
    if (latitude is None) != (longitude is None):
        raise WeatherToolError("緯度と経度は両方とも指定してください。")
    if not city:
        raise WeatherToolError("都市名 (city) か、緯度・経度 (latitude, longitude) を指定してください。")

    results = await _search_locations(city, count=5, country_code=country_code)
    if not results:
        hint = f" 国コード '{country_code}' での絞り込みを外すか、" if country_code else " "
        raise WeatherToolError(
            f"「{city}」に該当する地点が見つかりませんでした。{hint}"
            "表記を変える (例: 「大阪市」→「大阪」、ひらがな→漢字) か、"
            "weather_search_locations で候補を確認してから緯度・経度を指定してください。"
        )
    return results[0], results[1:]


# ---------------------------------------------------------------------------
# 整形ヘルパー
# ---------------------------------------------------------------------------


def _weather_text(code: Optional[int]) -> str:
    if code is None:
        return "不明"
    label, emoji = WEATHER_CODES.get(int(code), (f"不明 (コード {code})", "❔"))
    return f"{emoji} {label}"


def _wind_direction_ja(degrees: Optional[float]) -> str:
    if degrees is None:
        return "不明"
    index = int((float(degrees) % 360) / 22.5 + 0.5) % 16
    return WIND_DIRECTIONS_16[index]


def _fmt(value: Optional[float], unit: str, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}{unit}"


def _format_datetime_ja(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso)
    return f"{dt.year}年{dt.month}月{dt.day}日({WEEKDAYS_JA[dt.weekday()]}) {dt:%H:%M}"


def _format_date_ja(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso)
    return f"{d.month}/{d.day}({WEEKDAYS_JA[d.weekday()]})"


def _daily_humidity(hourly: dict[str, Any]) -> dict[str, dict[str, Optional[float]]]:
    """hourly の湿度を日付ごとに平均・最小・最大へ集計する."""
    buckets: dict[str, list[float]] = {}
    for t, h in zip(hourly.get("time") or [], hourly.get("relative_humidity_2m") or []):
        if h is None:
            continue
        buckets.setdefault(str(t)[:10], []).append(float(h))
    return {
        day: {
            "mean": round(sum(vals) / len(vals), 1),
            "min": min(vals),
            "max": max(vals),
        }
        for day, vals in buckets.items()
    }


def _other_candidates_note(others: list[dict[str, Any]]) -> str:
    if not others:
        return ""
    names = "、".join(_location_label(o) for o in others[:4])
    return (
        f"\n> 同名の候補が他にもあります: {names}。"
        "意図した地点と違う場合は `country_code` や緯度・経度で指定してください。\n"
    )


# ---------------------------------------------------------------------------
# MCP サーバー
# ---------------------------------------------------------------------------

mcp = FastMCP("open_meteo_mcp")

READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

CityParam = Annotated[
    Optional[str],
    Field(
        description="都市名・地名 (日本語可)。例: '東京', '大阪市', '札幌', '那覇', 'ロンドン'。"
        "緯度・経度を指定した場合は表示名としてのみ使われる。",
        max_length=100,
    ),
]
LatitudeParam = Annotated[
    Optional[float],
    Field(description="緯度 (-90〜90)。経度と併せて指定すると都市名検索を省略する。", ge=-90, le=90),
]
LongitudeParam = Annotated[
    Optional[float],
    Field(description="経度 (-180〜180)。緯度と併せて指定する。", ge=-180, le=180),
]
CountryCodeParam = Annotated[
    Optional[str],
    Field(
        description="検索を特定の国に絞る ISO 3166-1 alpha-2 の国コード。例: 'JP'。同名の地名が複数国にある場合に使う。",
        pattern=r"^[A-Za-z]{2}$",
    ),
]
FormatParam = Annotated[
    ResponseFormat,
    Field(
        description="出力形式。'markdown' は日本語の読みやすい表示、'json' は機械処理向けの構造化データ。",
    ),
]


@mcp.tool(
    name="weather_search_locations",
    annotations={"title": "地点を検索", **READ_ONLY_ANNOTATIONS},
)
async def weather_search_locations(
    query: Annotated[
        str,
        Field(description="検索する地名 (日本語可)。例: '横浜', '府中', '京都府'", min_length=1, max_length=100),
    ],
    count: Annotated[int, Field(description="返す候補の最大数 (1〜20)", ge=1, le=20)] = 5,
    country_code: CountryCodeParam = None,
    response_format: FormatParam = ResponseFormat.MARKDOWN,
) -> str:
    """日本語の地名から候補地点 (名称・都道府県/州・国・緯度経度・標高・タイムゾーン・人口) を検索する。

    同名の地名が複数ある場合 (例: '府中' は東京都と広島県) に、どの地点の天気を取得するか
    確かめるために使う。見つかった緯度・経度は weather_get_current / weather_get_forecast に渡せる。
    """
    try:
        query = query.strip()
        cc = country_code.upper() if country_code else None
        results = await _search_locations(query, count=count, country_code=cc)
    except Exception as exc:  # noqa: BLE001 - ツール境界で全例外を日本語メッセージ化する
        return _format_exception(exc)

    if not results:
        return (
            f"「{query}」に該当する地点が見つかりませんでした。"
            "表記を変える (例: 「〇〇市」→「〇〇」) か、別の地名でお試しください。"
        )

    if response_format == ResponseFormat.JSON:
        return json.dumps({"query": query, "count": len(results), "results": results}, ensure_ascii=False, indent=2)

    lines = [f"## 「{query}」の検索結果 ({len(results)}件)", ""]
    lines.append("| # | 地点 | 都道府県/州 | 国 | 緯度 | 経度 | 標高 | 人口 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        pop = f"{r['population']:,}人" if r.get("population") else "—"
        elev = _fmt(r.get("elevation"), "m", 0)
        lines.append(
            f"| {i} | {r.get('name') or '—'} | {r.get('admin1') or '—'} | {r.get('country') or '—'} "
            f"| {r.get('latitude'):.4f} | {r.get('longitude'):.4f} | {elev} | {pop} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="weather_get_current",
    annotations={"title": "現在の天気を取得", **READ_ONLY_ANNOTATIONS},
)
async def weather_get_current(
    city: CityParam = None,
    latitude: LatitudeParam = None,
    longitude: LongitudeParam = None,
    country_code: CountryCodeParam = None,
    response_format: FormatParam = ResponseFormat.MARKDOWN,
) -> str:
    """指定した都市の現在の天気・気温・体感温度・湿度・降水量・雲量・気圧・風向/風速を取得する。

    都市名 (日本語可) か緯度・経度のどちらかを指定する。都市名に同名の候補が複数ある場合は
    最も有力な地点を採用し、他の候補も併記する。時刻は現地時間。
    """
    try:
        cc = country_code.upper() if country_code else None
        loc, others = await _resolve_location(city, latitude, longitude, cc)
        data = await _get_json(
            FORECAST_URL,
            {
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "current": ",".join(CURRENT_VARIABLES),
                "timezone": "auto",
                "wind_speed_unit": "ms",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _format_exception(exc)

    cur = data.get("current") or {}
    units = data.get("current_units") or {}
    code = cur.get("weather_code")
    result = {
        "location": {**loc, "timezone": data.get("timezone", loc.get("timezone"))},
        "time": cur.get("time"),
        "weather_code": code,
        "weather": WEATHER_CODES.get(code, ("不明", ""))[0] if code is not None else "不明",
        "is_day": bool(cur.get("is_day")) if cur.get("is_day") is not None else None,
        "temperature_c": cur.get("temperature_2m"),
        "apparent_temperature_c": cur.get("apparent_temperature"),
        "relative_humidity_percent": cur.get("relative_humidity_2m"),
        "precipitation_mm": cur.get("precipitation"),
        "cloud_cover_percent": cur.get("cloud_cover"),
        "pressure_msl_hpa": cur.get("pressure_msl"),
        "wind_speed_ms": cur.get("wind_speed_10m"),
        "wind_gusts_ms": cur.get("wind_gusts_10m"),
        "wind_direction_deg": cur.get("wind_direction_10m"),
        "wind_direction": _wind_direction_ja(cur.get("wind_direction_10m")),
        "units": units,
    }

    if response_format == ResponseFormat.JSON:
        result["other_candidates"] = others
        return json.dumps(result, ensure_ascii=False, indent=2)

    lines = [
        f"## {_location_label(loc)} の現在の天気",
        f"観測時刻: {_format_datetime_ja(cur.get('time', ''))} (現地時間 / {data.get('timezone', '不明')})",
        "",
        f"- **天気**: {_weather_text(code)}",
        f"- **気温**: {_fmt(result['temperature_c'], '℃')} (体感 {_fmt(result['apparent_temperature_c'], '℃')})",
        f"- **湿度**: {_fmt(result['relative_humidity_percent'], '%', 0)}",
        f"- **降水量**: {_fmt(result['precipitation_mm'], 'mm')}",
        f"- **雲量**: {_fmt(result['cloud_cover_percent'], '%', 0)}",
        f"- **気圧 (海面)**: {_fmt(result['pressure_msl_hpa'], 'hPa')}",
        f"- **風**: {result['wind_direction']}の風 {_fmt(result['wind_speed_ms'], 'm/s')}"
        f" (最大瞬間 {_fmt(result['wind_gusts_ms'], 'm/s')})",
    ]
    note = _other_candidates_note(others)
    if note:
        lines.append(note)
    lines.append("\n出典: Open-Meteo.com (CC BY 4.0)")
    return "\n".join(lines)


@mcp.tool(
    name="weather_get_forecast",
    annotations={"title": "週間予報を取得", **READ_ONLY_ANNOTATIONS},
)
async def weather_get_forecast(
    city: CityParam = None,
    latitude: LatitudeParam = None,
    longitude: LongitudeParam = None,
    days: Annotated[
        int, Field(description="予報日数 (1〜16)。既定は 7 日間 (週間予報)。今日を含む。", ge=1, le=16)
    ] = 7,
    country_code: CountryCodeParam = None,
    response_format: FormatParam = ResponseFormat.MARKDOWN,
) -> str:
    """指定した都市の日別予報 (既定 7 日間) を取得する。

    各日の天気・最高/最低気温・降水確率・降水量・平均湿度 (最小〜最大)・最大風速を返す。
    都市名 (日本語可) か緯度・経度のどちらかを指定する。日付は現地日付。
    """
    try:
        cc = country_code.upper() if country_code else None
        loc, others = await _resolve_location(city, latitude, longitude, cc)
        data = await _get_json(
            FORECAST_URL,
            {
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "daily": ",".join(DAILY_VARIABLES),
                "hourly": ",".join(HOURLY_VARIABLES),
                "timezone": "auto",
                "wind_speed_unit": "ms",
                "forecast_days": days,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _format_exception(exc)

    daily = data.get("daily") or {}
    humidity = _daily_humidity(data.get("hourly") or {})

    def col(key: str) -> list[Any]:
        values = daily.get(key) or []
        return values + [None] * (len(daily.get("time") or []) - len(values))

    rows = []
    for t, code, tmax, tmin, psum, pprob, wmax in zip(
        daily.get("time") or [],
        col("weather_code"),
        col("temperature_2m_max"),
        col("temperature_2m_min"),
        col("precipitation_sum"),
        col("precipitation_probability_max"),
        col("wind_speed_10m_max"),
    ):
        h = humidity.get(t, {})
        rows.append(
            {
                "date": t,
                "weather_code": code,
                "weather": WEATHER_CODES.get(code, ("不明", ""))[0] if code is not None else "不明",
                "temperature_max_c": tmax,
                "temperature_min_c": tmin,
                "precipitation_probability_max_percent": pprob,
                "precipitation_sum_mm": psum,
                "relative_humidity_mean_percent": h.get("mean"),
                "relative_humidity_min_percent": h.get("min"),
                "relative_humidity_max_percent": h.get("max"),
                "wind_speed_max_ms": wmax,
            }
        )

    if not rows:
        return "エラー: Open-Meteo から予報データが返されませんでした。時間をおいて再度お試しください。"

    if response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "location": {**loc, "timezone": data.get("timezone", loc.get("timezone"))},
                "days": len(rows),
                "daily": rows,
                "other_candidates": others,
            },
            ensure_ascii=False,
            indent=2,
        )

    title = "週間予報" if len(rows) == 7 else f"{len(rows)}日間の予報"
    lines = [
        f"## {_location_label(loc)} の{title}",
        f"タイムゾーン: {data.get('timezone', '不明')}",
        "",
        "| 日付 | 天気 | 最高 | 最低 | 降水確率 | 降水量 | 湿度 (平均/最小〜最大) | 最大風速 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        hum = (
            f"{r['relative_humidity_mean_percent']:.0f}% ({r['relative_humidity_min_percent']:.0f}〜"
            f"{r['relative_humidity_max_percent']:.0f}%)"
            if r["relative_humidity_mean_percent"] is not None
            else "—"
        )
        lines.append(
            f"| {_format_date_ja(r['date'])} | {_weather_text(r['weather_code'])} "
            f"| {_fmt(r['temperature_max_c'], '℃')} | {_fmt(r['temperature_min_c'], '℃')} "
            f"| {_fmt(r['precipitation_probability_max_percent'], '%', 0)} | {_fmt(r['precipitation_sum_mm'], 'mm')} "
            f"| {hum} | {_fmt(r['wind_speed_max_ms'], 'm/s')} |"
        )
    note = _other_candidates_note(others)
    if note:
        lines.append(note)
    lines.append("\n出典: Open-Meteo.com (CC BY 4.0)")
    return "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
