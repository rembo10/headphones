# id3 support for mutagen
# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""ID3v2 reading and writing.

This is based off of the following references:

* http://id3.org/id3v2.4.0-structure
* http://id3.org/id3v2.4.0-frames
* http://id3.org/id3v2.3.0
* http://id3.org/id3v2-00
* http://id3.org/ID3v1

Its largest deviation from the above (versions 2.3 and 2.2) is that it
will not interpret the / characters as a separator, and will almost
always accept null separators to generate multi-valued text frames.

Because ID3 frame structure differs between frame types, each frame is
implemented as a different class (e.g. TIT2 as mutagen.id3.TIT2). Each
frame's documentation contains a list of its attributes.

Since this file's documentation is a little unwieldy, you are probably
interested in the :class:`ID3` class to start with.
"""

__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']

import struct

from struct import unpack, pack, error as StructError

import mutagen
from mutagen._util import insert_bytes, delete_bytes, DictProxy

from mutagen._id3util import *
from mutagen._id3frames import *
from mutagen._id3specs import *


class ID3(DictProxy, mutagen.Metadata):
    """A file with an ID3v2 tag.

    Attributes:

    * version -- ID3 tag version as a tuple
    * unknown_frames -- raw frame data of any unknown frames found
    * size -- the total size of the ID3 tag, including the header
    """

    PEDANTIC = True
    version = (2, 4, 0)

    filename = None
    size = 0
    __flags = 0
    __readbytes = 0
    __crc = None
    __unknown_version = None

    _V24 = (2, 4, 0)
    _V23 = (2, 3, 0)
    _V22 = (2, 2, 0)
    _V11 = (1, 1)

    def __init__(self, *args, **kwargs):
        self.unknown_frames = []
        super(ID3, self).__init__(*args, **kwargs)

    def __fullread(self, size):
        try:
            if size < 0:
                raise ValueError('Requested bytes (%s) less than zero' % size)
            if size > self.__filesize:
                raise EOFError('Requested %#x of %#x (%s)' % (
                    long(size), long(self.__filesize), self.filename))
        except AttributeError:
            pass
        data = self.__fileobj.read(size)
        if len(data) != size:
            raise EOFError
        self.__readbytes += size
        return data

    def load(self, filename, known_frames=None, translate=True, v2_version=4):
        """Load tags from a filename.

        Keyword arguments:

        * filename -- filename to load tag data from
        * known_frames -- dict mapping frame IDs to Frame objects
        * translate -- Update all tags to ID3v2.3/4 internally. If you
                       intend to save, this must be true or you have to
                       call update_to_v23() / update_to_v24() manually.
        * v2_version -- if update_to_v23 or update_to_v24 get called (3 or 4)

        Example of loading a custom frame::

            my_frames = dict(mutagen.id3.Frames)
            class XMYF(Frame): ...
            my_frames["XMYF"] = XMYF
            mutagen.id3.ID3(filename, known_frames=my_frames)
        """

        if not v2_version in (3, 4):
            raise ValueError("Only 3 and 4 possible for v2_version")

        from os.path import getsize

        self.filename = filename
        self.__known_frames = known_frames
        self.__fileobj = open(filename, 'rb')
        self.__filesize = getsize(filename)
        try:
            try:
                self.__load_header()
            except EOFError:
                self.size = 0
                raise ID3NoHeaderError("%s: too small (%d bytes)" % (
                    filename, self.__filesize))
            except (ID3NoHeaderError, ID3UnsupportedVersionError), err:
                self.size = 0
                import sys
                stack = sys.exc_info()[2]
                try:
                    self.__fileobj.seek(-128, 2)
                except EnvironmentError:
                    raise err, None, stack
                else:
                    frames = ParseID3v1(self.__fileobj.read(128))
                    if frames is not None:
                        self.version = self._V11
                        map(self.add, frames.values())
                    else:
                        raise err, None, stack
            else:
                frames = self.__known_frames
                if frames is None:
                    if self._V23 <= self.version:
                        frames = Frames
                    elif self._V22 <= self.version:
                        frames = Frames_2_2
                data = self.__fullread(self.size - 10)
                for frame in self.__read_frames(data, frames=frames):
                    if isinstance(frame, Frame):
                        self.add(frame)
                    else:
                        self.unknown_frames.append(frame)
                self.__unknown_version = self.version
        finally:
            self.__fileobj.close()
            del self.__fileobj
            del self.__filesize
            if translate:
                if v2_version == 3:
                    self.update_to_v23()
                else:
                    self.update_to_v24()

    def getall(self, key):
        """Return all frames with a given name (the list may be empty).

        This is best explained by examples::

            id3.getall('TIT2') == [id3['TIT2']]
            id3.getall('TTTT') == []
            id3.getall('TXXX') == [TXXX(desc='woo', text='bar'),
                                   TXXX(desc='baz', text='quuuux'), ...]

        Since this is based on the frame's HashKey, which is
        colon-separated, you can use it to do things like
        ``getall('COMM:MusicMatch')`` or ``getall('TXXX:QuodLibet:')``.
        """
        if key in self:
            return [self[key]]
        else:
            key = key + ":"
            return [v for s, v in self.items() if s.startswith(key)]

    def delall(self, key):
        """Delete all tags of a given kind; see getall."""
        if key in self:
            del(self[key])
        else:
            key = key + ":"
            for k in filter(lambda s: s.startswith(key), self.keys()):
                del(self[k])

    def setall(self, key, values):
        """Delete frames of the given type and add frames in 'values'."""
        self.delall(key)
        for tag in values:
            self[tag.HashKey] = tag

    def pprint(self):
        """Return tags in a human-readable format.

        "Human-readable" is used loosely here. The format is intended
        to mirror that used for Vorbis or APEv2 output, e.g.

            ``TIT2=My Title``

        However, ID3 frames can have multiple keys:

            ``POPM=user@example.org=3 128/255``
        """
        frames = list(map(Frame.pprint, self.values()))
        frames.sort()
        return "\n".join(frames)

    def loaded_frame(self, tag):
        """Deprecated; use the add method."""
        # turn 2.2 into 2.3/2.4 tags
        if len(type(tag).__name__) == 3:
            tag = type(tag).__base__(tag)
        self[tag.HashKey] = tag

    # add = loaded_frame (and vice versa) break applications that
    # expect to be able to override loaded_frame (e.g. Quod Libet),
    # as does making loaded_frame call add.
    def add(self, frame):
        """Add a frame to the tag."""
        return self.loaded_frame(frame)

    def __load_header(self):
        fn = self.filename
        data = self.__fullread(10)
        id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', data)
        self.__flags = flags
        self.size = BitPaddedInt(size) + 10
        self.version = (2, vmaj, vrev)

        if id3 != 'ID3':
            raise ID3NoHeaderError("'%s' doesn't start with an ID3 tag" % fn)
        if vmaj not in [2, 3, 4]:
            raise ID3UnsupportedVersionError("'%s' ID3v2.%d not supported"
                                             % (fn, vmaj))

        if self.PEDANTIC:
            if not BitPaddedInt.has_valid_padding(size):
                raise ValueError("Header size not synchsafe")

            if self._V24 <= self.version and (flags & 0x0f):
                raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))
            elif self._V23 <= self.version < self._V24 and (flags & 0x1f):
                raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))

        if self.f_extended:
            extsize = self.__fullread(4)
            if extsize in Frames:
                # Some tagger sets the extended header flag but
                # doesn't write an extended header; in this case, the
                # ID3 data follows immediately. Since no extended
                # header is going to be long enough to actually match
                # a frame, and if it's *not* a frame we're going to be
                # completely lost anyway, this seems to be the most
                # correct check.
                # http://code.google.com/p/quodlibet/issues/detail?id=126
                self.__flags ^= 0x40
                self.__extsize = 0
                self.__fileobj.seek(-4, 1)
                self.__readbytes -= 4
            elif self.version >= self._V24:
                # "Where the 'Extended header size' is the size of the whole
                # extended header, stored as a 32 bit synchsafe integer."
                self.__extsize = BitPaddedInt(extsize) - 4
                if self.PEDANTIC:
                    if not BitPaddedInt.has_valid_padding(extsize):
                        raise ValueError("Extended header size not synchsafe")
            else:
                # "Where the 'Extended header size', currently 6 or 10 bytes,
                # excludes itself."
                self.__extsize = unpack('>L', extsize)[0]
            if self.__extsize:
                self.__extdata = self.__fullread(self.__extsize)
            else:
                self.__extdata = ""

    def __determine_bpi(self, data, frames, EMPTY="\x00" * 10):
        if self.version < self._V24:
            return int
        # have to special case whether to use bitpaddedints here
        # spec says to use them, but iTunes has it wrong

        # count number of tags found as BitPaddedInt and how far past
        o = 0
        asbpi = 0
        while o < len(data) - 10:
            part = data[o:o + 10]
            if part == EMPTY:
                bpioff = -((len(data) - o) % 10)
                break
            name, size, flags = unpack('>4sLH', part)
            size = BitPaddedInt(size)
            o += 10 + size
            if name in frames:
                asbpi += 1
        else:
            bpioff = o - len(data)

        # count number of tags found as int and how far past
        o = 0
        asint = 0
        while o < len(data) - 10:
            part = data[o:o + 10]
            if part == EMPTY:
                intoff = -((len(data) - o) % 10)
                break
            name, size, flags = unpack('>4sLH', part)
            o += 10 + size
            if name in frames:
                asint += 1
        else:
            intoff = o - len(data)

        # if more tags as int, or equal and bpi is past and int is not
        if asint > asbpi or (asint == asbpi and (bpioff >= 1 and intoff <= 1)):
            return int
        return BitPaddedInt

    def __read_frames(self, data, frames):
        if self.version < self._V24 and self.f_unsynch:
            try:
                data = unsynch.decode(data)
            except ValueError:
                pass

        if self._V23 <= self.version:
            bpi = self.__determine_bpi(data, frames)
            while data:
                header = data[:10]
                try:
                    name, size, flags = unpack('>4sLH', header)
                except struct.error:
                    return  # not enough header
                if name.strip('\x00') == '':
                    return
                size = bpi(size)
                framedata = data[10:10+size]
                data = data[10+size:]
                if size == 0:
                    continue  # drop empty frames
                try:
                    tag = frames[name]
                except KeyError:
                    if is_valid_frame_id(name):
                        yield header + framedata
                else:
                    try:
                        yield self.__load_framedata(tag, flags, framedata)
                    except NotImplementedError:
                        yield header + framedata
                    except ID3JunkFrameError:
                        pass

        elif self._V22 <= self.version:
            while data:
                header = data[0:6]
                try:
                    name, size = unpack('>3s3s', header)
                except struct.error:
                    return  # not enough header
                size, = struct.unpack('>L', '\x00'+size)
                if name.strip('\x00') == '':
                    return
                framedata = data[6:6+size]
                data = data[6+size:]
                if size == 0:
                    continue  # drop empty frames
                try:
                    tag = frames[name]
                except KeyError:
                    if is_valid_frame_id(name):
                        yield header + framedata
                else:
                    try:
                        yield self.__load_framedata(tag, 0, framedata)
                    except NotImplementedError:
                        yield header + framedata
                    except ID3JunkFrameError:
                        pass

    def __load_framedata(self, tag, flags, framedata):
        return tag.fromData(self, flags, framedata)

    f_unsynch = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    #f_crc = property(lambda s: bool(s.__extflags & 0x8000))

    def save(self, filename=None, v1=1, v2_version=4, v23_sep='/'):
        """Save changes to a file.

        If no filename is given, the one most recently loaded is used.

        Keyword arguments:
        v1 -- if 0, ID3v1 tags will be removed
              if 1, ID3v1 tags will be updated but not added
              if 2, ID3v1 tags will be created and/or updated
        v2 -- version of ID3v2 tags (3 or 4).

        By default Mutagen saves ID3v2.4 tags. If you want to save ID3v2.3
        tags, you must call method update_to_v23 before saving the file.

        v23_sep -- the separator used to join multiple text values
                   if v2_version == 3. Defaults to '/' but if it's None
                   will be the ID3v2v2.4 null separator.

        The lack of a way to update only an ID3v1 tag is intentional.
        """

        if v2_version == 3:
            version = self._V23
        elif v2_version == 4:
            version = self._V24
        else:
            raise ValueError("Only 3 or 4 allowed for v2_version")

        # Sort frames by 'importance'
        order = ["TIT2", "TPE1", "TRCK", "TALB", "TPOS", "TDRC", "TCON"]
        order = dict(zip(order, range(len(order))))
        last = len(order)
        frames = self.items()
        frames.sort(lambda a, b: cmp(order.get(a[0][:4], last),
                                     order.get(b[0][:4], last)))

        framedata = [self.__save_frame(frame, version=version, v23_sep=v23_sep)
                     for (key, frame) in frames]

        # only write unknown frames if they were loaded from the version
        # we are saving with or upgraded to it
        if self.__unknown_version == version:
            framedata.extend([data for data in self.unknown_frames
                              if len(data) > 10])

        if not framedata:
            try:
                self.delete(filename)
            except EnvironmentError, err:
                from errno import ENOENT
                if err.errno != ENOENT:
                    raise
            return

        framedata = ''.join(framedata)
        framesize = len(framedata)

        if filename is None:
            filename = self.filename
        try:
            f = open(filename, 'rb+')
        except IOError, err:
            from errno import ENOENT
            if err.errno != ENOENT:
                raise
            f = open(filename, 'ab')  # create, then reopen
            f = open(filename, 'rb+')
        try:
            idata = f.read(10)
            try:
                id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
            except struct.error:
                id3, insize = '', 0
            insize = BitPaddedInt(insize)
            if id3 != 'ID3':
                insize = -10

            if insize >= framesize:
                outsize = insize
            else:
                outsize = (framesize + 1023) & ~0x3FF
            framedata += '\x00' * (outsize - framesize)

            framesize = BitPaddedInt.to_str(outsize, width=4)
            flags = 0
            header = pack('>3sBBB4s', 'ID3', v2_version, 0, flags, framesize)
            data = header + framedata

            if (insize < outsize):
                insert_bytes(f, outsize-insize, insize+10)
            f.seek(0)
            f.write(data)

            try:
                f.seek(-128, 2)
            except IOError, err:
                # If the file is too small, that's OK - it just means
                # we're certain it doesn't have a v1 tag.
                from errno import EINVAL
                if err.errno != EINVAL:
                    # If we failed to see for some other reason, bail out.
                    raise
                # Since we're sure this isn't a v1 tag, don't read it.
                f.seek(0, 2)

            data = f.read(128)
            try:
                idx = data.index("TAG")
            except ValueError:
                offset = 0
                has_v1 = False
            else:
                offset = idx - len(data)
                has_v1 = True

            f.seek(offset, 2)
            if v1 == 1 and has_v1 or v1 == 2:
                f.write(MakeID3v1(self))
            else:
                f.truncate()

        finally:
            f.close()

    def delete(self, filename=None, delete_v1=True, delete_v2=True):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.

        Keyword arguments:

        * delete_v1 -- delete any ID3v1 tag
        * delete_v2 -- delete any ID3v2 tag
        """
        if filename is None:
            filename = self.filename
        delete(filename, delete_v1, delete_v2)
        self.clear()

    def __save_frame(self, frame, name=None, version=_V24, v23_sep=None):
        flags = 0
        if self.PEDANTIC and isinstance(frame, TextFrame):
            if len(str(frame)) == 0:
                return ''

        if version == self._V23:
            framev23 = frame._get_v23_frame(sep=v23_sep)
            framedata = framev23._writeData()
        else:
            framedata = frame._writeData()

        usize = len(framedata)
        if usize > 2048:
            # Disabled as this causes iTunes and other programs
            # to fail to find these frames, which usually includes
            # e.g. APIC.
            #framedata = BitPaddedInt.to_str(usize) + framedata.encode('zlib')
            #flags |= Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN
            pass

        if version == self._V24:
            bits = 7
        elif version == self._V23:
            bits = 8
        else:
            raise ValueError

        datasize = BitPaddedInt.to_str(len(framedata), width=4, bits=bits)
        header = pack('>4s4sH', name or type(frame).__name__, datasize, flags)
        return header + framedata

    def __update_common(self):
        """Updates done by both v23 and v24 update"""

        if "TCON" in self:
            # Get rid of "(xx)Foobr" format.
            self["TCON"].genres = self["TCON"].genres

        if self.version < self._V23:
            # ID3v2.2 PIC frames are slightly different.
            pics = self.getall("APIC")
            mimes = {"PNG": "image/png", "JPG": "image/jpeg"}
            self.delall("APIC")
            for pic in pics:
                newpic = APIC(
                    encoding=pic.encoding, mime=mimes.get(pic.mime, pic.mime),
                    type=pic.type, desc=pic.desc, data=pic.data)
                self.add(newpic)

            # ID3v2.2 LNK frames are just way too different to upgrade.
            self.delall("LINK")

    def update_to_v24(self):
        """Convert older tags into an ID3v2.4 tag.

        This updates old ID3v2 frames to ID3v2.4 ones (e.g. TYER to
        TDRC). If you intend to save tags, you must call this function
        at some point; it is called by default when loading the tag.
        """

        self.__update_common()

        if self.__unknown_version == (2, 3, 0):
            # convert unknown 2.3 frames (flags/size) to 2.4
            converted = []
            for frame in self.unknown_frames:
                try:
                    name, size, flags = unpack('>4sLH', frame[:10])
                    frame = BinaryFrame.fromData(self, flags, frame[10:])
                except (struct.error, error):
                    continue
                converted.append(self.__save_frame(frame, name=name))
            self.unknown_frames[:] = converted
            self.__unknown_version = (2, 4, 0)

        # TDAT, TYER, and TIME have been turned into TDRC.
        try:
            if str(self.get("TYER", "")).strip("\x00"):
                date = str(self.pop("TYER"))
                if str(self.get("TDAT", "")).strip("\x00"):
                    dat = str(self.pop("TDAT"))
                    date = "%s-%s-%s" % (date, dat[2:], dat[:2])
                    if str(self.get("TIME", "")).strip("\x00"):
                        time = str(self.pop("TIME"))
                        date += "T%s:%s:00" % (time[:2], time[2:])
                if "TDRC" not in self:
                    self.add(TDRC(encoding=0, text=date))
        except UnicodeDecodeError:
            # Old ID3 tags have *lots* of Unicode problems, so if TYER
            # is bad, just chuck the frames.
            pass

        # TORY can be the first part of a TDOR.
        if "TORY" in self:
            f = self.pop("TORY")
            if "TDOR" not in self:
                try:
                    self.add(TDOR(encoding=0, text=str(f)))
                except UnicodeDecodeError:
                    pass

        # IPLS is now TIPL.
        if "IPLS" in self:
            f = self.pop("IPLS")
            if "TIPL" not in self:
                self.add(TIPL(encoding=f.encoding, people=f.people))

        # These can't be trivially translated to any ID3v2.4 tags, or
        # should have been removed already.
        for key in ["RVAD", "EQUA", "TRDA", "TSIZ", "TDAT", "TIME", "CRM"]:
            if key in self:
                del(self[key])

    def update_to_v23(self):
        """Convert older (and newer) tags into an ID3v2.3 tag.

        This updates incompatible ID3v2 frames to ID3v2.3 ones. If you
        intend to save tags as ID3v2.3, you must call this function
        at some point.

        If you want to to go off spec and include some v2.4 frames
        in v2.3, remove them before calling this and add them back afterwards.
        """

        self.__update_common()

        # we could downgrade unknown v2.4 frames here, but given that
        # the main reason to save v2.3 is compatibility and this
        # might increase the chance of some parser breaking.. better not

        # TMCL, TIPL -> TIPL
        if "TIPL" in self or "TMCL" in self:
            people = []
            if "TIPL" in self:
                f = self.pop("TIPL")
                people.extend(f.people)
            if "TMCL" in self:
                f = self.pop("TMCL")
                people.extend(f.people)
            if "IPLS" not in self:
                self.add(IPLS(encoding=f.encoding, people=people))

        # TDOR -> TORY
        if "TDOR" in self:
            f = self.pop("TDOR")
            if f.text:
                d = f.text[0]
                if d.year and "TORY" not in self:
                    self.add(TORY(encoding=f.encoding, text="%04d" % d.year))

        # TDRC -> TYER, TDAT, TIME
        if "TDRC" in self:
            f = self.pop("TDRC")
            if f.text:
                d = f.text[0]
                if d.year and "TYER" not in self:
                    self.add(TYER(encoding=f.encoding, text="%04d" % d.year))
                if d.month and d.day and "TDAT" not in self:
                    self.add(TDAT(encoding=f.encoding,
                                  text="%02d%02d" % (d.day, d.month)))
                if d.hour and d.minute and "TIME" not in self:
                    self.add(TIME(encoding=f.encoding,
                                  text="%02d%02d" % (d.hour, d.minute)))

        # New frames added in v2.4
        v24_frames = [
            'ASPI', 'EQU2', 'RVA2', 'SEEK', 'SIGN', 'TDEN', 'TDOR',
            'TDRC', 'TDRL', 'TDTG', 'TIPL', 'TMCL', 'TMOO', 'TPRO',
            'TSOA', 'TSOP', 'TSOT', 'TSST',
        ]

        for key in v24_frames:
            if key in self:
                del(self[key])


