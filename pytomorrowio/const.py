"""Constants."""
from datetime import timedelta
from enum import IntEnum

HEADERS = {"content-type": "application/json"}

HEADER_DAILY_API_LIMIT = "X-RateLimit-Limit-hour"

DAILY = "daily"
HOURLY = "hourly"
NOWCAST = "nowcast"
FORECASTS = "forecasts"

TIMESTEP_HOURLY = "1h"
TIMESTEP_DAILY = "1d"

TYPE_WEATHER = "weather"
TYPE_POLLEN = "pollen"
TYPE_AIR_QUALITY = "air_quality"
TYPE_FIRE = "fire"
TYPE_SOLAR = "solar"
TYPE_PRECIPITATION = "precipitation"

# V4 constants
BASE_URL_V4 = "https://api.tomorrow.io/v4/timelines"
CURRENT = "current"

ONE_DAY = timedelta(days=1)
ONE_HOUR = timedelta(hours=1)
THIRTY_MINUTES = timedelta(minutes=30)
FIFTEEN_MINUTES = timedelta(minutes=15)
FIVE_MINUTES = timedelta(minutes=5)
ONE_MINUTE = timedelta(minutes=1)
REALTIME = timedelta(0)

VALID_TIMESTEPS = (
    ONE_DAY,
    ONE_HOUR,
    THIRTY_MINUTES,
    FIFTEEN_MINUTES,
    FIVE_MINUTES,
    ONE_MINUTE,
    REALTIME,
)


class PrecipitationType(IntEnum):
    """Precipitation types."""

    NONE = 0
    RAIN = 1
    SNOW = 2
    FREEZING_RAIN = 3
    ICE_PELLETS = 4


class PollenIndex(IntEnum):
    """Pollen index."""

    NONE = 0
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class PrimaryPollutantType(IntEnum):
    """Primary pollutant type."""

    PM25 = 0
    PM10 = 1
    O3 = 2
    NO2 = 3
    CO = 4
    SO2 = 5


class HealthConcernType(IntEnum):
    """Health concern type."""

    GOOD = 0
    MODERATE = 1
    UNHEALTHY_FOR_SENSITIVE_GROUPS = 2
    UNHEALTHY = 3
    VERY_UNHEALTHY = 4
    HAZARDOUS = 5


class WeatherCode(IntEnum):
    """Weather codes"""

    UNKNOWN = 0
    CLEAR = 1000
    CLOUDY = 1001
    MOSTLY_CLEAR = 1100
    PARTLY_CLOUDY = 1101
    MOSTLY_CLOUDY = 1102
    FOG = 2000
    LIGHT_FOG = 2100
    LIGHT_WIND = 3000
    WIND = 3001
    STRONG_WIND = 3002
    DRIZZLE = 4000
    RAIN = 4001
    LIGHT_RAIN = 4200
    HEAVY_RAIN = 4201
    SNOW = 5000
    FLURRIES = 5001
    LIGHT_SNOW = 5100
    HEAVY_SNOW = 5101
    FREEZING_DRIZZLE = 6000
    FREEZING_RAIN = 6001
    LIGHT_FREEZING_RAIN = 6200
    HEAVY_FREEZING_RAIN = 6201
    ICE_PELLETS = 7000
    HEAVY_ICE_PELLETS = 7101
    LIGHT_ICE_PELLETS = 7102
    THUNDERSTORM = 8000
