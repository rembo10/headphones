from __future__ import division, absolute_import, print_function

import os
import re
import sys

from . import util
from . import exceptions

try:
    import enum
    SUPPORTS_ENUM = True
except ImportError:
    SUPPORTS_ENUM = False

try:
    import pathlib
    SUPPORTS_PATHLIB = True
except ImportError:
    SUPPORTS_PATHLIB = False

if sys.version_info >= (3, 3):
    from collections import abc
else:
    import collections as abc


REQUIRED = object()
"""A sentinel indicating that there is no default value and an exception
should be raised when the value is missing.
"""


class Template(object):
    """A value template for configuration fields.

    The template works like a type and instructs Confuse about how to
    interpret a deserialized YAML value. This includes type conversions,
    providing a default value, and validating for errors. For example, a
    filepath type might expand tildes and check that the file exists.
    """
    def __init__(self, default=REQUIRED):
        """Create a template with a given default value.

        If `default` is the sentinel `REQUIRED` (as it is by default),
        then an error will be raised when a value is missing. Otherwise,
        missing values will instead return `default`.
        """
        self.default = default

    def __call__(self, view):
        """Invoking a template on a view gets the view's value according
        to the template.
        """
        return self.value(view, self)

    def value(self, view, template=None):
        """Get the value for a `ConfigView`.

        May raise a `NotFoundError` if the value is missing (and the
        template requires it) or a `ConfigValueError` for invalid values.
        """
        try:
            value, _ = view.first()
            return self.convert(value, view)
        except exceptions.NotFoundError:
            pass

        # Get default value, or raise if required.
        return self.get_default_value(view.name)

    def get_default_value(self, key_name='default'):
        """Get the default value to return when the value is missing.

        May raise a `NotFoundError` if the value is required.
        """
        if not hasattr(self, 'default') or self.default is REQUIRED:
            # The value is required. A missing value is an error.
            raise exceptions.NotFoundError(u"{} not found".format(key_name))
        # The value is not required.
        return self.default

    def convert(self, value, view):
        """Convert the YAML-deserialized value to a value of the desired
        type.

        Subclasses should override this to provide useful conversions.
        May raise a `ConfigValueError` when the configuration is wrong.
        """
        # Default implementation does no conversion.
        return value

    def fail(self, message, view, type_error=False):
        """Raise an exception indicating that a value cannot be
        accepted.

        `type_error` indicates whether the error is due to a type
        mismatch rather than a malformed value. In this case, a more
        specific exception is raised.
        """
        exc_class = (
            exceptions.ConfigTypeError if type_error
            else exceptions.ConfigValueError)
        raise exc_class(u'{0}: {1}'.format(view.name, message))

    def __repr__(self):
        return '{0}({1})'.format(
            type(self).__name__,
            '' if self.default is REQUIRED else repr(self.default),
        )


class Integer(Template):
    """An integer configuration value template.
    """
    def convert(self, value, view):
        """Check that the value is an integer. Floats are rounded.
        """
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        else:
            self.fail(u'must be a number', view, True)


class Number(Template):
    """A numeric type: either an integer or a floating-point number.
    """
    def convert(self, value, view):
        """Check that the value is an int or a float.
        """
        if isinstance(value, util.NUMERIC_TYPES):
            return value
        else:
            self.fail(
                u'must be numeric, not {0}'.format(type(value).__name__),
                view,
                True
            )


class MappingTemplate(Template):
    """A template that uses a dictionary to specify other types for the
    values for a set of keys and produce a validated `AttrDict`.
    """
    def __init__(self, mapping):
        """Create a template according to a dict (mapping). The
        mapping's values should themselves either be Types or
        convertible to Types.
        """
        subtemplates = {}
        for key, typ in mapping.items():
            subtemplates[key] = as_template(typ)
        self.subtemplates = subtemplates

    def value(self, view, template=None):
        """Get a dict with the same keys as the template and values
        validated according to the value types.
        """
        out = AttrDict()
        for key, typ in self.subtemplates.items():
            out[key] = typ.value(view[key], self)
        return out

    def __repr__(self):
        return 'MappingTemplate({0})'.format(repr(self.subtemplates))


