"""Tests for `pytomorrowio` package."""
import re
from datetime import datetime
from http import HTTPStatus
from typing import Mapping, Sequence

import pytest
from aiohttp import ClientSession

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import (
    FIVE_MINUTES,
    ONE_DAY,
    ONE_HOUR,
    ONE_MINUTE,
    REALTIME,
    TIMESTEP_DAILY,
    TIMESTEP_HOURLY,
    TYPE_POLLEN,
    TYPE_PRECIPITATION,
    TYPE_WEATHER,
)
from pytomorrowio.exceptions import (
    InvalidAPIKeyException,
    MalformedRequestException,
    RateLimitedException,
)

from .helpers import create_session, create_trace_config

GPS_COORD = (28.4195, -81.5812)


async def _test_capture_request_and_response():
    # Remove leading underscore to capture request & response to stdout
    async with ClientSession(trace_configs=[create_trace_config()]) as session:
        api = TomorrowioV4("real_api_key", *GPS_COORD, session=session)

        await api.realtime_and_all_forecasts(
            realtime_fields=api.available_fields(REALTIME),
            forecast_or_nowcast_fields=api.available_fields(ONE_MINUTE),
            hourly_fields=api.available_fields(ONE_HOUR),
            daily_fields=api.available_fields(ONE_DAY),
            nowcast_timestep=1,
        )

        assert False  # force traces to be displayed


