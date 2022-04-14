"""Tests for `pytomorrowio` package."""
import json
import re
import sys
from datetime import datetime
from typing import Mapping, Sequence

if sys.version_info < (3, 8):
    from asynctest import patch
else:
    from unittest.mock import patch

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import ONE_HOUR, TIMESTEP_HOURLY, TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER


def call_api_mock():
    return patch("pytomorrowio.TomorrowioV4._call_api")


def load_json(file_name: str):
    with open(file_name, "r") as handle:
        return json.load(handle)


async def test_timelines_hourly_good():
    with call_api_mock() as mock:
        mock.return_value = load_json("tests/fixtures/timelines_hourly_good.json")

        api = TomorrowioV4("bogus_api_key", 28.4195, -81.5812)
        available_fields = api.available_fields(ONE_HOUR, [TYPE_POLLEN, TYPE_PRECIPITATION, TYPE_WEATHER])
        res = await api.forecast_hourly(available_fields)

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