def delete(filename, delete_v1=True, delete_v2=True):
    """Remove tags from a file.

    Keyword arguments:

    * delete_v1 -- delete any ID3v1 tag
    * delete_v2 -- delete any ID3v2 tag
    """

    f = open(filename, 'rb+')

    if delete_v1:
        try:
            f.seek(-128, 2)
        except IOError:
            pass
        else:
            if f.read(3) == "TAG":
                f.seek(-128, 2)
                f.truncate()

    # technically an insize=0 tag is invalid, but we delete it anyway
    # (primarily because we used to write it)
    if delete_v2:
        f.seek(0, 0)
        idata = f.read(10)
        try:
            id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
        except struct.error:
            id3, insize = '', -1
        insize = BitPaddedInt(insize)
        if id3 == 'ID3' and insize >= 0:
            delete_bytes(f, insize + 10, 0)


# support open(filename) as interface
Open = ID3


# ID3v1.1 support.
def ParseID3v1(string):
    """Parse an ID3v1 tag, returning a list of ID3v2.4 frames."""

    try:
        string = string[string.index("TAG"):]
    except ValueError:
        return None
    if 128 < len(string) or len(string) < 124:
        return None

    # Issue #69 - Previous versions of Mutagen, when encountering
    # out-of-spec TDRC and TYER frames of less than four characters,
    # wrote only the characters available - e.g. "1" or "" - into the
    # year field. To parse those, reduce the size of the year field.
    # Amazingly, "0s" works as a struct format string.
    unpack_fmt = "3s30s30s30s%ds29sBB" % (len(string) - 124)

    try:
        tag, title, artist, album, year, comment, track, genre = unpack(
            unpack_fmt, string)
    except StructError:
        return None

    if tag != "TAG":
        return None

    def fix(string):
        return string.split("\x00")[0].strip().decode('latin1')

    title, artist, album, year, comment = map(
        fix, [title, artist, album, year, comment])

    frames = {}
    if title:
        frames["TIT2"] = TIT2(encoding=0, text=title)
    if artist:
        frames["TPE1"] = TPE1(encoding=0, text=[artist])
    if album:
        frames["TALB"] = TALB(encoding=0, text=album)
    if year:
        frames["TDRC"] = TDRC(encoding=0, text=year)
    if comment:
        frames["COMM"] = COMM(
            encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)
    # Don't read a track number if it looks like the comment was
    # padded with spaces instead of nulls (thanks, WinAmp).
    if track and (track != 32 or string[-3] == '\x00'):
        frames["TRCK"] = TRCK(encoding=0, text=str(track))
    if genre != 255:
        frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames


