from __future__ import division, absolute_import, print_function

from .util import BASESTRING, build_dict
from . import yaml_util
import os


class ConfigSource(dict):
    """A dictionary augmented with metadata about the source of the
    configuration.
    """
    def __init__(self, value, filename=None, default=False,
                 base_for_paths=False):
        """Create a configuration source from a dictionary.

        :param filename: The file with the data for this configuration source.

        :param default: Indicates whether this source provides the
            application's default configuration settings.

        :param base_for_paths: Indicates whether the source file's directory
        (i.e., the directory component of `self.filename`) should be used as
        the base directory for resolving relative path values provided by this
        source, instead of using the application's configuration directory. If
        no `filename` is provided, `base_for_paths` will be treated as False.
        See `templates.Filename` for details of the relative path resolution
        behavior.
        """
        super(ConfigSource, self).__init__(value)
        if (filename is not None
                and not isinstance(filename, BASESTRING)):
            raise TypeError(u'filename must be a string or None')
        self.filename = filename
        self.default = default
        self.base_for_paths = base_for_paths if filename is not None else False

    def __repr__(self):
        return 'ConfigSource({0!r}, {1!r}, {2!r}, {3!r})'.format(
            super(ConfigSource, self),
            self.filename,
            self.default,
            self.base_for_paths,
        )

    @classmethod
    def of(cls, value):
        """Given either a dictionary or a `ConfigSource` object, return
        a `ConfigSource` object. This lets a function accept either type
        of object as an argument.
        """
        if isinstance(value, ConfigSource):
            return value
        elif isinstance(value, dict):
            return ConfigSource(value)
        else:
            raise TypeError(u'source value must be a dict')


class YamlSource(ConfigSource):
    """A configuration data source that reads from a YAML file.
    """

    def __init__(self, filename=None, default=False, base_for_paths=False,
                 optional=False, loader=yaml_util.Loader):
        """Create a YAML data source by reading data from a file.

        May raise a `ConfigReadError`. However, if `optional` is
        enabled, this exception will not be raised in the case when the
        file does not exist---instead, the source will be silently
        empty.
        """
        filename = os.path.abspath(filename)
        super(YamlSource, self).__init__({}, filename, default, base_for_paths)
        self.loader = loader
        self.optional = optional
        self.load()

    def load(self):
        """Load YAML data from the source's filename.
        """
        if self.optional and not os.path.isfile(self.filename):
            value = {}
        else:
            value = yaml_util.load_yaml(self.filename,
                                        loader=self.loader) or {}
        self.update(value)


class EnvSource(ConfigSource):
    """A configuration data source loaded from environment variables.
    """
    def __init__(self, prefix, sep='__', lower=True, handle_lists=True,
                 parse_yaml_docs=False, loader=yaml_util.Loader):
        """Create a configuration source from the environment.

        :param prefix: The prefix used to identify the environment variables
            to be loaded into this configuration source.

        :param sep: Separator within variable names to define nested keys.

        :param lower: Indicates whether to convert variable names to lowercase
            after prefix matching.

        :param handle_lists: If variables are split into nested keys, indicates
            whether to search for sub-dicts with keys that are sequential
            integers starting from 0 and convert those dicts to lists.

        :param parse_yaml_docs: Enable parsing the values of environment
            variables as full YAML documents. By default, when False, values
            are parsed only as YAML scalars.

        :param loader: PyYAML Loader class to use to parse YAML values.
        """
        super(EnvSource, self).__init__({}, filename=None, default=False,
                                        base_for_paths=False)
        self.prefix = prefix
        self.sep = sep
        self.lower = lower
        self.handle_lists = handle_lists
        self.parse_yaml_docs = parse_yaml_docs
        self.loader = loader
        self.load()

    def load(self):
        """Load configuration data from the environment.
        """
        # Read config variables with prefix from the environment.
        config_vars = {}
        for var, value in os.environ.items():
            if var.startswith(self.prefix):
                key = var[len(self.prefix):]
                if self.lower:
                    key = key.lower()
                if self.parse_yaml_docs:
                    # Parse the value as a YAML document, which will convert
                    # string representations of dicts and lists into the
                    # appropriate object (ie, '{foo: bar}' to {'foo': 'bar'}).
                    # Will raise a ConfigReadError if YAML parsing fails.
                    value = yaml_util.load_yaml_string(value,
                                                       'env variable ' + var,
                                                       loader=self.loader)
                else:
                    # Parse the value as a YAML scalar so that values are type
                    # converted using the same rules as the YAML Loader (ie,
                    # numeric string to int/float, 'true' to True, etc.). Will
                    # not raise a ConfigReadError.
                    value = yaml_util.parse_as_scalar(value,
                                                      loader=self.loader)
                config_vars[key] = value
        if self.sep:
            # Build a nested dict, keeping keys with `None` values to allow
            # environment variables to unset values from lower priority sources
            config_vars = build_dict(config_vars, self.sep, keep_none=True)
        if self.handle_lists:
            for k, v in config_vars.items():
                config_vars[k] = self._convert_dict_lists(v)
        self.update(config_vars)

    @classmethod
    def _convert_dict_lists(cls, obj):
        """Recursively search for dicts where all of the keys are integers
        from 0 to the length of the dict, and convert them to lists.
        """
        # We only deal with dictionaries
        if not isinstance(obj, dict):
            return obj

        # Recursively search values for additional dicts to convert to lists
        for k, v in obj.items():
            obj[k] = cls._convert_dict_lists(v)

        try:
            # Convert the keys to integers, mapping the ints back to the keys
            int_to_key = {int(k): k for k in obj.keys()}
        except (ValueError):
            # Not all of the keys represent integers
            return obj
        try:
            # For the integers from 0 to the length of the dict, try to create
            # a list from the dict values using the integer to key mapping
            return [obj[int_to_key[i]] for i in range(len(obj))]
        except (KeyError):
            # At least one integer within the range is not a key of the dict
            return obj
