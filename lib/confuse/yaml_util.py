from __future__ import division, absolute_import, print_function

from collections import OrderedDict
import yaml
from .exceptions import ConfigReadError
from .util import BASESTRING

# YAML loading.


class Loader(yaml.SafeLoader):
    """A customized YAML loader. This loader deviates from the official
    YAML spec in a few convenient ways:

    - All strings as are Unicode objects.
    - All maps are OrderedDicts.
    - Strings can begin with % without quotation.
    """
    # All strings should be Unicode objects, regardless of contents.
    def _construct_unicode(self, node):
        return self.construct_scalar(node)

    # Use ordered dictionaries for every YAML map.
    # From https://gist.github.com/844388
    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(
                None, None,
                u'expected a mapping node, but found %s' % node.id,
                node.start_mark
            )

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    u'while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc,
                    key_node.start_mark
                )
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    # Allow bare strings to begin with %. Directives are still detected.
    def check_plain(self):
        plain = super(Loader, self).check_plain()
        return plain or self.peek() == '%'

    @staticmethod
    def add_constructors(loader):
        """Modify a PyYAML Loader class to add extra constructors for strings
        and maps. Call this method on a custom Loader class to make it behave
        like Confuse's own Loader
        """
        loader.add_constructor('tag:yaml.org,2002:str',
                               Loader._construct_unicode)
        loader.add_constructor('tag:yaml.org,2002:map',
                               Loader.construct_yaml_map)
        loader.add_constructor('tag:yaml.org,2002:omap',
                               Loader.construct_yaml_map)


Loader.add_constructors(Loader)


def load_yaml(filename, loader=Loader):
    """Read a YAML document from a file. If the file cannot be read or
    parsed, a ConfigReadError is raised.
    loader is the PyYAML Loader class to use to parse the YAML. By default,
    this is Confuse's own Loader class, which is like SafeLoader with
    extra constructors.
    """
    try:
        with open(filename, 'rb') as f:
            return yaml.load(f, Loader=loader)
    except (IOError, yaml.error.YAMLError) as exc:
        raise ConfigReadError(filename, exc)


def load_yaml_string(yaml_string, name, loader=Loader):
    """Read a YAML document from a string. If the string cannot be parsed,
    a ConfigReadError is raised.
    `yaml_string` is a string to be parsed as a YAML document.
    `name` is the name to use in error messages.
    `loader` is the PyYAML Loader class to use to parse the YAML. By default,
    this is Confuse's own Loader class, which is like SafeLoader with
    extra constructors.
    """
    try:
        return yaml.load(yaml_string, Loader=loader)
    except yaml.error.YAMLError as exc:
        raise ConfigReadError(name, exc)


def parse_as_scalar(value, loader=Loader):
    """Parse a value as if it were a YAML scalar to perform type conversion
    that is consistent with YAML documents.
    `value` should be a string. Non-string inputs or strings that raise YAML
    errors will be returned unchanged.
    `Loader` is the PyYAML Loader class to use for parsing, defaulting to
    Confuse's own Loader class.

    Examples with the default Loader:
      - '1' will return 1 as an integer
      - '1.0' will return 1 as a float
      - 'true' will return True
      - The empty string '' will return None
    """
    # We only deal with strings
    if not isinstance(value, BASESTRING):
        return value
    try:
        loader = loader('')
        tag = loader.resolve(yaml.ScalarNode, value, (True, False))
        node = yaml.ScalarNode(tag, value)
        return loader.construct_object(node)
    except yaml.error.YAMLError:
        # Fallback to returning the value unchanged
        return value


# YAML dumping.

class Dumper(yaml.SafeDumper):
    """A PyYAML Dumper that represents OrderedDicts as ordinary mappings
    (in order, of course).
    """
    # From http://pyyaml.org/attachment/ticket/161/use_ordered_dict.py
    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = yaml.MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = False
        if hasattr(mapping, 'items'):
            mapping = list(mapping.items())
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, yaml.ScalarNode)
                    and not node_key.style):
                best_style = False
            if not (isinstance(node_value, yaml.ScalarNode)
                    and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_list(self, data):
        """If a list has less than 4 items, represent it in inline style
        (i.e. comma separated, within square brackets).
        """
        node = super(Dumper, self).represent_list(data)
        length = len(data)
        if self.default_flow_style is None and length < 4:
            node.flow_style = True
        elif self.default_flow_style is None:
            node.flow_style = False
        return node

    def represent_bool(self, data):
        """Represent bool as 'yes' or 'no' instead of 'true' or 'false'.
        """
        if data:
            value = u'yes'
        else:
            value = u'no'
        return self.represent_scalar('tag:yaml.org,2002:bool', value)

    def represent_none(self, data):
        """Represent a None value with nothing instead of 'none'.
        """
        return self.represent_scalar('tag:yaml.org,2002:null', '')


Dumper.add_representer(OrderedDict, Dumper.represent_dict)
Dumper.add_representer(bool, Dumper.represent_bool)
Dumper.add_representer(type(None), Dumper.represent_none)
Dumper.add_representer(list, Dumper.represent_list)


def restore_yaml_comments(data, default_data):
    """Scan default_data for comments (we include empty lines in our
    definition of comments) and place them before the same keys in data.
    Only works with comments that are on one or more own lines, i.e.
    not next to a yaml mapping.
    """
    comment_map = dict()
    default_lines = iter(default_data.splitlines())
    for line in default_lines:
        if not line:
            comment = "\n"
        elif line.startswith("#"):
            comment = "{0}\n".format(line)
        else:
            continue
        while True:
            line = next(default_lines)
            if line and not line.startswith("#"):
                break
            comment += "{0}\n".format(line)
        key = line.split(':')[0].strip()
        comment_map[key] = comment
    out_lines = iter(data.splitlines())
    out_data = ""
    for line in out_lines:
        key = line.split(':')[0].strip()
        if key in comment_map:
            out_data += comment_map[key]
        out_data += "{0}\n".format(line)
    return out_data