class Sequence(Template):
    """A template used to validate lists of similar items,
    based on a given subtemplate.
    """
    def __init__(self, subtemplate):
        """Create a template for a list with items validated
        on a given subtemplate.
        """
        self.subtemplate = as_template(subtemplate)

    def value(self, view, template=None):
        """Get a list of items validated against the template.
        """
        out = []
        for item in view.sequence():
            out.append(self.subtemplate.value(item, self))
        return out

    def __repr__(self):
        return 'Sequence({0})'.format(repr(self.subtemplate))


class MappingValues(Template):
    """A template used to validate mappings of similar items,
    based on a given subtemplate applied to the values.

    All keys in the mapping are considered valid, but values
    must pass validation by the subtemplate. Similar to the
    Sequence template but for mappings.
    """
    def __init__(self, subtemplate):
        """Create a template for a mapping with variable keys
        and item values validated on a given subtemplate.
        """
        self.subtemplate = as_template(subtemplate)

    def value(self, view, template=None):
        """Get a dict with the same keys as the view and the
        value of each item validated against the subtemplate.
        """
        out = {}
        for key, item in view.items():
            out[key] = self.subtemplate.value(item, self)
        return out

    def __repr__(self):
        return 'MappingValues({0})'.format(repr(self.subtemplate))


class String(Template):
    """A string configuration value template.
    """
    def __init__(self, default=REQUIRED, pattern=None, expand_vars=False):
        """Create a template with the added optional `pattern` argument,
        a regular expression string that the value should match.
        """
        super(String, self).__init__(default)
        self.pattern = pattern
        self.expand_vars = expand_vars
        if pattern:
            self.regex = re.compile(pattern)

    def __repr__(self):
        args = []

        if self.default is not REQUIRED:
            args.append(repr(self.default))

        if self.pattern is not None:
            args.append('pattern=' + repr(self.pattern))

        return 'String({0})'.format(', '.join(args))

    def convert(self, value, view):
        """Check that the value is a string and matches the pattern.
        """
        if not isinstance(value, util.BASESTRING):
            self.fail(u'must be a string', view, True)

        if self.pattern and not self.regex.match(value):
            self.fail(
                u"must match the pattern {0}".format(self.pattern),
                view
            )

        if self.expand_vars:
            return os.path.expandvars(value)
        else:
            return value


class Choice(Template):
    """A template that permits values from a sequence of choices.
    """
    def __init__(self, choices, default=REQUIRED):
        """Create a template that validates any of the values from the
        iterable `choices`.

        If `choices` is a map, then the corresponding value is emitted.
        Otherwise, the value itself is emitted.

        If `choices` is a `Enum`, then the enum entry with the value is
        emitted.
        """
        super(Choice, self).__init__(default)
        self.choices = choices

    def convert(self, value, view):
        """Ensure that the value is among the choices (and remap if the
        choices are a mapping).
        """
        if (SUPPORTS_ENUM and isinstance(self.choices, type)
                and issubclass(self.choices, enum.Enum)):
            try:
                return self.choices(value)
            except ValueError:
                self.fail(
                    u'must be one of {0!r}, not {1!r}'.format(
                        [c.value for c in self.choices], value
                    ),
                    view
                )

        if value not in self.choices:
            self.fail(
                u'must be one of {0!r}, not {1!r}'.format(
                    list(self.choices), value
                ),
                view
            )

        if isinstance(self.choices, abc.Mapping):
            return self.choices[value]
        else:
            return value

    def __repr__(self):
        return 'Choice({0!r})'.format(self.choices)


