"""Tests for `pytomorrowio` package."""
import json
import re
from datetime import datetime
from typing import Mapping, Sequence
from unittest.mock import AsyncMock, patch

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import ONE_HOUR


def call_api_mock():
    return patch("pytomorrowio.TomorrowioV4._call_api")


def load_json(file_name: str):
    with open(file_name, "r") as handle:
        return json.load(handle)


async def test_timelines_hourly_good():
    with call_api_mock() as mock:
        mock.return_value = load_json("tests/fixtures/timelines_hourly_good.json")

        api = TomorrowioV4("bogus_api_key", 28.4195, -81.5812)  # , session=client)
        available_fields = api.available_fields(ONE_HOUR)
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

        assert timeline.get("timestep") == "1h"

        intervals = timeline.get("intervals")
        assert isinstance(intervals, Sequence)
        assert len(intervals) == 109

        interval = intervals[0]
        assert isinstance(interval, Mapping)

        startTime = interval.get("startTime")
        # Might be fixed in Python 3.11 - https://github.com/python/cpython/issues/80010
        # Maybe pytomorrowio should do the replacement to improve user experience
        startTime = re.sub("Z$", "+00:00", startTime)
        datetime.fromisoformat(startTime)

        values = interval.get("values")
        assert isinstance(values, Mapping)

        unavailable_values = {
            "epaHealthConcern",
            "epaIndex",
            "epaPrimaryPollutant",
            "mepHealthConcern",
            "mepIndex",
            "mepPrimaryPollutant",
            "particulateMatter10",
            "particulateMatter25",
            "pollutantCO",
            "pollutantNO2",
            "pollutantO3",
            "pollutantSO2",
            "solarDHI",
            "solarDNI",
            "solarGHI",
        }

        assert set(values) == (set(available_fields) - unavailable_values)
