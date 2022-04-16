"""Tests for `pytomorrowio` package."""
import json
import re
import sys
from datetime import datetime
from types import SimpleNamespace
from typing import Mapping, Sequence

from aiohttp import (
    ClientSession,
    TraceConfig,
    TraceRequestChunkSentParams,
    TraceRequestEndParams,
)
from multidict import CIMultiDict

if sys.version_info < (3, 8):
    from asynctest import patch, Mock, PropertyMock
else:
    from unittest.mock import patch, Mock, PropertyMock

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import (
    FIVE_MINUTES,
    ONE_DAY,
    ONE_HOUR,
    TIMESTEP_DAILY,
    TIMESTEP_HOURLY,
    TYPE_POLLEN,
    TYPE_PRECIPITATION,
    TYPE_WEATHER,
)

GPS_COORD = (28.4195, -81.5812)


def create_trace_config() -> TraceConfig:
    async def on_request_chunk_sent(
        session: ClientSession,
        trace_config_ctx: SimpleNamespace,
        params: TraceRequestChunkSentParams,
    ):
        trace_config_ctx.request_body = params.chunk

    async def on_request_end(
        session: ClientSession,
        trace_config_ctx: SimpleNamespace,
        params: TraceRequestEndParams,
    ):
        print("Request:")
        print(params.url)
        for k, v in params.headers.items():
            print(f"  {k}: {v}")
        if trace_config_ctx.request_body:
            print(trace_config_ctx.request_body)
        print()
        print("Response:")
        for k, v in sorted(params.response.headers.items()):
            print(f"  {k}: {v}")
        resp = await params.response.json()
        print(json.dumps(resp, indent=2))

    trace_config = TraceConfig()
    trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
    trace_config.on_request_end.append(on_request_end)
    return trace_config


def load_json(file_name: str):
    with open(f"tests/fixtures/{file_name}", "r") as file:
        return json.load(file)


async def _test_capture_request_and_response():
    # Remove leading underscore to capture request & response
    async with ClientSession(trace_configs=[create_trace_config()]) as session:
        api = TomorrowioV4("real_api_key", *GPS_COORD, session=session)

        available_fields = api.available_fields(
            ONE_DAY, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
        )
        await api.forecast_daily(available_fields)
        assert False


def set_mock_return_value(mock: Mock, return_value):
    mock.return_value = return_value
    return None  # return None so caller can chain in lambda func


@patch.object(TomorrowioV4, "rate_limits", new_callable=PropertyMock)
@patch.object(TomorrowioV4, "_call_api")
async def test_rate_limits(call_api_mock: Mock, rate_limits_mock: Mock):
    rate_limits_return_value = CIMultiDict({
        "RateLimit-Limit": 3,
        "RateLimit-Remaining": 2,
        "RateLimit-Reset": 1,
        "X-RateLimit-Limit-Day": 500,
        "X-RateLimit-Limit-Hour": 25,
        "X-RateLimit-Limit-Second": 3,
        "X-RateLimit-Remaining-Day": 447,
        "X-RateLimit-Remaining-Hour": 24,
        "X-RateLimit-Remaining-Second": 2,
    })

    call_api_mock.side_effect = lambda _: set_mock_return_value(
        rate_limits_mock, rate_limits_return_value
    ) or load_json("timelines_hourly_good.json")

    rate_limits_mock.return_value = CIMultiDict()

    api = TomorrowioV4("bogus_api_key", *GPS_COORD)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    assert api.max_requests_per_day is None

    forecast = await api.forecast_hourly(available_fields)
    call_api_mock.assert_called_once()

    assert forecast is not None

    assert api.rate_limits == rate_limits_return_value
    assert api.max_requests_per_day == 500
    assert api.rate_limits.get("X-RateLimit-Remaining-Day") == 447


@patch.object(TomorrowioV4, "_call_api")
async def test_timelines_hourly_good(call_api_mock: Mock):
    call_api_mock.return_value = load_json("timelines_hourly_good.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD)
    available_fields = api.available_fields(
        ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )

    res = await api.forecast_hourly(available_fields)
    call_api_mock.assert_called_once()

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


@patch.object(TomorrowioV4, "_call_api")
async def test_timelines_daily_good(call_api_mock: Mock):
    call_api_mock.return_value = load_json("timelines_daily_good.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD)
    available_fields = api.available_fields(
        ONE_DAY, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )
    res = await api.forecast_daily(available_fields)
    call_api_mock.assert_called_once()

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


@patch.object(TomorrowioV4, "_call_api")
async def test_timelines_5min_good(call_api_mock: Mock):
    call_api_mock.return_value = load_json("timelines_5min_good.json")

    api = TomorrowioV4("bogus_api_key", *GPS_COORD)
    available_fields = api.available_fields(
        FIVE_MINUTES, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER]
    )
    res = await api.forecast_nowcast(available_fields)
    call_api_mock.assert_called_once()

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
