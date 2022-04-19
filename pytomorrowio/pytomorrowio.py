"""Main module."""
import json
import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

from aiohttp import ClientConnectionError, ClientResponseError, ClientSession
from multidict import CIMultiDict, CIMultiDictProxy

from .const import (
    BASE_URL_V4,
    CURRENT,
    DAILY,
    FORECASTS,
    HEADER_DAILY_API_LIMIT,
    HEADERS,
    HOURLY,
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
        session: Optional[ClientSession] = None,
    ) -> None:
        """Initialize Tomorrow.io API object."""
        if unit_system.lower() not in ("metric", "imperial"):
            raise ValueError("`unit_system` must be `metric` or `imperial`")

        self._apikey = apikey
        self.unit_system = unit_system.lower()
        self._session = session
        self._params = {
            "location": f"{float(latitude)},{float(longitude)}",
            "units": self.unit_system,
        }
        self._headers = {**HEADERS, "apikey": self._apikey}
        self._rate_limits: CIMultiDict = CIMultiDict()
        self._num_api_requests: int = 0

    @property
    def rate_limits(self) -> CIMultiDictProxy:
        """Return tomorrow.io rate limits for API key"""
        return CIMultiDictProxy(self._rate_limits)  # make read-only

    @property
    def max_requests_per_day(self) -> Optional[int]:
        """Return the maximum number of requests per day."""
        return self.rate_limits.get(HEADER_DAILY_API_LIMIT)

    @property
    def num_api_requests(self) -> int:
        """The number of API requests made during the most recent call."""
        return self._num_api_requests

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

    @staticmethod
    def _get_url() -> str:
        # This method is required for test mocks
        return BASE_URL_V4

    async def _call_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._session:
            return await self._make_call(params, self._session)

        async with ClientSession() as session:
            return await self._make_call(params, session)

    async def _make_call(
        self, params: Dict[str, Any], session: ClientSession
    ) -> Dict[str, Any]:
        try:
            resp = await session.post(
                self._get_url(),
                headers=self._headers,
                data=json.dumps({**self._params, **params}),
            )
            resp_json = await resp.json()
        except ClientConnectionError as error:
            raise CantConnectException() from error

        self._rate_limits = CIMultiDict(
            {k: int(v) for k, v in resp.headers.items() if "ratelimit" in k.lower()}
        )

        if resp.status == HTTPStatus.OK:
            self._num_api_requests += 1
            return resp_json
        if resp.status == HTTPStatus.BAD_REQUEST:
            raise MalformedRequestException(resp_json, resp.headers)
        if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise InvalidAPIKeyException(resp_json, resp.headers)
        if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise RateLimitedException(resp_json, resp.headers)

        try:
            resp.raise_for_status()
        except ClientResponseError as error:
            raise UnknownException(resp_json, resp.headers) from error

        return {}

    async def realtime(
        self, fields: List[str], reset_num_api_requests: bool = True
    ) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        if reset_num_api_requests:
            self._num_api_requests = 0

        data = await self._call_api(
            {
                "timesteps": ["current"],
                "fields": fields,
            }
        )
        if (
            "data" in data
            and "timelines" in data["data"]
            and "intervals" in data["data"]["timelines"][0]
            and "values" in data["data"]["timelines"][0]["intervals"][0]
        ):
            return data["data"]["timelines"][0]["intervals"][0]["values"]

        return {}

    async def _forecast(
        self,
        timesteps: List[timedelta],
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **kwargs,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return forecast data from Tomorrow.io's API for a given time period."""
        if reset_num_api_requests:
            self._num_api_requests = 0

        params: Dict[str, Any] = {
            "fields": fields,
            **kwargs,
        }
        timesteps_param: List[str] = []

        for timestep in timesteps:
            if timestep == ONE_DAY:
                timesteps_param.append(TIMESTEP_DAILY)
            elif timestep == ONE_HOUR:
                timesteps_param.append(TIMESTEP_HOURLY)
            else:
                timesteps_param.append(f"{int(timestep.total_seconds()/60)}m")

        params["timesteps"] = timesteps_param

        if start_time:
            if not start_time.tzinfo:
                start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = datetime.now(tz=timezone.utc)
        params["startTime"] = start_time.replace(microsecond=0).isoformat()
        if duration:
            end_time = (start_time + duration).replace(microsecond=0)
            params["endTime"] = end_time.isoformat()

        forecasts: Dict[str, List[Dict[str, Any]]] = {}
        data = await self._call_api(params)
        if "data" in data and "timelines" in data["data"]:
            for timeline in data["data"]["timelines"]:
                if timeline["timestep"] == TIMESTEP_DAILY:
                    key = DAILY
                elif timeline["timestep"] == TIMESTEP_HOURLY:
                    key = HOURLY
                else:
                    key = NOWCAST
                forecasts[key] = timeline["intervals"]

        return forecasts

    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        if timestep not in (1, 5, 15, 30):
            raise InvalidTimestep
        forecasts = await self._forecast(
            [timedelta(minutes=timestep)],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )
        return forecasts[NOWCAST]

    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        forecasts = await self._forecast(
            [ONE_DAY],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )
        return forecasts[DAILY]

    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        forecasts = await self._forecast(
            [ONE_HOUR],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )
        return forecasts[HOURLY]

    async def all_forecasts(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        nowcast_timestep: int = 5,
        reset_num_api_requests: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return all forecasts."""
        return await self._forecast(
            [
                timedelta(minutes=nowcast_timestep),
                ONE_HOUR,
                ONE_DAY,
            ],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )

    async def realtime_and_all_forecasts(
        self,
        realtime_fields: List[str],
        all_forecasts_fields: Optional[List[str]] = None,
        nowcast_fields: Optional[List[str]] = None,
        hourly_fields: Optional[List[str]] = None,
        daily_fields: Optional[List[str]] = None,
        nowcast_timestep: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return realtime weather and all forecasts.

        To get the same fields for all forecasts, use all_forecasts_fields. To get
        specific fields for specific forecast types, use the corresponding fields list.
        """
        self._num_api_requests = 0
        if (
            not all_forecasts_fields
            and not nowcast_fields
            and not hourly_fields
            and not daily_fields
        ):
            raise ValueError("At least one field list must be specified")
        if all_forecasts_fields and (nowcast_fields or hourly_fields or daily_fields):
            raise ValueError(
                "Either only all_forecasts_fields list must be specified or at least "
                "one of the other field lists"
            )

        forecasts: Dict[str, List[Dict[str, Any]]] = {}
        if all_forecasts_fields is not None:
            forecasts = await TomorrowioV4.all_forecasts(
                self,
                all_forecasts_fields,
                nowcast_timestep=nowcast_timestep,
                reset_num_api_requests=False,
            )
        else:
            if nowcast_fields is not None:
                forecasts[NOWCAST] = await TomorrowioV4.forecast_nowcast(
                    self,
                    nowcast_fields,
                    timestep=nowcast_timestep,
                    reset_num_api_requests=False,
                )
            for fields, forecast_type, method in (
                (hourly_fields, HOURLY, TomorrowioV4.forecast_hourly),
                (daily_fields, DAILY, TomorrowioV4.forecast_daily),
            ):
                if fields is not None:
                    forecasts[forecast_type] = await method(
                        self, fields, reset_num_api_requests=False
                    )

        return {
            CURRENT: await TomorrowioV4.realtime(
                self, realtime_fields, reset_num_api_requests=False
            ),
            FORECASTS: forecasts,
        }


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
    async def realtime(
        self, fields: List[str], reset_num_api_requests: bool = True
    ) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        return await super().realtime(
            fields, reset_num_api_requests=reset_num_api_requests
        )

    @async_to_sync
    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        return await super().forecast_nowcast(
            fields,
            start_time=start_time,
            duration=duration,
            timestep=timestep,
            reset_num_api_requests=reset_num_api_requests,
        )

    @async_to_sync
    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_daily(
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )

    @async_to_sync
    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_hourly(
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
        )

    @async_to_sync
    async def all_forecasts(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        nowcast_timestep: int = 5,
        reset_num_api_requests: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return all forecasts."""
        return await super().all_forecasts(
            fields,
            start_time=start_time,
            duration=duration,
            nowcast_timestep=nowcast_timestep,
            reset_num_api_requests=reset_num_api_requests,
        )

    @async_to_sync
    async def realtime_and_all_forecasts(
        self,
        realtime_fields: List[str],
        all_forecasts_fields: Optional[List[str]] = None,
        nowcast_fields: Optional[List[str]] = None,
        hourly_fields: Optional[List[str]] = None,
        daily_fields: Optional[List[str]] = None,
        nowcast_timestep: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return realtime weather and all forecasts.

        To get the same fields for all forecasts, use all_forecasts_fields. To get
        specific fields for specific forecast types, use the corresponding fields list.
        """
        return await super().realtime_and_all_forecasts(
            realtime_fields=realtime_fields,
            all_forecasts_fields=all_forecasts_fields,
            nowcast_fields=nowcast_fields,
            hourly_fields=hourly_fields,
            daily_fields=daily_fields,
            nowcast_timestep=nowcast_timestep,
        )
