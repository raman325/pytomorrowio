"""Main module."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

from aiohttp import ClientConnectionError, ClientSession

from .const import (
    BASE_URL_V4,
    CURRENT,
    DAILY,
    FORECASTS,
    HEADERS,
    HOURLY,
    INSTANT,
    NOWCAST,
    ONE_DAY,
    ONE_HOUR,
    TIMESTEP_DAILY,
    TIMESTEP_HOURLY,
    VALID_TIMESTEPS,
)
from .exceptions import (
    CantConnectException,
    InvalidAPIKeyException,
    InvalidTimestep,
    MalformedRequestException,
    RateLimitedException,
    UnknownException,
)
from .fields import FIELDS_V4
from .helpers import async_to_sync

_LOGGER = logging.getLogger(__name__)


def process_v4_fields(
    fields: List[str], timestep: timedelta, write_log: bool = True
) -> List[str]:
    """
    Filter v4 field list to only include valid fields for a given endpoint.

    Optionally logs a warning when fields get filtered out.
    """
    valid_fields = [field for field in fields if field in FIELDS_V4]
    if write_log and len(valid_fields) < len(fields):
        _LOGGER.warning(
            "Removed invalid fields: %s", list(set(fields) - set(valid_fields))
        )
    processed_fields = [
        field for field in valid_fields if timestep <= FIELDS_V4[field].max_timestep
    ]
    if write_log and len(processed_fields) < len(valid_fields):
        _LOGGER.warning(
            "Removed fields not available for `%s` timestep: %s",
            timestep,
            list(set(valid_fields) - set(processed_fields)),
        )
    return processed_fields


def dt_to_utc(input_dt: datetime) -> datetime:
    """If input datetime has a timezone defined, convert to UTC."""
    if input_dt and input_dt.tzinfo:
        return input_dt.astimezone(timezone.utc)
    return input_dt


class TomorrowioV4:
    """Async class to query the Tomorrow.io v4 API."""

    def __init__(
        self,
        apikey: str,
        latitude: Union[int, float, str],
        longitude: Union[int, float, str],
        unit_system: str = "imperial",
        session: ClientSession = None,
    ) -> None:
        """Initialize Tomorrow.io API object."""
        if unit_system.lower() not in ("metric", "imperial", "si", "us"):
            raise ValueError("`unit_system` must be `metric` or `imperial`")
        if unit_system.lower() == "si":
            unit_system = "metric"
        elif unit_system.lower() == "us":
            unit_system = "imperial"

        self._apikey = apikey
        self.location = [float(latitude), float(longitude)]
        self.unit_system = unit_system.lower()
        self._session = session
        self._params = {
            "location": self.location,
            "units": self.unit_system,
        }
        self._headers = {**HEADERS, "apikey": self._apikey}

    @staticmethod
    def convert_fields_to_measurements(fields: List[str]) -> List[str]:
        """Converts general field list into fields with measurements."""
        field_list = []
        for field in fields:
            measurements = FIELDS_V4[field].measurements
            if len(measurements) < 2:
                field_list.append(field)
            else:
                field_list.extend(
                    [f"{field}{measurement}" for measurement in measurements]
                )

        return field_list

    @staticmethod
    def available_fields(
        timestep: timedelta, types: Optional[List[str]] = None
    ) -> List[str]:
        "Return available fields for a given timestep."
        if timestep not in VALID_TIMESTEPS:
            raise InvalidTimestep(f"{timestep} is not a valid 'timestep' parameter")
        fields = process_v4_fields(list(FIELDS_V4), timestep, write_log=False)

        if types:
            return [field for field in fields if FIELDS_V4[field].type in types]

        return fields

    async def _call_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call Tomorrow.io API."""
        try:
            if self._session:
                return await self._make_call(params, self._session)

            async with ClientSession() as session:
                return await self._make_call(params, session)

        except ClientConnectionError as error:
            raise CantConnectException() from error

    async def _make_call(
        self, params: Dict[str, Any], session: ClientSession
    ) -> Dict[str, Any]:
        resp = await session.post(
            BASE_URL_V4,
            headers=self._headers,
            data=json.dumps({**self._params, **params}),
        )
        resp_json = await resp.json()
        if resp.status == HTTPStatus.OK:
            return resp_json
        if resp.status == HTTPStatus.BAD_REQUEST:
            raise MalformedRequestException(resp_json, resp.headers)
        if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise InvalidAPIKeyException(resp_json, resp.headers)
        if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise RateLimitedException(resp_json, resp.headers)
        raise UnknownException(resp_json, resp.headers)

    async def realtime(self, fields: List[str]) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        return await self._call_api(
            {
                "fields": process_v4_fields(fields, INSTANT),
                "timesteps": ["current"],
            }
        )

    async def _forecast(
        self,
        timestep: timedelta,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return forecast data from Tomorrow.io's API for a given time period."""
        if timestep not in VALID_TIMESTEPS:
            raise InvalidTimestep(f"{timestep} is not a valid 'timestep' parameter")
        fields = process_v4_fields(fields, timestep)
        if timestep > ONE_HOUR:
            fields = self.convert_fields_to_measurements(fields)

        params: Dict[str, Any] = {
            "fields": fields,
            **kwargs,
        }
        if timestep == ONE_DAY:
            params["timestep"] = [TIMESTEP_DAILY]
        elif timestep == ONE_HOUR:
            params["timestep"] = [TIMESTEP_HOURLY]
        else:
            params["timestep"] = [f"{int(timestep.total_seconds()/60)}m"]

        if start_time:
            if not start_time.tzinfo:
                start_time.replace(tzinfo=timezone.utc)
            params["startTime"] = start_time.replace(microsecond=0).isoformat()
        else:
            start_time = datetime.now(tz=timezone.utc)
        if duration:
            end_time = (start_time + duration).replace(microsecond=0)
            params["endTime"] = end_time.isoformat()

        return await self._call_api(params)

    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
    ) -> Dict[str, Any]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        if timestep not in (1, 5, 15, 30):
            raise InvalidTimestep
        return await self._forecast(
            timedelta(minutes=timestep),
            fields,
            start_time=start_time,
            duration=duration,
        )

    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        return await self._forecast(
            ONE_DAY, fields, start_time=start_time, duration=duration
        )

    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        return await self._forecast(
            ONE_HOUR, fields, start_time=start_time, duration=duration
        )

    async def realtime_and_all_forecasts(
        self,
        realtime_fields: List[str],
        forecast_or_nowcast_fields: List[str],
        hourly_fields: List[str] = None,
        daily_fields: List[str] = None,
        nowcast_timestep: int = 5,
    ) -> Dict[str, Any]:
        """
        Return realtime weather and all forecasts.

        If `hourly_fields` and `daily_fields` are not provided,
        `forecast_or_nowcast_fields` will be used to get nowcast, hourly, and daily
        data.
        """
        ret_data = {}
        data = await self._call_api(
            {
                "timesteps": ["current"],
                "fields": realtime_fields,
            }
        )
        if (
            "data" in data
            and "timelines" in data["data"]
            and "intervals" in data["data"]["timelines"][0]
            and "values" in data["data"]["timelines"][0]["intervals"][0]
        ):
            ret_data[CURRENT] = data["data"]["timelines"][0]["intervals"][0]["values"]

        forecasts = ret_data.setdefault(FORECASTS, {})
        start_time = datetime.now(tz=timezone.utc).isoformat()

        if not hourly_fields and not daily_fields:
            data = await self._call_api(
                {
                    "timesteps": [
                        f"{nowcast_timestep}m",
                        TIMESTEP_HOURLY,
                        TIMESTEP_DAILY,
                    ],
                    "fields": forecast_or_nowcast_fields,
                    "startTime": start_time,
                }
            )
            if "data" in data and "timelines" in data["data"]:
                for timeline in data["data"]["timelines"]:
                    if timeline["timestep"] == TIMESTEP_DAILY:
                        key = DAILY
                    elif timeline["timestep"] == TIMESTEP_HOURLY:
                        key = HOURLY
                    else:
                        key = NOWCAST
                    forecasts[key] = timeline["intervals"]
        else:
            data = await self._call_api(
                {
                    "timesteps": [f"{nowcast_timestep}m"],
                    "fields": forecast_or_nowcast_fields,
                    "startTime": start_time,
                }
            )
            if "data" in data and "timelines" in data["data"]:
                forecasts[NOWCAST] = data["data"]["timelines"][0]["intervals"]

            for field_list, timestep, key in (
                (hourly_fields, TIMESTEP_HOURLY, HOURLY),
                (daily_fields, TIMESTEP_DAILY, DAILY),
            ):
                if field_list:
                    await asyncio.sleep(1)
                    data = await self._call_api(
                        {
                            "timesteps": [timestep],
                            "fields": field_list,
                            "startTime": start_time,
                        }
                    )
                    if "data" in data and "timelines" in data["data"]:
                        forecasts[key] = data["data"]["timelines"][0]["intervals"]
        return ret_data


