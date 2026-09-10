import asyncio

import httpx
import pytest

from stages.phase3_personal_agent.app.contracts import GetWeatherArgs
from stages.phase3_personal_agent.app.tools.weather import WeatherToolError, get_weather


def _weather_handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "geocoding-api.open-meteo.com":
        assert request.url.params["name"] == "上海"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Shanghai",
                        "country": "China",
                        "latitude": 31.22222,
                        "longitude": 121.45806,
                    }
                ]
            },
        )
    assert request.url.host == "api.open-meteo.com"
    assert request.url.params["timezone"] == "auto"
    return httpx.Response(
        200,
        json={
            "current": {
                "time": "2026-09-10T15:00",
                "temperature_2m": 18.2,
                "apparent_temperature": 17.4,
                "precipitation": 0.0,
                "weather_code": 3,
                "wind_speed_10m": 9.1,
            }
        },
    )


def test_get_weather_combines_location_and_current_weather():
    async def run():
        transport = httpx.MockTransport(_weather_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await get_weather(GetWeatherArgs(city="上海"), client=client)

    result = asyncio.run(run())

    assert result == {
        "location": "Shanghai, China",
        "local_time": "2026-09-10T15:00",
        "temperature_c": 18.2,
        "apparent_temperature_c": 17.4,
        "precipitation_mm": 0.0,
        "weather_code": 3,
        "weather": "阴",
        "wind_speed_kmh": 9.1,
    }


def test_get_weather_rejects_missing_city_match():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": []})
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await get_weather(GetWeatherArgs(city="不存在的城市"), client=client)

    with pytest.raises(WeatherToolError, match="没有找到城市"):
        asyncio.run(run())


def test_get_weather_converts_http_failure_to_safe_error():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(503, text="provider details")
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await get_weather(GetWeatherArgs(city="上海"), client=client)

    with pytest.raises(WeatherToolError, match="天气服务暂时不可用") as exc_info:
        asyncio.run(run())

    assert "provider details" not in str(exc_info.value)


def test_get_weather_rejects_malformed_forecast_response():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(
                200,
                json={"results": [{"name": "Shanghai", "latitude": 31, "longitude": 121}]},
            )
        return httpx.Response(200, json={"current": {"temperature_2m": 20}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await get_weather(GetWeatherArgs(city="上海"), client=client)

    with pytest.raises(WeatherToolError, match="响应格式异常"):
        asyncio.run(run())