async def test_raises_malformed_request(aiohttp_client, mock_url):
    session = await create_session(
        aiohttp_client, "timelines_1hour.json", status=HTTPStatus.BAD_REQUEST
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day is None
    assert api.num_api_requests == 0

    with pytest.raises(MalformedRequestException):
        await api.forecast_hourly(available_fields)


async def test_raises_invalid_api_key(aiohttp_client, mock_url):
    session = await create_session(
        aiohttp_client, "timelines_1hour.json", status=HTTPStatus.UNAUTHORIZED
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day is None
    assert api.num_api_requests == 0

    with pytest.raises(InvalidAPIKeyException):
        await api.forecast_hourly(available_fields)


async def test_raises_rate_limited(aiohttp_client, mock_url):
    headers = {
        "RateLimit-Limit": "3",
        "RateLimit-Remaining": "0",
        "RateLimit-Reset": "1",
        "X-RateLimit-Limit-Day": "500",
        "X-RateLimit-Limit-Hour": "25",
        "X-RateLimit-Limit-Second": "3",
        "X-RateLimit-Remaining-Day": "484",
        "X-RateLimit-Remaining-Hour": "22",
        "X-RateLimit-Remaining-Second": "0",
    }

    session = await create_session(
        aiohttp_client,
        "timelines_1hour.json",
        headers=headers,
        status=HTTPStatus.TOO_MANY_REQUESTS,
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day is None
    assert api.num_api_requests == 0

    with pytest.raises(RateLimitedException):
        await api.forecast_hourly(available_fields)

    assert api.rate_limits.get("RateLimit-Reset") == 1
    assert api.rate_limits.get("X-RateLimit-Remaining-Second") == 0
    assert api.rate_limits.get("X-RateLimit-Remaining-Hour") == 22
    assert api.rate_limits.get("X-RateLimit-Remaining-Day") == 484
    assert api.max_requests_per_day == 500


async def test_timelines_hourly_good(aiohttp_client, mock_url):
    session = await create_session(aiohttp_client, "timelines_1hour.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    res = await api.forecast_hourly(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, Mapping)

    data = res.get("data")
    assert isinstance(data, Mapping)

    timelines = data.get("timelines")
    assert isinstance(timelines, Sequence)
    assert len(timelines) == 1

    timeline = timelines[0]
    assert isinstance(timeline, Mapping)

    assert timeline.get("timestep") == TIMESTEP_HOURLY

    intervals = timeline.get("intervals")
    assert isinstance(intervals, Sequence)
    assert len(intervals) == 109

    for interval in intervals:
        assert isinstance(interval, Mapping)

        start_time = interval.get("startTime")
        assert isinstance(start_time, str)

        # Might be fixed in Python 3.11 - https://github.com/python/cpython/issues/80010
        # Maybe pytomorrowio should do the replacements to improve user experience
        start_time = re.sub("Z$", "+00:00", start_time)
        datetime.fromisoformat(start_time)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        assert set(values) == set(available_fields)


async def test_timelines_daily_good(aiohttp_client, mock_url):
    session = await create_session(aiohttp_client, "timelines_1day.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_DAY, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )
    res = await api.forecast_daily(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, Mapping)

    data = res.get("data")
    assert isinstance(data, Mapping)

    timelines = data.get("timelines")
    assert isinstance(timelines, Sequence)
    assert len(timelines) == 1

    timeline = timelines[0]
    assert isinstance(timeline, Mapping)

    assert timeline.get("timestep") == TIMESTEP_DAILY

    intervals = timeline.get("intervals")
    assert isinstance(intervals, Sequence)
    assert len(intervals) == 15

    expected_values = api.convert_fields_to_measurements(available_fields)

    for interval in intervals:
        assert isinstance(interval, Mapping)

        start_time = interval.get("startTime")
        assert isinstance(start_time, str)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        assert set(values) == set(expected_values)


async def test_timelines_5min_good(aiohttp_client, mock_url):
    session = await create_session(aiohttp_client, "timelines_5min.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        FIVE_MINUTES, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )
    res = await api.forecast_nowcast(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, Mapping)

    data = res.get("data")
    assert isinstance(data, Mapping)

    timelines = data.get("timelines")
    assert isinstance(timelines, Sequence)
    assert len(timelines) == 1

    timeline = timelines[0]
    assert isinstance(timeline, Mapping)

    assert timeline.get("timestep") == "5m"


async def test_timelines_realtime_good(aiohttp_client, mock_url):
    session = await create_session(aiohttp_client, "timelines_realtime.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(FIVE_MINUTES)
    res = await api.realtime(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, Mapping)

    data = res.get("data")
    assert isinstance(data, Mapping)

    timelines = data.get("timelines")
    assert isinstance(timelines, Sequence)
    assert len(timelines) == 1

    timeline = timelines[0]
    assert isinstance(timeline, Mapping)

    assert timeline.get("timestep") == "current"


async def test_timelines_realtime_and_nowcast_good(aiohttp_client, mock_url):
    session = await create_session(
        aiohttp_client,
        ["timelines_realtime.json", "timelines_realtime_1min_1hour_1day.json"],
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)

    res = await api.realtime_and_all_forecasts(
        realtime_fields=api.available_fields(REALTIME),
        forecast_or_nowcast_fields=api.available_fields(ONE_MINUTE),
        nowcast_timestep=1,
    )

    assert api.num_api_requests == 2

    assert res is not None
    assert isinstance(res, Mapping)

    current = res.get("current")
    assert isinstance(current, Mapping)
    assert current.get("temperature") == 74.53

    forecasts = res.get("forecasts")
    assert isinstance(forecasts, Mapping)
    assert set(forecasts.keys()) == {"hourly", "nowcast", "daily"}

    for key, expected_count in {"nowcast": 721, "hourly": 360, "daily": 16}.items():
        forecast = forecasts[key]
        assert isinstance(forecast, Sequence)
        assert len(forecast) == expected_count


async def test_timelines_realtime_nowcast_hourly_daily(aiohttp_client, mock_url):
    session = await create_session(
        aiohttp_client,
        [
            "timelines_realtime.json",
            "timelines_1min.json",
            "timelines_1hour.json",
            "timelines_1day.json",
        ],
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)

    res = await api.realtime_and_all_forecasts(
        realtime_fields=api.available_fields(REALTIME),
        forecast_or_nowcast_fields=api.available_fields(ONE_MINUTE),
        hourly_fields=api.available_fields(ONE_HOUR),
        daily_fields=api.available_fields(ONE_DAY),
        nowcast_timestep=1,
    )

    assert api.num_api_requests == 4

    assert res is not None
    assert isinstance(res, Mapping)

    current = res.get("current")
    assert isinstance(current, Mapping)
    assert current.get("temperature") == 74.53

    forecasts = res.get("forecasts")
    assert isinstance(forecasts, Mapping)
    assert set(forecasts.keys()) == {"hourly", "nowcast", "daily"}

    for key, expected_count in {"nowcast": 361, "hourly": 109, "daily": 15}.items():
        forecast = forecasts[key]
        assert isinstance(forecast, Sequence)
        print(key, len(forecast))
        assert len(forecast) == expected_count
