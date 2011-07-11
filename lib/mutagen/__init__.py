#! /usr/bin/env python
#
# mutagen aims to be an all purpose media tagging library
# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id: __init__.py 4348 2008-12-02 02:41:15Z piman $
#

"""Mutagen aims to be an all purpose tagging library.

    import mutagen.[format]
    metadata = mutagen.[format].Open(filename)

metadata acts like a dictionary of tags in the file. Tags are generally a
list of string-like values, but may have additional methods available
depending on tag or format. They may also be entirely different objects
for certain keys, again depending on format.
"""

version = (1, 20)
version_string = ".".join(map(str, version))

import warnings

from lib.mutagen import _util

class Metadata(object):
    """An abstract dict-like object.

    Metadata is the base class for many of the tag objects in Mutagen.
    """

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            self.load(*args, **kwargs)

    def load(self, *args, **kwargs):
        raise NotImplementedError

    def save(self, filename=None):
        raise NotImplementedError

    def delete(self, filename=None):
        raise NotImplementedError

class FileType(_util.DictMixin):
    """An abstract object wrapping tags and audio stream information.

    Attributes:
    info -- stream information (length, bitrate, sample rate)
    tags -- metadata tags, if any

    Each file format has different potential tags and stream
    information.

    FileTypes implement an interface very similar to Metadata; the
    dict interface, save, load, and delete calls on a FileType call
    the appropriate methods on its tag data.
    """

    info = None
    tags = None
    filename = None
    _mimes = ["application/octet-stream"]

    def __init__(self, filename=None, *args, **kwargs):
        if filename is None:
            warnings.warn("FileType constructor requires a filename",
                          DeprecationWarning)
        else:
            self.load(filename, *args, **kwargs)

    def load(self, filename, *args, **kwargs):
        raise NotImplementedError

    def __getitem__(self, key):
        """Look up a metadata tag key.

        If the file has no tags at all, a KeyError is raised.
        """
        if self.tags is None: raise KeyError, key
        else: return self.tags[key]

    def __setitem__(self, key, value):
        """Set a metadata tag.

        If the file has no tags, an appropriate format is added (but
        not written until save is called).
        """
        if self.tags is None:
            self.add_tags()
        self.tags[key] = value

    def __delitem__(self, key):
        """Delete a metadata tag key.

        If the file has no tags at all, a KeyError is raised.
        """
        if self.tags is None: raise KeyError, key
        else: del(self.tags[key])

    def keys(self):
        """Return a list of keys in the metadata tag.

        If the file has no tags at all, an empty list is returned.
        """
        if self.tags is None: return []
        else: return self.tags.keys()

    def delete(self, filename=None):
        """Remove tags from a file."""
        if self.tags is not None:
            if filename is None:
                filename = self.filename
            else:
                warnings.warn(
                    "delete(filename=...) is deprecated, reload the file",
                    DeprecationWarning)
            return self.tags.delete(filename)

    def save(self, filename=None, **kwargs):
        """Save metadata tags."""
        if filename is None:
            filename = self.filename
        else:
            warnings.warn(
                "save(filename=...) is deprecated, reload the file",
                DeprecationWarning)
        if self.tags is not None:
            return self.tags.save(filename, **kwargs)
        else: raise ValueError("no tags in file")

    def pprint(self):
        """Print stream information and comment key=value pairs."""
        stream = "%s (%s)" % (self.info.pprint(), self.mime[0])
        try: tags = self.tags.pprint()
        except AttributeError:
            return stream
        else: return stream + ((tags and "\n" + tags) or "")

    def add_tags(self):
        raise NotImplementedError

    def __get_mime(self):
        mimes = []
        for Kind in type(self).__mro__:
            for mime in getattr(Kind, '_mimes', []):
                if mime not in mimes:
                    mimes.append(mime)
        return mimes

    mime = property(__get_mime)

def File(filename, options=None, easy=False):
    """Guess the type of the file and try to open it.

    The file type is decided by several things, such as the first 128
    bytes (which usually contains a file type identifier), the
    filename extension, and the presence of existing tags.

    If no appropriate type could be found, None is returned.
    """

    if options is None:
        from lib.mutagen.asf import ASF
        from lib.mutagen.apev2 import APEv2File
        from lib.mutagen.flac import FLAC
        if easy:
            from lib.mutagen.easyid3 import EasyID3FileType as ID3FileType
        else:
            from lib.mutagen.id3 import ID3FileType
        if easy:
            from lib.mutagen.mp3 import EasyMP3 as MP3
        else:
            from lib.mutagen.mp3 import MP3
        from lib.mutagen.oggflac import OggFLAC
        from lib.mutagen.oggspeex import OggSpeex
        from lib.mutagen.oggtheora import OggTheora
        from lib.mutagen.oggvorbis import OggVorbis
        if easy:
            from lib.mutagen.trueaudio import EasyTrueAudio as TrueAudio
        else:
            from lib.mutagen.trueaudio import TrueAudio
        from lib.mutagen.wavpack import WavPack
        if easy:
            from lib.mutagen.easymp4 import EasyMP4 as MP4
        else:
            from lib.mutagen.mp4 import MP4
        from lib.mutagen.musepack import Musepack
        from lib.mutagen.monkeysaudio import MonkeysAudio
        from lib.mutagen.optimfrog import OptimFROG
        options = [MP3, TrueAudio, OggTheora, OggSpeex, OggVorbis, OggFLAC,
                   FLAC, APEv2File, MP4, ID3FileType, WavPack, Musepack,
                   MonkeysAudio, OptimFROG, ASF]

    if not options:
        return None

    fileobj = file(filename, "rb")
    try:
        header = fileobj.read(128)
        # Sort by name after score. Otherwise import order affects
        # Kind sort order, which affects treatment of things with
        # equals scores.
        results = [(Kind.score(filename, fileobj, header), Kind.__name__)
                   for Kind in options]
    finally:
        fileobj.close()
    results = zip(results, options)
    results.sort()
    (score, name), Kind = results[-1]
    if score > 0: return Kind(filename)
    else: return None
