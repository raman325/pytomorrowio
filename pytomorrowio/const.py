"""Constants."""
from enum import IntEnum

HEADERS = {"content-type": "application/json"}

HEADER_DAILY_API_LIMIT = "X-RateLimit-Limit-hour"

DAILY = "daily"
HOURLY = "hourly"
NOWCAST = "nowcast"
FORECASTS = "forecasts"

TIMESTEP_HOURLY = "1h"
TIMESTEP_DAILY = "1d"

MIN = "Min"
MAX = "Max"
AVG = "Avg"

TYPE_WEATHER = "weather"
TYPE_POLLEN = "pollen"
TYPE_AIR_QUALITY = "air_quality"
TYPE_FIRE = "fire"
TYPE_SOLAR = "solar"
TYPE_PRECIPITATION = "precipitation"

ALL_MEASUREMENTS = [MIN, MAX, AVG]
NO_AVG = [MIN, MAX]


# V4 constants
BASE_URL_V4 = "https://api.tomorrow.io/v4/timelines"
CURRENT = "current"
FIELDS_V4 = {
    "temperature": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "temperatureApparent": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "dewPoint": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "humidity": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "windSpeed": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "windDirection": {
        "timestep": [-6, 360],
        "measurements": [AVG],
        "type": TYPE_WEATHER,
    },
    "windGust": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "pressureSurfaceLevel": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "pressureSeaLevel": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "precipitationIntensity": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_PRECIPITATION,
    },
    "precipitationProbability": {
        "timestep": [0, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_PRECIPITATION,
    },
    "precipitationType": {
        "timestep": [-6, 108],
        "measurements": [],
        "type": TYPE_PRECIPITATION,
    },
    "hailBinary": {
        "timestep": [-6, 48],
        "measurements": [],
        "type": TYPE_PRECIPITATION,
    },
    "solarGHI": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_SOLAR,
    },
    "solarDNI": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_SOLAR,
    },
    "solarDHI": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_SOLAR,
    },
    "visibility": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "cloudCover": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "cloudBase": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "cloudCeiling": {
        "timestep": [-6, 360],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
    "weatherCode": {
        "timestep": [-6, 360],
        "measurements": NO_AVG,
        "type": TYPE_WEATHER,
    },
    "particulateMatter25": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "particulateMatter10": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "pollutantO3": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "pollutantNO2": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "pollutantCO": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "pollutantSO2": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "mepIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "mepPrimaryPollutant": {
        "timestep": [-6, 108],
        "measurements": [],
        "type": TYPE_AIR_QUALITY,
    },
    "mepHealthConcern": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "epaIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "epaPrimaryPollutant": {
        "timestep": [-6, 108],
        "measurements": [],
        "type": TYPE_AIR_QUALITY,
    },
    "epaHealthConcern": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_AIR_QUALITY,
    },
    "treeIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_POLLEN,
    },
    "grassIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_POLLEN,
    },
    "grassGrassIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_POLLEN,
    },
    "weedIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_POLLEN,
    },
    "weedRagweedIndex": {
        "timestep": [-6, 108],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_POLLEN,
    },
    "fireIndex": {
        "timestep": [-6, 0],
        "measurements": ALL_MEASUREMENTS,
        "type": TYPE_WEATHER,
    },
}


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