class TomorrowioV4Sync(TomorrowioV4):
    """Synchronous class to query the Tomorrow.io API."""

    def __init__(
        self,
        apikey: str,
        latitude: Union[int, float, str],
        longitude: Union[int, float, str],
        unit_system: str = "imperial",
    ) -> None:
        """Initialize Synchronous Tomorrow.io v4 API object."""
        super().__init__(apikey, latitude, longitude, unit_system)

    @async_to_sync
    async def realtime(self, fields: List[str]) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        return await super().realtime(fields)

    @async_to_sync
    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
    ) -> Dict[str, Any]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        return await super().forecast_nowcast(fields, start_time, duration, timestep)

    @async_to_sync
    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_daily(fields, start_time, duration)

    @async_to_sync
    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_hourly(fields, start_time, duration)

    @async_to_sync
    async def realtime_and_all_forecasts(
        self,
        realtime_fields: List[str],
        forecast_or_nowcast_fields: List[str],
        hourly_fields: List[str] = None,
        daily_fields: List[str] = None,
        nowcast_timestep: int = 5,
    ) -> Dict[str, Any]:
        """
        Return realtime weather and all forecasts.

        If `hourly_fields` and `daily_fields` are not provided,
        `forecast_or_nowcast_fields` will be used to get nowcast, hourly, and daily
        data.
        """
        return await super().realtime_and_all_forecasts(
            realtime_fields=realtime_fields,
            forecast_or_nowcast_fields=forecast_or_nowcast_fields,
            hourly_fields=hourly_fields,
            daily_fields=daily_fields,
            nowcast_timestep=nowcast_timestep,
        )
