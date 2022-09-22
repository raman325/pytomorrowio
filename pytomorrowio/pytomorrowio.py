"""Main module."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

from aiohttp import ClientConnectionError, ClientSession
from multidict import CIMultiDict, CIMultiDictProxy

from .const import (
    BASE_URL_V4,
    CURRENT,
    DAILY,
    FIFTEEN_MINUTES,
    FIVE_MINUTES,
    FORECASTS,
    HEADER_DAILY_API_LIMIT,
    HEADER_REMAINING_CALLS_IN_SECOND,
    HEADERS,
    HOURLY,
    MAX_FIELDS_PER_REQUEST,
    NOWCAST,
    ONE_DAY,
    ONE_HOUR,
    ONE_MINUTE,
    THIRTY_MINUTES,
    TIMESTEP_CURRENT,
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


def _timedelta_to_str(timestep: timedelta) -> str:
    """Convert timedelta to timestep string."""
    if timestep == ONE_DAY:
        return TIMESTEP_DAILY
    if timestep == ONE_HOUR:
        return TIMESTEP_HOURLY
    if timestep not in (THIRTY_MINUTES, FIFTEEN_MINUTES, FIVE_MINUTES, ONE_MINUTE):
        raise InvalidTimestep(f"Invalid `timestep` value {timestep}")
    return f"{int(timestep.total_seconds()/60)}m"


def _timestep_to_key(timestep: str) -> str:
    """Convert timestep to dict key."""
    if timestep == TIMESTEP_DAILY:
        return DAILY
    if timestep == TIMESTEP_HOURLY:
        return HOURLY
    return NOWCAST


def mask(text: Union[str, float]) -> str:
    """Mask 3/4 of a string."""
    text_len = len(str(text))
    mask_len = text_len * 3 // 4
    unmask_len = text_len - mask_len
    prefix_len = unmask_len // 2
    suffix_len = prefix_len + (1 if unmask_len % 2 else 0)
    return f"{text[0:prefix_len]}{'*' * mask_len}{text[-(suffix_len):]}"


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

        self.api_key = apikey
        self.unit_system = unit_system.lower()
        self._session = session
        self._lat = float(latitude)
        self._long = float(longitude)
        self._params = {
            "location": f"{self._lat},{self._long}",
            "units": self.unit_system,
        }
        self._headers = {**HEADERS, "apikey": self.api_key}
        self._rate_limits: CIMultiDict = CIMultiDict()
        self._num_api_requests: int = 0

    @property
    def rate_limits(self) -> CIMultiDictProxy:
        """Return tomorrow.io rate limits for API key"""
        return CIMultiDictProxy(self._rate_limits)  # make read-only

    @property
    def max_requests_per_day(self) -> int:
        """
        Return the maximum number of requests per day.

        Defaults to 100 as a safe fallback.
        """
        return self.rate_limits.get(HEADER_DAILY_API_LIMIT, 100)

    @property
    def _remaining_requests_in_second(self) -> int:
        """
        Return the max remaining requests that can be made in the current seconed.

        Defaults to 1 so the first call can be made.
        """
        return self.rate_limits.get(HEADER_REMAINING_CALLS_IN_SECOND, 1)

    @property
    def num_api_requests(self) -> int:
        """The number of API requests made during the most recent call."""
        return self._num_api_requests

    @property
    def location_masked(self) -> str:
        """
        Return the location with the latitude and longitude masked.

        Doesn't count negative character in masking.
        """
        return ",".join(
            [
                f"-{mask(-part)}" if part < 0 else mask(part)
                for part in (self._lat, self._long)
            ]
        )

    @property
    def api_key_masked(self) -> str:
        """Return the API key with the first 3/4 masked."""
        return mask(self.api_key)

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
        """Return base URL for API requests."""
        # This method is required for test mocks
        return BASE_URL_V4

    def _strip_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive data from a dict."""
        masked_payload = data.copy()

        for key, masked_val in (
            ("apikey", self.api_key_masked),
            ("location", self.location_masked),
        ):
            if masked_val in masked_payload:
                masked_payload[key] = masked_val

        return masked_payload

    async def _call_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tomorrow.io API."""
        if self._session:
            return await self.__call_api(params, self._session)

        async with ClientSession() as session:
            return await self.__call_api(params, session)

    async def __call_api(
        self, params: Dict[str, Any], session: ClientSession
    ) -> Dict[str, Any]:
        """Make API call with session."""
        if self._remaining_requests_in_second == 0:
            await asyncio.sleep(1)

        payload = {**self._params, **params}

        _LOGGER.debug(
            "Sending the following payload to tomorrow.io: %s",
            payload
            if "location" not in payload
            else {**payload, "location": self.location_masked},
        )

        try:
            resp = await session.post(
                self._get_url(),
                headers=self._headers,
                json=payload,
                compress=False,
            )
            resp_json = await resp.json(content_type=None)
        except ClientConnectionError as error:
            raise CantConnectException() from error

        _LOGGER.debug(
            "Received a response with status code %s and headers %s",
            resp.status,
            resp.headers,
        )

        self._rate_limits = CIMultiDict(
            {k: int(v) for k, v in resp.headers.items() if "ratelimit" in k.lower()}
        )

        if resp.status in (HTTPStatus.OK, HTTPStatus.PARTIAL_CONTENT):
            self._num_api_requests += 1
            for warning in set(
                warning["message"] for warning in resp_json.get("warnings", [])
            ):
                _LOGGER.info(
                    (
                        "While calling the API for the timesteps [%s], the following "
                        "warning was returned: %s"
                    ),
                    ", ".join(params["timesteps"]),
                    warning,
                )

            return resp_json
        if resp.status == HTTPStatus.BAD_REQUEST:
            raise MalformedRequestException(resp_json, resp.headers)
        if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise InvalidAPIKeyException(resp_json, resp.headers)
        if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise RateLimitedException(resp_json, resp.headers)

        resp.raise_for_status()
        raise UnknownException(resp_json, resp.headers)

    async def realtime(
        self,
        fields: List[str],
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        if reset_num_api_requests:
            self._num_api_requests = 0

        if not additional_params:
            additional_params = {}

        ret_data = {}
        for i in range(0, len(fields), MAX_FIELDS_PER_REQUEST):
            data = await self._call_api(
                {
                    "timesteps": [TIMESTEP_CURRENT],
                    "fields": fields[i : i + MAX_FIELDS_PER_REQUEST],
                    **additional_params,
                }
            )
            try:
                ret_data.update(data["data"]["timelines"][0]["intervals"][0]["values"])
            except LookupError as error:
                raise UnknownException(data) from error

        return ret_data

    async def forecast(
        self,
        timesteps: List[timedelta],
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return forecast data from Tomorrow.io's API for a given time period."""
        if reset_num_api_requests:
            self._num_api_requests = 0

        params: Dict[str, Any] = {
            "timesteps": [_timedelta_to_str(timestep) for timestep in timesteps],
            **additional_params,
        }

        if start_time:
            if not start_time.tzinfo:
                start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = datetime.now(tz=timezone.utc)
        params["startTime"] = start_time.replace(microsecond=0).isoformat()

        if duration:
            params["endTime"] = (
                (start_time + duration).replace(microsecond=0).isoformat()
            )

        forecasts: Dict[str, List[Dict[str, Any]]] = {}
        for i in range(0, len(fields), MAX_FIELDS_PER_REQUEST):
            data = await self._call_api(
                {**params, "fields": fields[i : i + MAX_FIELDS_PER_REQUEST]}
            )
            try:
                for timeline in data["data"]["timelines"]:
                    forecast_type = _timestep_to_key(timeline["timestep"])
                    if forecast_type not in forecasts:
                        forecasts[forecast_type] = timeline["intervals"]
                        continue
                    for idx in range(0, len(forecasts[forecast_type])):
                        forecasts[forecast_type][idx]["values"].update(
                            timeline["intervals"][idx]["values"]
                        )
            except LookupError as error:
                raise UnknownException(data) from error

        return forecasts

    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        forecasts = await TomorrowioV4.forecast(
            self,
            [timedelta(minutes=timestep)],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )
        return forecasts[NOWCAST]

    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        forecasts = await TomorrowioV4.forecast(
            self,
            [ONE_DAY],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )
        return forecasts[DAILY]

    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        forecasts = await TomorrowioV4.forecast(
            self,
            [ONE_HOUR],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )
        return forecasts[HOURLY]

    async def all_forecasts(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        nowcast_timestep: int = 5,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return all forecasts."""
        return await TomorrowioV4.forecast(
            self,
            [
                timedelta(minutes=nowcast_timestep),
                ONE_HOUR,
                ONE_DAY,
            ],
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )

    async def realtime_and_all_forecasts(
        self,
        realtime_fields: List[str],
        all_forecasts_fields: Optional[List[str]] = None,
        nowcast_fields: Optional[List[str]] = None,
        hourly_fields: Optional[List[str]] = None,
        daily_fields: Optional[List[str]] = None,
        nowcast_timestep: int = 5,
        **additional_params,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return realtime weather and all forecasts.

        To get the same fields for all forecasts, use all_forecasts_fields. To get
        specific fields for specific forecast types, use the corresponding fields list.

        additional keyword arguments will be added as additional parameters, overriding
        existing parameters when applicable.
        """
        self._num_api_requests = 0
        if not (
            all_forecasts_fields or nowcast_fields or hourly_fields or daily_fields
        ):
            raise ValueError("At least one field list must be specified")
        if all_forecasts_fields and any(
            fields for fields in (nowcast_fields, hourly_fields, daily_fields)
        ):
            raise ValueError(
                "Either only all_forecasts_fields list must be specified or at least "
                "one of the other field lists"
            )

        forecasts: Dict[str, List[Dict[str, Any]]] = {}
        if all_forecasts_fields:
            forecasts = await TomorrowioV4.all_forecasts(
                self,
                all_forecasts_fields,
                nowcast_timestep=nowcast_timestep,
                reset_num_api_requests=False,
                **additional_params,
            )
        else:
            for fields, timestep in [
                (nowcast_fields, timedelta(minutes=nowcast_timestep)),
                (hourly_fields, ONE_HOUR),
                (daily_fields, ONE_DAY),
            ]:
                if fields:
                    forecasts.update(
                        await TomorrowioV4.forecast(
                            self,
                            [timestep],
                            fields,
                            reset_num_api_requests=False,
                            **additional_params,
                        )
                    )

        current = await TomorrowioV4.realtime(
            self, realtime_fields, reset_num_api_requests=False, **additional_params
        )
        return {CURRENT: current, FORECASTS: forecasts}


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
        self,
        fields: List[str],
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, Any]:
        """Return realtime weather conditions from Tomorrow.io API."""
        return await super().realtime(
            fields, reset_num_api_requests=reset_num_api_requests, **additional_params
        )

    @async_to_sync
    async def forecast(
        self,
        timesteps: List[timedelta],
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast(
            timesteps,
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )

    @async_to_sync
    async def forecast_nowcast(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        timestep: int = 5,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return forecast data from Tomorrow.io's NowCast API for a given time period."""
        return await super().forecast_nowcast(
            fields,
            start_time=start_time,
            duration=duration,
            timestep=timestep,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )

    @async_to_sync
    async def forecast_daily(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return daily forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_daily(
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )

    @async_to_sync
    async def forecast_hourly(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> List[Dict[str, Any]]:
        """Return hourly forecast data from Tomorrow.io's API for a given time period."""
        return await super().forecast_hourly(
            fields,
            start_time=start_time,
            duration=duration,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
        )

    @async_to_sync
    async def all_forecasts(
        self,
        fields: List[str],
        start_time: Optional[datetime] = None,
        duration: Optional[timedelta] = None,
        nowcast_timestep: int = 5,
        reset_num_api_requests: bool = True,
        **additional_params,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return all forecasts."""
        return await super().all_forecasts(
            fields,
            start_time=start_time,
            duration=duration,
            nowcast_timestep=nowcast_timestep,
            reset_num_api_requests=reset_num_api_requests,
            **additional_params,
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
        **additional_params,
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
            **additional_params,
        )
