from __future__ import division, absolute_import, print_function

import yaml

__all__ = [
    'ConfigError', 'NotFoundError', 'ConfigValueError', 'ConfigTypeError',
    'ConfigTemplateError', 'ConfigReadError']

YAML_TAB_PROBLEM = "found character '\\t' that cannot start any token"

# Exceptions.


class ConfigError(Exception):
    """Base class for exceptions raised when querying a configuration.
    """


class NotFoundError(ConfigError):
    """A requested value could not be found in the configuration trees.
    """


class ConfigValueError(ConfigError):
    """The value in the configuration is illegal."""


class ConfigTypeError(ConfigValueError):
    """The value in the configuration did not match the expected type.
    """


class ConfigTemplateError(ConfigError):
    """Base class for exceptions raised because of an invalid template.
    """


class ConfigReadError(ConfigError):
    """A configuration source could not be read."""
    def __init__(self, name, reason=None):
        self.name = name
        self.reason = reason

        message = u'{0} could not be read'.format(name)
        if (isinstance(reason, yaml.scanner.ScannerError)
                and reason.problem == YAML_TAB_PROBLEM):
            # Special-case error message for tab indentation in YAML markup.
            message += u': found tab character at line {0}, column {1}'.format(
                reason.problem_mark.line + 1,
                reason.problem_mark.column + 1,
            )
        elif reason:
            # Generic error message uses exception's message.
            message += u': {0}'.format(reason)

        super(ConfigReadError, self).__init__(message)
