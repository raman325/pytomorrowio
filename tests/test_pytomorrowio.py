"""Tests for `pytomorrowio` package."""
import re
from datetime import datetime
from http import HTTPStatus
from typing import Mapping, Sequence
from unittest.mock import patch

import pytest
from aiohttp import ClientConnectionError, ClientResponseError, ClientSession

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import (
    FIVE_MINUTES,
    MAX_FIELDS_PER_REQUEST,
    ONE_DAY,
    ONE_HOUR,
    ONE_MINUTE,
    REALTIME,
    TYPE_POLLEN,
    TYPE_PRECIPITATION,
    TYPE_WEATHER,
)
from pytomorrowio.exceptions import (
    CantConnectException,
    InvalidAPIKeyException,
    InvalidTimestep,
    MalformedRequestException,
    RateLimitedException,
    UnknownException,
)

from .const import CORE_FIELDS, REALTIME_FIELDS_GREATER_THAN_MAX
from .helpers import create_session, create_trace_config

GPS_COORD = (28.4195, -81.5812)


async def _test_capture_request_and_response():
    # Remove leading underscore to capture request & response to stdout
    async with ClientSession(trace_configs=[create_trace_config()]) as session:
        api = TomorrowioV4("real_api_key", *GPS_COORD, session=session)

        await api.realtime_and_all_forecasts(
            realtime_fields=api.available_fields(REALTIME),
            nowcast_fields=api.available_fields(ONE_MINUTE),
            hourly_fields=api.available_fields(ONE_HOUR),
            daily_fields=api.available_fields(ONE_DAY),
            nowcast_timestep=1,
        )

        assert False  # force traces to be displayed