class OneOf(Template):
    """A template that permits values complying to one of the given templates.
    """
    def __init__(self, allowed, default=REQUIRED):
        super(OneOf, self).__init__(default)
        self.allowed = list(allowed)

    def __repr__(self):
        args = []

        if self.allowed is not None:
            args.append('allowed=' + repr(self.allowed))

        if self.default is not REQUIRED:
            args.append(repr(self.default))

        return 'OneOf({0})'.format(', '.join(args))

    def value(self, view, template):
        self.template = template
        return super(OneOf, self).value(view, template)

    def convert(self, value, view):
        """Ensure that the value follows at least one template.
        """
        is_mapping = isinstance(self.template, MappingTemplate)

        for candidate in self.allowed:
            try:
                if is_mapping:
                    if isinstance(candidate, Filename) and \
                            candidate.relative_to:
                        next_template = candidate.template_with_relatives(
                            view,
                            self.template
                        )

                        next_template.subtemplates[view.key] = as_template(
                            candidate
                        )
                    else:
                        next_template = MappingTemplate({view.key: candidate})

                    return view.parent.get(next_template)[view.key]
                else:
                    return view.get(candidate)
            except exceptions.ConfigTemplateError:
                raise
            except exceptions.ConfigError:
                pass
            except ValueError as exc:
                raise exceptions.ConfigTemplateError(exc)

        self.fail(
            u'must be one of {0}, not {1}'.format(
                repr(self.allowed), repr(value)
            ),
            view
        )


class StrSeq(Template):
    """A template for values that are lists of strings.

    Validates both actual YAML string lists and single strings. Strings
    can optionally be split on whitespace.
    """
    def __init__(self, split=True, default=REQUIRED):
        """Create a new template.

        `split` indicates whether, when the underlying value is a single
        string, it should be split on whitespace. Otherwise, the
        resulting value is a list containing a single string.
        """
        super(StrSeq, self).__init__(default)
        self.split = split

    def _convert_value(self, x, view):
        if isinstance(x, util.STRING):
            return x
        elif isinstance(x, bytes):
            return x.decode('utf-8', 'ignore')
        else:
            self.fail(u'must be a list of strings', view, True)

    def convert(self, value, view):
        if isinstance(value, bytes):
            value = value.decode('utf-8', 'ignore')

        if isinstance(value, util.STRING):
            if self.split:
                value = value.split()
            else:
                value = [value]
        else:
            try:
                value = list(value)
            except TypeError:
                self.fail(u'must be a whitespace-separated string or a list',
                          view, True)
        return [self._convert_value(v, view) for v in value]


class Pairs(StrSeq):
    """A template for ordered key-value pairs.

    This can either be given with the same syntax as for `StrSeq` (i.e. without
    values), or as a list of strings and/or single-element mappings such as::

        - key: value
        - [key, value]
        - key

    The result is a list of two-element tuples. If no value is provided, the
    `default_value` will be returned as the second element.
    """

    def __init__(self, default_value=None):
        """Create a new template.

        `default` is the dictionary value returned for items that are not
        a mapping, but a single string.
        """
        super(Pairs, self).__init__(split=True)
        self.default_value = default_value

    def _convert_value(self, x, view):
        try:
            return (super(Pairs, self)._convert_value(x, view),
                    self.default_value)
        except exceptions.ConfigTypeError:
            if isinstance(x, abc.Mapping):
                if len(x) != 1:
                    self.fail(u'must be a single-element mapping', view, True)
                k, v = util.iter_first(x.items())
            elif isinstance(x, abc.Sequence):
                if len(x) != 2:
                    self.fail(u'must be a two-element list', view, True)
                k, v = x
            else:
                # Is this even possible? -> Likely, if some !directive cause
                # YAML to parse this to some custom type.
                self.fail(u'must be a single string, mapping, or a list'
                          u'' + str(x),
                          view, True)
            return (super(Pairs, self)._convert_value(k, view),
                    super(Pairs, self)._convert_value(v, view))


