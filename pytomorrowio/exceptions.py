"""Exceptions for pytomorrowio."""


class TomorrowioException(Exception):
    """Base Exception class for pytomorrowio."""


class MalformedRequestException(TomorrowioException):
    """Raised when request was malformed."""


class InvalidAPIKeyException(TomorrowioException):
    """Raised when API key is invalid."""


class RateLimitedException(TomorrowioException):
    """Raised when API rate limit has been exceeded."""


class UnknownException(TomorrowioException):
    """Raised when unknown error occurs."""


class CantConnectException(TomorrowioException):
    """Raise when client can't connect to Tomorrowio API."""


class InvalidTimestep(TomorrowioException):
    """Raise when an invalid timestep is specified."""