async def test_raises_malformed_request(aiohttp_client):
    session = await create_session(
        aiohttp_client, "timelines_1hour.json", status=HTTPStatus.BAD_REQUEST
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day == 100
    assert api.num_api_requests == 0

    with pytest.raises(MalformedRequestException):
        await api.forecast_hourly(available_fields)


async def test_raises_invalid_api_key(aiohttp_client):
    session = await create_session(
        aiohttp_client, "timelines_1hour.json", status=HTTPStatus.UNAUTHORIZED
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day == 100
    assert api.num_api_requests == 0

    with pytest.raises(InvalidAPIKeyException):
        await api.forecast_hourly(available_fields)


async def test_raises_rate_limited(aiohttp_client):
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

    assert api.max_requests_per_day == 100
    assert api.num_api_requests == 0
    assert api.api_key_masked == "bo*********ey"

    with pytest.raises(RateLimitedException):
        await api.forecast_hourly(available_fields)

    assert api.rate_limits.get("RateLimit-Reset") == 1
    assert api.rate_limits.get("X-RateLimit-Remaining-Second") == 0
    assert api.rate_limits.get("X-RateLimit-Remaining-Hour") == 22
    assert api.rate_limits.get("X-RateLimit-Remaining-Day") == 484
    assert api.max_requests_per_day == 500


async def test_timelines_hourly_good(aiohttp_client):
    session = await create_session(aiohttp_client, "timelines_1hour.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    res = await api.forecast_hourly(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, list)
    assert len(res) == 109

    for interval in res:
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


async def test_timelines_daily_good(aiohttp_client):
    session = await create_session(aiohttp_client, "timelines_1day.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.convert_fields_to_measurements(
        api.available_fields(ONE_DAY, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER])
    )
    res = await api.forecast_daily(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, list)

    assert len(res) == 15

    for interval in res:
        assert isinstance(interval, Mapping)

        start_time = interval.get("startTime")
        assert isinstance(start_time, str)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        assert set(values) == set(available_fields)


async def test_timelines_daily_greater_than_max_fields_good(aiohttp_client):
    fields = []
    for field in CORE_FIELDS:
        fields.append(f"{field}Min")
        fields.append(f"{field}Max")
        fields.append(field)
    session = await create_session(
        aiohttp_client,
        [
            "timelines_1day_greater_than_max_fields_1.json",
            "timelines_1day_greater_than_max_fields_2.json",
        ],
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    res = await api.forecast_daily(fields)

    assert api.num_api_requests == 2

    assert res is not None
    assert isinstance(res, list)

    assert len(res) == 16

    for interval in res:
        assert isinstance(interval, Mapping)

        start_time = interval.get("startTime")
        assert isinstance(start_time, str)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        assert set(values) == set(fields)


async def test_timelines_5min_good(aiohttp_client):
    session = await create_session(aiohttp_client, "timelines_5min.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(
        FIVE_MINUTES, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )
    res = await api.forecast_nowcast(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, list)

    assert len(res) == 73

    for interval in res:
        assert isinstance(interval, Mapping)

        start_time = interval.get("startTime")
        assert isinstance(start_time, str)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        assert set(values) == set(available_fields)


async def test_timelines_realtime_good(aiohttp_client):
    session = await create_session(aiohttp_client, "timelines_realtime.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    available_fields = api.available_fields(FIVE_MINUTES)
    res = await api.realtime(available_fields)

    assert api.num_api_requests == 1

    assert res is not None
    assert isinstance(res, Mapping)


async def test_timelines_realtime_greater_than_max_fields_good(aiohttp_client):
    session = await create_session(
        aiohttp_client,
        [
            "timelines_realtime_more_than_max_fields_1.json",
            "timelines_realtime_more_than_max_fields_2.json",
        ],
    )
    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)

    res = await api.realtime(REALTIME_FIELDS_GREATER_THAN_MAX)

    assert api.num_api_requests == 2

    assert res is not None
    assert isinstance(res, Mapping)

    assert set(res) == set(REALTIME_FIELDS_GREATER_THAN_MAX)
    assert len(res) > MAX_FIELDS_PER_REQUEST


async def test_timelines_realtime_and_nowcast_good(aiohttp_client):
    session = await create_session(
        aiohttp_client,
        ["timelines_realtime_1min_1hour_1day.json", "timelines_realtime.json"],
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)

    res = await api.realtime_and_all_forecasts(
        realtime_fields=api.available_fields(REALTIME),
        all_forecasts_fields=api.available_fields(ONE_MINUTE),
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


async def test_timelines_realtime_nowcast_hourly_daily(aiohttp_client):
    session = await create_session(
        aiohttp_client,
        [
            "timelines_1min.json",
            "timelines_1hour.json",
            "timelines_1day.json",
            "timelines_realtime.json",
        ],
    )

    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)

    res = await api.realtime_and_all_forecasts(
        realtime_fields=api.available_fields(REALTIME),
        nowcast_fields=api.available_fields(ONE_MINUTE),
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


async def test_errors(aiohttp_client):
    """Test errors."""
    with pytest.raises(ValueError, match="unit_system"):
        TomorrowioV4("bogus_api_key", 0, 0, "fake_unit")

    with pytest.raises(InvalidTimestep):
        TomorrowioV4.available_fields("not_a_timestep", [])

    session = await create_session(
        aiohttp_client, "empty_response.json", status=HTTPStatus.BAD_GATEWAY
    )
    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    with pytest.raises(ClientResponseError):
        await api.realtime(["test"])

    session = await create_session(
        aiohttp_client, "empty_response.json", status=HTTPStatus.PERMANENT_REDIRECT
    )
    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    with pytest.raises(UnknownException):
        await api.realtime(["test"])

    with pytest.raises(InvalidTimestep):
        await api.forecast_nowcast(["test"], timestep=99)

    with pytest.raises(ValueError, match="Either"):
        await api.realtime_and_all_forecasts(
            ["test"], all_forecasts_fields=["test"], nowcast_fields=["test"]
        )

    with pytest.raises(ValueError, match="At least"):
        await api.realtime_and_all_forecasts(["test"])

    with patch(
        "pytomorrowio.pytomorrowio.ClientSession.post",
        side_effect=ClientConnectionError,
    ), pytest.raises(CantConnectException):
        await api.realtime(["test"])

    session = await create_session(aiohttp_client, "empty_response.json")
    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    with pytest.raises(UnknownException):
        await api.realtime(["test"])

    session = await create_session(aiohttp_client, "empty_response.json")
    api = TomorrowioV4("bogus_api_key", *GPS_COORD, session=session)
    with pytest.raises(UnknownException):
        await api.forecast_nowcast(["test"])