def MakeID3v1(id3):
    """Return an ID3v1.1 tag string from a dict of ID3v2.4 frames."""

    v1 = {}

    for v2id, name in {"TIT2": "title", "TPE1": "artist",
                       "TALB": "album"}.items():
        if v2id in id3:
            text = id3[v2id].text[0].encode('latin1', 'replace')[:30]
        else:
            text = ""
        v1[name] = text + ("\x00" * (30 - len(text)))

    if "COMM" in id3:
        cmnt = id3["COMM"].text[0].encode('latin1', 'replace')[:28]
    else:
        cmnt = ""
    v1["comment"] = cmnt + ("\x00" * (29 - len(cmnt)))

    if "TRCK" in id3:
        try:
            v1["track"] = chr(+id3["TRCK"])
        except ValueError:
            v1["track"] = "\x00"
    else:
        v1["track"] = "\x00"

    if "TCON" in id3:
        try:
            genre = id3["TCON"].genres[0]
        except IndexError:
            pass
        else:
            if genre in TCON.GENRES:
                v1["genre"] = chr(TCON.GENRES.index(genre))
    if "genre" not in v1:
        v1["genre"] = "\xff"

    if "TDRC" in id3:
        year = str(id3["TDRC"])
    elif "TYER" in id3:
        year = str(id3["TYER"])
    else:
        year = ""
    v1["year"] = (year + "\x00\x00\x00\x00")[:4]

    return ("TAG%(title)s%(artist)s%(album)s%(year)s%(comment)s"
            "%(track)s%(genre)s") % v1


