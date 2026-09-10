from typing import Any

import httpx

from ..contracts import GetWeatherArgs
from .base import PublicToolError


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_WEATHER = {
    0: "晴",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    95: "雷暴",
}


class WeatherToolError(PublicToolError):
    """天气服务无法返回可用结果。"""


def _require_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WeatherToolError("天气服务响应格式异常")
    return value


async def _fetch_weather(
    args: GetWeatherArgs,
    *,
    client: httpx.AsyncClient,
) -> dict[str, object]:
    geocoding_response = await client.get(
        GEOCODING_URL,
        params={"name": args.city, "count": 1, "language": "zh", "format": "json"},
    )
    geocoding_response.raise_for_status()
    geocoding = _require_mapping(geocoding_response.json())
    results = geocoding.get("results")
    if not isinstance(results, list) or not results:
        raise WeatherToolError(f"没有找到城市：{args.city}")
    location = _require_mapping(results[0])

    try:
        latitude = location["latitude"]
        longitude = location["longitude"]
        location_name = str(location["name"])
    except KeyError as exc:
        raise WeatherToolError("天气服务响应格式异常") from exc

    forecast_response = await client.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,apparent_temperature,precipitation,"
                "weather_code,wind_speed_10m"
            ),
            "timezone": "auto",
        },
    )
    forecast_response.raise_for_status()
    forecast = _require_mapping(forecast_response.json())
    current = _require_mapping(forecast.get("current"))
    required = (
        "time",
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
    )
    if any(key not in current for key in required):
        raise WeatherToolError("天气服务响应格式异常")

    country = location.get("country")
    display_location = f"{location_name}, {country}" if country else location_name
    weather_code = int(current["weather_code"])
    return {
        "location": display_location,
        "local_time": current["time"],
        "temperature_c": current["temperature_2m"],
        "apparent_temperature_c": current["apparent_temperature"],
        "precipitation_mm": current["precipitation"],
        "weather_code": weather_code,
        "weather": WMO_WEATHER.get(weather_code, "未知天气"),
        "wind_speed_kmh": current["wind_speed_10m"],
    }


async def get_weather(
    args: GetWeatherArgs,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
    try:
        if client is not None:
            return await _fetch_weather(args, client=client)
        async with httpx.AsyncClient(timeout=10) as owned_client:
            return await _fetch_weather(args, client=owned_client)
    except WeatherToolError:
        raise
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise WeatherToolError("天气服务暂时不可用，请稍后重试") from exc
