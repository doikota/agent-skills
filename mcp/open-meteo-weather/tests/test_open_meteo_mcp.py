"""open_meteo_mcp のオフラインテスト.

実際の Open-Meteo API には接続せず、httpx.MockTransport で応答を差し替える。
実行: .venv/bin/python -m pytest mcp/open-meteo-weather/tests -q
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import open_meteo_mcp as om  # noqa: E402

TOKYO = {
    "id": 1850147,
    "name": "東京",
    "latitude": 35.6895,
    "longitude": 139.69171,
    "elevation": 44.0,
    "timezone": "Asia/Tokyo",
    "country_code": "JP",
    "country": "日本",
    "admin1": "東京都",
    "population": 8336599,
}
FUCHU_TOKYO = {**TOKYO, "id": 1, "name": "府中", "latitude": 35.66, "longitude": 139.48, "population": 260000}
FUCHU_HIROSHIMA = {**TOKYO, "id": 2, "name": "府中", "admin1": "広島県", "latitude": 34.56, "longitude": 133.24, "population": 40000}
TSU = {**TOKYO, "id": 3, "name": "津", "admin1": "三重県", "latitude": 34.73, "longitude": 136.51}

CURRENT_RESPONSE = {
    "latitude": 35.7,
    "longitude": 139.69,
    "timezone": "Asia/Tokyo",
    "current_units": {"temperature_2m": "°C", "relative_humidity_2m": "%"},
    "current": {
        "time": "2026-10-31T23:45",
        "temperature_2m": 15.3,
        "relative_humidity_2m": 72,
        "apparent_temperature": 14.1,
        "is_day": 0,
        "precipitation": 0.0,
        "weather_code": 3,
        "cloud_cover": 90,
        "pressure_msl": 1015.2,
        "wind_speed_10m": 2.4,
        "wind_direction_10m": 350,
        "wind_gusts_10m": 5.1,
    },
}


def _forecast_response(days: int) -> dict[str, Any]:
    dates = [f"2026-11-{d:02d}" for d in range(1, days + 1)]
    return {
        "timezone": "Asia/Tokyo",
        "daily": {
            "time": dates,
            "weather_code": [0, 61, 3, 95, 71, 2, 45][:days] + [1] * max(0, days - 7),
            "temperature_2m_max": [20.0 + i for i in range(days)],
            "temperature_2m_min": [10.0 + i for i in range(days)],
            "precipitation_sum": [0.0] * days,
            "precipitation_probability_max": [10] * days,
            "wind_speed_10m_max": [3.0] * days,
        },
        "hourly": {
            "time": [f"{d}T{h:02d}:00" for d in dates for h in range(24)],
            "relative_humidity_2m": [50 + (h % 24) for _ in dates for h in range(24)],
        },
    }


class FakeOpenMeteo:
    """URL とクエリに応じて固定応答を返すフェイク."""

    def __init__(self, geocode: Callable[[dict[str, str]], list[dict]] | None = None, forecast: Any = None,
                 forecast_status: int = 200) -> None:
        self.geocode = geocode or (lambda p: [TOKYO])
        self.forecast = forecast
        self.forecast_status = forecast_status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = dict(request.url.params)
        if request.url.host == "geocoding-api.open-meteo.com":
            results = self.geocode(params)
            return httpx.Response(200, json={"results": results} if results else {"generationtime_ms": 0.1})
        if request.url.host == "api.open-meteo.com":
            body = self.forecast
            if callable(body):
                body = body(params)
            return httpx.Response(self.forecast_status, json=body)
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeOpenMeteo]:
    def install(**kwargs: Any) -> FakeOpenMeteo:
        f = FakeOpenMeteo(**kwargs)
        monkeypatch.setattr(om, "_transport", httpx.MockTransport(f.handler))
        return f

    return install


def run(coro):
    return asyncio.run(coro)


# --- 純粋関数 ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("deg", "expected"),
    [(0, "北"), (11, "北"), (12, "北北東"), (90, "東"), (180, "南"), (225, "南西"), (350, "北"), (359.9, "北"), (None, "不明")],
)
def test_wind_direction_ja(deg, expected):
    assert om._wind_direction_ja(deg) == expected


def test_weather_text():
    assert om._weather_text(0) == "☀️ 快晴"
    assert om._weather_text(95) == "⛈️ 雷雨"
    assert "不明" in om._weather_text(42)
    assert om._weather_text(None) == "不明"


def test_format_datetime_and_date_ja():
    assert om._format_datetime_ja("2026-10-31T23:45") == "2026年10月31日(土) 23:45"
    assert om._format_date_ja("2026-11-01") == "11/1(日)"


def test_candidate_queries():
    assert om._candidate_queries("東京") == [("東京", None), ("Tokyo", "JP")]
    assert om._candidate_queries("大阪市") == [("大阪市", None), ("大阪", None), ("Osaka", "JP")]
    assert om._candidate_queries("京都府") == [("京都府", None), ("京都", None), ("Kyoto", "JP")]
    assert om._candidate_queries("ロンドン") == [("ロンドン", None)]


def test_daily_humidity():
    agg = om._daily_humidity({"time": ["2026-11-01T00:00", "2026-11-01T01:00", "2026-11-02T00:00"],
                              "relative_humidity_2m": [60, 80, None]})
    assert agg == {"2026-11-01": {"mean": 70.0, "min": 60.0, "max": 80.0}}


# --- 地点検索 ---------------------------------------------------------------


def test_search_sends_japanese_language(fake):
    f = fake()
    out = run(om.weather_search_locations("東京"))
    params = dict(f.requests[0].url.params)
    assert params["name"] == "東京"
    assert params["language"] == "ja"
    assert "東京都" in out and "日本" in out and "8,336,599人" in out


def test_search_falls_back_to_alias_for_single_char(fake):
    # API は 1 文字の検索語に結果を返さない → ローマ字別名 Tsu + countryCode=JP で再検索
    f = fake(geocode=lambda p: [TSU] if p["name"] == "Tsu" else [])
    out = run(om.weather_search_locations("津", response_format=om.ResponseFormat.JSON))
    data = json.loads(out)
    assert data["results"][0]["admin1"] == "三重県"
    last = dict(f.requests[-1].url.params)
    assert last["name"] == "Tsu" and last["countryCode"] == "JP"


def test_search_strips_suffix(fake):
    f = fake(geocode=lambda p: [TOKYO] if p["name"] == "横浜" else [])
    run(om.weather_search_locations("横浜市"))
    assert [dict(r.url.params)["name"] for r in f.requests] == ["横浜市", "横浜"]


def test_search_not_found(fake):
    fake(geocode=lambda p: [])
    out = run(om.weather_search_locations("存在しない町"))
    assert "見つかりませんでした" in out


def test_country_code_is_passed(fake):
    f = fake()
    run(om.weather_search_locations("府中", country_code="jp"))
    assert dict(f.requests[0].url.params)["countryCode"] == "JP"


# --- 現在の天気 -------------------------------------------------------------


def test_current_markdown(fake):
    f = fake(forecast=CURRENT_RESPONSE)
    out = run(om.weather_get_current(city="東京"))
    assert "## 東京 (東京都, 日本) の現在の天気" in out
    assert "2026年10月31日(土) 23:45" in out
    assert "☁️ 曇り" in out
    assert "15.3℃ (体感 14.1℃)" in out
    assert "**湿度**: 72%" in out
    assert "北の風 2.4m/s" in out
    fp = dict(f.requests[-1].url.params)
    assert fp["latitude"] == "35.6895" and fp["timezone"] == "auto" and fp["wind_speed_unit"] == "ms"
    assert "relative_humidity_2m" in fp["current"]


def test_current_json(fake):
    fake(forecast=CURRENT_RESPONSE)
    data = json.loads(run(om.weather_get_current(city="東京", response_format=om.ResponseFormat.JSON)))
    assert data["weather"] == "曇り"
    assert data["relative_humidity_percent"] == 72
    assert data["location"]["timezone"] == "Asia/Tokyo"


def test_current_with_coordinates_skips_geocoding(fake):
    f = fake(forecast=CURRENT_RESPONSE)
    out = run(om.weather_get_current(latitude=35.0, longitude=135.75))
    assert all(r.url.host == "api.open-meteo.com" for r in f.requests)
    assert "緯度 35.0000, 経度 135.7500" in out


def test_current_lists_other_candidates(fake):
    fake(geocode=lambda p: [FUCHU_TOKYO, FUCHU_HIROSHIMA], forecast=CURRENT_RESPONSE)
    out = run(om.weather_get_current(city="府中"))
    assert "府中 (東京都, 日本) の現在の天気" in out
    assert "同名の候補が他にもあります: 府中 (広島県, 日本)" in out


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({}, "都市名 (city) か"), ({"latitude": 35.0}, "両方とも指定")],
)
def test_current_argument_errors(fake, kwargs, message):
    fake(forecast=CURRENT_RESPONSE)
    out = run(om.weather_get_current(**kwargs))
    assert out.startswith("エラー:") and message in out


def test_current_city_not_found(fake):
    fake(geocode=lambda p: [], forecast=CURRENT_RESPONSE)
    out = run(om.weather_get_current(city="ほげほげ"))
    assert out.startswith("エラー:") and "weather_search_locations" in out


def test_api_400_error_is_japanese(fake):
    fake(forecast={"error": True, "reason": "Latitude must be in range"}, forecast_status=400)
    out = run(om.weather_get_current(latitude=10.0, longitude=10.0))
    assert out.startswith("エラー:") and "Latitude must be in range" in out


def test_api_429(fake):
    fake(forecast={"error": True, "reason": "Too many"}, forecast_status=429)
    out = run(om.weather_get_current(city="東京"))
    assert "利用回数制限" in out


def test_timeout(monkeypatch):
    def boom(request):
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr(om, "_transport", httpx.MockTransport(boom))
    out = run(om.weather_get_current(city="東京"))
    assert "タイムアウト" in out


# --- 週間予報 ---------------------------------------------------------------


def test_forecast_markdown_7days(fake):
    f = fake(forecast=lambda p: _forecast_response(int(p["forecast_days"])))
    out = run(om.weather_get_forecast(city="東京"))
    assert "## 東京 (東京都, 日本) の週間予報" in out
    assert out.count("\n| 11/") == 7
    assert "| 11/1(日) | ☀️ 快晴 | 20.0℃ | 10.0℃ | 10% | 0.0mm | 62% (50〜73%) | 3.0m/s |" in out
    assert "⛈️ 雷雨" in out and "🌨️ 弱い雪" in out
    fp = dict(f.requests[-1].url.params)
    assert fp["forecast_days"] == "7"
    assert fp["hourly"] == "relative_humidity_2m"
    assert "precipitation_probability_max" in fp["daily"]


def test_forecast_json_custom_days(fake):
    fake(forecast=lambda p: _forecast_response(int(p["forecast_days"])))
    data = json.loads(run(om.weather_get_forecast(city="東京", days=3, response_format=om.ResponseFormat.JSON)))
    assert data["days"] == 3
    assert data["daily"][1]["weather"] == "弱い雨"
    assert data["daily"][0]["relative_humidity_mean_percent"] == 61.5


def test_forecast_empty(fake):
    fake(forecast={"timezone": "Asia/Tokyo", "daily": {}})
    out = run(om.weather_get_forecast(city="東京"))
    assert out.startswith("エラー:")


# --- MCP プロトコル層 -------------------------------------------------------


def test_tools_are_registered_with_schemas():
    tools = {t.name: t for t in run(om.mcp.list_tools())}
    assert set(tools) == {"weather_search_locations", "weather_get_current", "weather_get_forecast"}
    fc = tools["weather_get_forecast"]
    props = fc.inputSchema["properties"]
    assert props["days"]["default"] == 7 and props["days"]["maximum"] == 16
    assert "city" in props and "city" not in fc.inputSchema.get("required", [])
    assert fc.annotations.readOnlyHint is True and fc.annotations.openWorldHint is True


def test_call_tool_via_mcp_validates_input(fake):
    fake(forecast=lambda p: _forecast_response(int(p["forecast_days"])))
    result = run(om.mcp.call_tool("weather_get_forecast", {"city": "東京", "days": 2}))
    content = result[0] if isinstance(result, tuple) else result
    assert "2日間の予報" in content[0].text
    with pytest.raises(Exception):
        run(om.mcp.call_tool("weather_get_forecast", {"city": "東京", "days": 30}))