class ID3FileType(mutagen.FileType):
    """An unknown type of file with ID3 tags."""

    ID3 = ID3

    class _Info(object):
        length = 0

        def __init__(self, fileobj, offset):
            pass

        @staticmethod
        def pprint():
            return "Unknown format with ID3 tag"

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith("ID3")

    def add_tags(self, ID3=None):
        """Add an empty ID3 tag to the file.

        A custom tag reader may be used in instead of the default
        mutagen.id3.ID3 object, e.g. an EasyID3 reader.
        """
        if ID3 is None:
            ID3 = self.ID3
        if self.tags is None:
            self.ID3 = ID3
            self.tags = ID3()
        else:
            raise error("an ID3 tag already exists")

    def load(self, filename, ID3=None, **kwargs):
        """Load stream and tag information from a file.

        A custom tag reader may be used in instead of the default
        mutagen.id3.ID3 object, e.g. an EasyID3 reader.
        """

        if ID3 is None:
            ID3 = self.ID3
        else:
            # If this was initialized with EasyID3, remember that for
            # when tags are auto-instantiated in add_tags.
            self.ID3 = ID3
        self.filename = filename
        try:
            self.tags = ID3(filename, **kwargs)
        except error:
            self.tags = None
        if self.tags is not None:
            try:
                offset = self.tags.size
            except AttributeError:
                offset = None
        else:
            offset = None
        try:
            fileobj = open(filename, "rb")
            self.info = self._Info(fileobj, offset)
        finally:
            fileobj.close()
