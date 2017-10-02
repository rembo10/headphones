"""
All exceptions used in CloudConvert Python wrapper derives from `APIError`
"""

class APIError(Exception):
    """Base CloudConvert API exception, all specific exceptions inherits from it."""

class HTTPError(APIError):
    """Raised when the request fails at a low level (DNS, network, ...)"""

class BadRequest(APIError):
    """Raised when a the CloudConvert API returns any HTTP error code 400"""

class ConversionFailed(APIError):
    """Raised when when a the CloudConvert API returns any HTTP error code 422"""

class TemporaryUnavailable(APIError):
    """Raised when a the CloudConvert API returns any HTTP error code 503"""

class InvalidResponse(APIError):
    """Raised when api response is not valid json"""

class InvalidParameterException(APIError):
    """Raised when request contains bad parameters."""