class Filename(Template):
    """A template that validates strings as filenames.

    Filenames are returned as absolute, tilde-free paths.

    Relative paths are relative to the template's `cwd` argument
    when it is specified. Otherwise, if the paths come from a file,
    they will be relative to the configuration directory (see the
    `config_dir` method) by default or to the base directory of the
    config file if either the source has `base_for_paths` set to True
    or the template has `in_source_dir` set to True. Paths from sources
    without a file are relative to the current working directory. This
    helps attain the expected behavior when using command-line options.
    """
    def __init__(self, default=REQUIRED, cwd=None, relative_to=None,
                 in_app_dir=False, in_source_dir=False):
        """`relative_to` is the name of a sibling value that is
        being validated at the same time.

        `in_app_dir` indicates whether the path should be resolved
        inside the application's config directory (even when the setting
        does not come from a file).

        `in_source_dir` indicates whether the path should be resolved
        relative to the directory containing the source file, if there is
        one, taking precedence over the application's config directory.
        """
        super(Filename, self).__init__(default)
        self.cwd = cwd
        self.relative_to = relative_to
        self.in_app_dir = in_app_dir
        self.in_source_dir = in_source_dir

    def __repr__(self):
        args = []

        if self.default is not REQUIRED:
            args.append(repr(self.default))

        if self.cwd is not None:
            args.append('cwd=' + repr(self.cwd))

        if self.relative_to is not None:
            args.append('relative_to=' + repr(self.relative_to))

        if self.in_app_dir:
            args.append('in_app_dir=True')

        if self.in_source_dir:
            args.append('in_source_dir=True')

        return 'Filename({0})'.format(', '.join(args))

    def resolve_relative_to(self, view, template):
        if not isinstance(template, (abc.Mapping, MappingTemplate)):
            # disallow config.get(Filename(relative_to='foo'))
            raise exceptions.ConfigTemplateError(
                u'relative_to may only be used when getting multiple values.'
            )

        elif self.relative_to == view.key:
            raise exceptions.ConfigTemplateError(
                u'{0} is relative to itself'.format(view.name)
            )

        elif self.relative_to not in view.parent.keys():
            # self.relative_to is not in the config
            self.fail(
                (
                    u'needs sibling value "{0}" to expand relative path'
                ).format(self.relative_to),
                view
            )

        old_template = {}
        old_template.update(template.subtemplates)

        # save time by skipping MappingTemplate's init loop
        next_template = MappingTemplate({})
        next_relative = self.relative_to

        # gather all the needed templates and nothing else
        while next_relative is not None:
            try:
                # pop to avoid infinite loop because of recursive
                # relative paths
                rel_to_template = old_template.pop(next_relative)
            except KeyError:
                if next_relative in template.subtemplates:
                    # we encountered this config key previously
                    raise exceptions.ConfigTemplateError((
                        u'{0} and {1} are recursively relative'
                    ).format(view.name, self.relative_to))
                else:
                    raise exceptions.ConfigTemplateError((
                        u'missing template for {0}, needed to expand {1}\'s'
                        u'relative path'
                    ).format(self.relative_to, view.name))

            next_template.subtemplates[next_relative] = rel_to_template
            next_relative = rel_to_template.relative_to

        return view.parent.get(next_template)[self.relative_to]

    def value(self, view, template=None):
        try:
            path, source = view.first()
        except exceptions.NotFoundError:
            return self.get_default_value(view.name)

        if not isinstance(path, util.BASESTRING):
            self.fail(
                u'must be a filename, not {0}'.format(type(path).__name__),
                view,
                True
            )
        path = os.path.expanduser(util.STRING(path))

        if not os.path.isabs(path):
            if self.cwd is not None:
                # relative to the template's argument
                path = os.path.join(self.cwd, path)

            elif self.relative_to is not None:
                path = os.path.join(
                    self.resolve_relative_to(view, template),
                    path,
                )

            elif ((source.filename and self.in_source_dir)
                  or (source.base_for_paths and not self.in_app_dir)):
                # relative to the directory the source file is in.
                path = os.path.join(os.path.dirname(source.filename), path)

            elif source.filename or self.in_app_dir:
                # From defaults: relative to the app's directory.
                path = os.path.join(view.root().config_dir(), path)

        return os.path.abspath(path)


