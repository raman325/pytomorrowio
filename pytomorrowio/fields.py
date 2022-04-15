"""Tomorrow.io field definitions"""
from dataclasses import dataclass
from datetime import timedelta
from typing import List

from .const import (
    ONE_DAY,
    ONE_HOUR,
    REALTIME,
    TYPE_AIR_QUALITY,
    TYPE_FIRE,
    TYPE_POLLEN,
    TYPE_PRECIPITATION,
    TYPE_SOLAR,
    TYPE_WEATHER,
)

MIN = "Min"
MAX = "Max"
AVG = "Avg"

ALL_MEASUREMENTS = [MIN, MAX, AVG]
NO_AVG = [MIN, MAX]


@dataclass
class FieldDefinition:
    """Tomorrow.io field definition"""

    max_timestep: timedelta
    measurements: List[str]
    type: str


FIELDS_V4 = {
    "temperature": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "temperatureApparent": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "dewPoint": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "humidity": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "windSpeed": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "windDirection": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=[AVG],
        type=TYPE_WEATHER,
    ),
    "windGust": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "pressureSurfaceLevel": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "pressureSeaLevel": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "precipitationIntensity": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_PRECIPITATION,
    ),
    "precipitationProbability": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_PRECIPITATION,
    ),
    "precipitationType": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=[],
        type=TYPE_PRECIPITATION,
    ),
    "hailBinary": FieldDefinition(
        max_timestep=REALTIME,
        measurements=[],
        type=TYPE_PRECIPITATION,
    ),
    "solarGHI": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_SOLAR,
    ),
    "solarDNI": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_SOLAR,
    ),
    "solarDHI": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_SOLAR,
    ),
    "visibility": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "cloudCover": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "cloudBase": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "cloudCeiling": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_WEATHER,
    ),
    "weatherCode": FieldDefinition(
        max_timestep=ONE_DAY,
        measurements=NO_AVG,
        type=TYPE_WEATHER,
    ),
    "particulateMatter25": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "particulateMatter10": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "pollutantO3": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "pollutantNO2": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "pollutantCO": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "pollutantSO2": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "mepIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "mepPrimaryPollutant": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=[],
        type=TYPE_AIR_QUALITY,
    ),
    "mepHealthConcern": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "epaIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "epaPrimaryPollutant": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=[],
        type=TYPE_AIR_QUALITY,
    ),
    "epaHealthConcern": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_AIR_QUALITY,
    ),
    "treeIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_POLLEN,
    ),
    "grassIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_POLLEN,
    ),
    "grassGrassIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_POLLEN,
    ),
    "weedIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_POLLEN,
    ),
    "weedRagweedIndex": FieldDefinition(
        max_timestep=ONE_HOUR,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_POLLEN,
    ),
    "fireIndex": FieldDefinition(
        max_timestep=REALTIME,
        measurements=ALL_MEASUREMENTS,
        type=TYPE_FIRE,
    ),
}
