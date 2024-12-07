"""Deprecated HTTP header parsing helpers."""
# for compatibility, expose accidentally here
import warnings

from .._private_api.compat.headers import _parse_param, parse_header  # noqa


warnings.warn(
    'Import `cherrypy._private_api.compat.headers` '
    'instead of `cherrypy.lib.headers`',
    DeprecationWarning,
    stacklevel=2,
)
