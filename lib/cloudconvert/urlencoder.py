"""
source: https://github.com/udemy/multidimensional_urlencode
should be changed to install requirement of "multidimensional_urlencode" as soon as https://github.com/uber/multidimensional_urlencode/pull/5 is merged

"""


try:
    from urllib.parse import urlencode as urllib_urlencode
except ImportError:
    from urllib import urlencode as urllib_urlencode


def flatten(d):
    """Return a dict as a list of lists.
    >>> flatten({"a": "b"})
    [['a', 'b']]
    >>> flatten({"a": [1, 2, 3]})
    [['a', [1, 2, 3]]]
    >>> flatten({"a": {"b": "c"}})
    [['a', 'b', 'c']]
    >>> flatten({"a": {"b": {"c": "e"}}})
    [['a', 'b', 'c', 'e']]
    >>> sorted(flatten({"a": {"b": "c", "d": "e"}}))
    [['a', 'b', 'c'], ['a', 'd', 'e']]
    >>> sorted(flatten({"a": {"b": "c", "d": "e"}, "b": {"c": "d"}}))
    [['a', 'b', 'c'], ['a', 'd', 'e'], ['b', 'c', 'd']]
    """

    if not isinstance(d, dict):
        return [[d]]

    returned = []
    for key, value in list(d.items()):
        # Each key, value is treated as a row.
        nested = flatten(value)
        for nest in nested:
            current_row = [key]
            current_row.extend(nest)
            returned.append(current_row)

    return returned


def parametrize(params):
    """Return list of params as params.
    >>> parametrize(['a'])
    'a'
    >>> parametrize(['a', 'b'])
    'a[b]'
    >>> parametrize(['a', 'b', 'c'])
    'a[b][c]'
    """
    returned = str(params[0])
    returned += "".join("[" + str(p) + "]" for p in params[1:])
    return returned


def urlencode(params):
    """Urlencode a multidimensional dict."""

    # Not doing duck typing here. Will make debugging easier.
    if not isinstance(params, dict):
        raise TypeError("Only dicts are supported.")

    params = flatten(params)

    url_params = {}
    for param in params:
        value = param.pop()

        name = parametrize(param)
        if isinstance(value, (list, tuple)):
            name += "[]"

        url_params[name] = value

    return urllib_urlencode(url_params, doseq=True)