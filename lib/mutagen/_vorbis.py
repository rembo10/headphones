# Vorbis comment support for Mutagen
# Copyright 2005-2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""Read and write Vorbis comment data.

Vorbis comments are freeform key/value pairs; keys are
case-insensitive ASCII and values are Unicode strings. A key may have
multiple values.

The specification is at http://www.xiph.org/vorbis/doc/v-comment.html.
"""

import sys

from cStringIO import StringIO

import mutagen
from mutagen._util import DictMixin, cdata


def is_valid_key(key):
    """Return true if a string is a valid Vorbis comment key.

    Valid Vorbis comment keys are printable ASCII between 0x20 (space)
    and 0x7D ('}'), excluding '='.
    """
    for c in key:
        if c < " " or c > "}" or c == "=":
            return False
    else:
        return bool(key)

istag = is_valid_key


class error(IOError):
    pass


class VorbisUnsetFrameError(error):
    pass


class VorbisEncodingError(error):
    pass


class VComment(mutagen.Metadata, list):
    """A Vorbis comment parser, accessor, and renderer.

    All comment ordering is preserved. A VComment is a list of
    key/value pairs, and so any Python list method can be used on it.

    Vorbis comments are always wrapped in something like an Ogg Vorbis
    bitstream or a FLAC metadata block, so this loads string data or a
    file-like object, not a filename.

    Attributes:
    vendor -- the stream 'vendor' (i.e. writer); default 'Mutagen'
    """

    vendor = u"Mutagen " + mutagen.version_string

    def __init__(self, data=None, *args, **kwargs):
        # Collect the args to pass to load, this lets child classes
        # override just load and get equivalent magic for the
        # constructor.
        if data is not None:
            if isinstance(data, str):
                data = StringIO(data)
            elif not hasattr(data, 'read'):
                raise TypeError("VComment requires string data or a file-like")
            self.load(data, *args, **kwargs)

    def load(self, fileobj, errors='replace', framing=True):
        """Parse a Vorbis comment from a file-like object.

        Keyword arguments:
        errors:
          'strict', 'replace', or 'ignore'. This affects Unicode decoding
          and how other malformed content is interpreted.
        framing -- if true, fail if a framing bit is not present

        Framing bits are required by the Vorbis comment specification,
        but are not used in FLAC Vorbis comment blocks.

        """
        try:
            vendor_length = cdata.uint_le(fileobj.read(4))
            self.vendor = fileobj.read(vendor_length).decode('utf-8', errors)
            count = cdata.uint_le(fileobj.read(4))
            for i in xrange(count):
                length = cdata.uint_le(fileobj.read(4))
                try:
                    string = fileobj.read(length).decode('utf-8', errors)
                except (OverflowError, MemoryError):
                    raise error("cannot read %d bytes, too large" % length)
                try:
                    tag, value = string.split('=', 1)
                except ValueError, err:
                    if errors == "ignore":
                        continue
                    elif errors == "replace":
                        tag, value = u"unknown%d" % i, string
                    else:
                        raise VorbisEncodingError, err, sys.exc_info()[2]
                try:
                    tag = tag.encode('ascii', errors)
                except UnicodeEncodeError:
                    raise VorbisEncodingError("invalid tag name %r" % tag)
                else:
                    if is_valid_key(tag):
                        self.append((tag, value))
            if framing and not ord(fileobj.read(1)) & 0x01:
                raise VorbisUnsetFrameError("framing bit was unset")
        except (cdata.error, TypeError):
            raise error("file is not a valid Vorbis comment")

    def validate(self):
        """Validate keys and values.

        Check to make sure every key used is a valid Vorbis key, and
        that every value used is a valid Unicode or UTF-8 string. If
        any invalid keys or values are found, a ValueError is raised.
        """

        if not isinstance(self.vendor, unicode):
            try:
                self.vendor.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError

        for key, value in self:
            try:
                if not is_valid_key(key):
                    raise ValueError
            except:
                raise ValueError("%r is not a valid key" % key)
            if not isinstance(value, unicode):
                try:
                    value.encode("utf-8")
                except:
                    raise ValueError("%r is not a valid value" % value)
        else:
            return True

    def clear(self):
        """Clear all keys from the comment."""
        del(self[:])

    def write(self, framing=True):
        """Return a string representation of the data.

        Validation is always performed, so calling this function on
        invalid data may raise a ValueError.

        Keyword arguments:
        framing -- if true, append a framing bit (see load)
        """

        self.validate()

        f = StringIO()
        f.write(cdata.to_uint_le(len(self.vendor.encode('utf-8'))))
        f.write(self.vendor.encode('utf-8'))
        f.write(cdata.to_uint_le(len(self)))
        for tag, value in self:
            comment = "%s=%s" % (tag, value.encode('utf-8'))
            f.write(cdata.to_uint_le(len(comment)))
            f.write(comment)
        if framing:
            f.write("\x01")
        return f.getvalue()

    def pprint(self):
        return "\n".join(["%s=%s" % (k.lower(), v) for k, v in self])


class VCommentDict(VComment, DictMixin):
    """A VComment that looks like a dictionary.

    This object differs from a dictionary in two ways. First,
    len(comment) will still return the number of values, not the
    number of keys. Secondly, iterating through the object will
    iterate over (key, value) pairs, not keys. Since a key may have
    multiple values, the same value may appear multiple times while
    iterating.

    Since Vorbis comment keys are case-insensitive, all keys are
    normalized to lowercase ASCII.
    """

    def __getitem__(self, key):
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.

        """
        key = key.lower().encode('ascii')
        values = [value for (k, value) in self if k.lower() == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    def __delitem__(self, key):
        """Delete all values associated with the key."""
        key = key.lower().encode('ascii')
        to_delete = filter(lambda x: x[0].lower() == key, self)
        if not to_delete:
            raise KeyError(key)
        else:
            map(self.remove, to_delete)

    def __contains__(self, key):
        """Return true if the key has any values."""
        key = key.lower().encode('ascii')
        for k, value in self:
            if k.lower() == key:
                return True
        else:
            return False

    def __setitem__(self, key, values):
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.

        """

        key = key.encode('ascii')
        if not isinstance(values, list):
            values = [values]
        try:
            del(self[key])
        except KeyError:
            pass
        for value in values:
            self.append((key, value))

    def keys(self):
        """Return all keys in the comment."""
        return self and list(set([k.lower() for k, v in self]))

    def as_dict(self):
        """Return a copy of the comment data in a real dict."""
        return dict([(key, self[key]) for key in self.keys()])