class Path(Filename):
    """A template that validates strings as `pathlib.Path` objects.

    Filenames are parsed equivalent to the `Filename` template and then
    converted to `pathlib.Path` objects.

    For Python 2 it returns the original path as returned by the `Filename`
    template.
    """
    def value(self, view, template=None):
        value = super(Path, self).value(view, template)
        if value is None:
            return
        import pathlib
        return pathlib.Path(value)


class Optional(Template):
    """A template that makes a subtemplate optional.

    If the value is present and not null, it must validate against the
    subtemplate. However, if the value is null or missing, the template will
    still validate, returning a default value. If `allow_missing` is False,
    the template will not allow missing values while still permitting null.
    """

    def __init__(self, subtemplate, default=None, allow_missing=True):
        self.subtemplate = as_template(subtemplate)
        if default is None:
            # When no default is passed, try to use the subtemplate's
            # default value as the default for this template
            try:
                default = self.subtemplate.get_default_value()
            except exceptions.NotFoundError:
                pass
        self.default = default
        self.allow_missing = allow_missing

    def value(self, view, template=None):
        try:
            value, _ = view.first()
        except exceptions.NotFoundError:
            if self.allow_missing:
                # Value is missing but not required
                return self.default
            # Value must be present even though it can be null. Raise an error.
            raise exceptions.NotFoundError(u'{} not found'.format(view.name))

        if value is None:
            # None (ie, null) is always a valid value
            return self.default
        return self.subtemplate.value(view, self)

    def __repr__(self):
        return 'Optional({0}, {1}, allow_missing={2})'.format(
            repr(self.subtemplate),
            repr(self.default),
            self.allow_missing,
        )


class TypeTemplate(Template):
    """A simple template that checks that a value is an instance of a
    desired Python type.
    """
    def __init__(self, typ, default=REQUIRED):
        """Create a template that checks that the value is an instance
        of `typ`.
        """
        super(TypeTemplate, self).__init__(default)
        self.typ = typ

    def convert(self, value, view):
        if not isinstance(value, self.typ):
            self.fail(
                u'must be a {0}, not {1}'.format(
                    self.typ.__name__,
                    type(value).__name__,
                ),
                view,
                True
            )
        return value


class AttrDict(dict):
    """A `dict` subclass that can be accessed via attributes (dot
    notation) for convenience.
    """
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


def as_template(value):
    """Convert a simple "shorthand" Python value to a `Template`.
    """
    if isinstance(value, Template):
        # If it's already a Template, pass it through.
        return value
    elif isinstance(value, abc.Mapping):
        # Dictionaries work as templates.
        return MappingTemplate(value)
    elif value is int:
        return Integer()
    elif isinstance(value, int):
        return Integer(value)
    elif isinstance(value, type) and issubclass(value, util.BASESTRING):
        return String()
    elif isinstance(value, util.BASESTRING):
        return String(value)
    elif isinstance(value, set):
        # convert to list to avoid hash related problems
        return Choice(list(value))
    elif (SUPPORTS_ENUM and isinstance(value, type)
            and issubclass(value, enum.Enum)):
        return Choice(value)
    elif isinstance(value, list):
        return OneOf(value)
    elif value is float:
        return Number()
    elif isinstance(value, float):
        return Number(value)
    elif SUPPORTS_PATHLIB and isinstance(value, pathlib.PurePath):
        return Path(value)
    elif value is None:
        return Template(None)
    elif value is REQUIRED:
        return Template()
    elif value is dict:
        return TypeTemplate(abc.Mapping)
    elif value is list:
        return TypeTemplate(abc.Sequence)
    elif isinstance(value, type):
        return TypeTemplate(value)
    else:
        raise ValueError(u'cannot convert to template: {0!r}'.format(value))
