# id3 support for mutagen
# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id: id3.py 4285 2008-09-06 08:01:31Z piman $

"""ID3v2 reading and writing.

This is based off of the following references:
   http://www.id3.org/id3v2.4.0-structure.txt
   http://www.id3.org/id3v2.4.0-frames.txt
   http://www.id3.org/id3v2.3.0.html
   http://www.id3.org/id3v2-00.txt
   http://www.id3.org/id3v1.html

Its largest deviation from the above (versions 2.3 and 2.2) is that it
will not interpret the / characters as a separator, and will almost
always accept null separators to generate multi-valued text frames.

Because ID3 frame structure differs between frame types, each frame is
implemented as a different class (e.g. TIT2 as mutagen.id3.TIT2). Each
frame's documentation contains a list of its attributes.

Since this file's documentation is a little unwieldy, you are probably
interested in the 'ID3' class to start with.
"""

__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']

import struct; from struct import unpack, pack
from zlib import error as zlibError
from warnings import warn

import lib.mutagen
from lib.mutagen._util import insert_bytes, delete_bytes, DictProxy

class error(Exception): pass
class ID3NoHeaderError(error, ValueError): pass
class ID3BadUnsynchData(error, ValueError): pass
class ID3BadCompressedData(error, ValueError): pass
class ID3TagError(error, ValueError): pass
class ID3UnsupportedVersionError(error, NotImplementedError): pass
class ID3EncryptionUnsupportedError(error, NotImplementedError): pass
class ID3JunkFrameError(error, ValueError): pass

class ID3Warning(error, UserWarning): pass

def is_valid_frame_id(frame_id):
    return frame_id.isalnum() and frame_id.isupper()

class ID3(DictProxy, lib.mutagen.Metadata):
    """A file with an ID3v2 tag.

    Attributes:
    version -- ID3 tag version as a tuple
    unknown_frames -- raw frame data of any unknown frames found
    size -- the total size of the ID3 tag, including the header
    """

    PEDANTIC = True
    version = (2, 4, 0)

    filename = None
    size = 0
    __flags = 0
    __readbytes = 0
    __crc = None

    def __init__(self, *args, **kwargs):
        self.unknown_frames = []
        super(ID3, self).__init__(*args, **kwargs)

    def __fullread(self, size):
        try:
            if size < 0:
                raise ValueError('Requested bytes (%s) less than zero' % size)
            if size > self.__filesize:
                raise EOFError('Requested %#x of %#x (%s)' % 
                        (long(size), long(self.__filesize), self.filename))
        except AttributeError: pass
        data = self.__fileobj.read(size)
        if len(data) != size: raise EOFError
        self.__readbytes += size
        return data

    def load(self, filename, known_frames=None, translate=True):
        """Load tags from a filename.

        Keyword arguments:
        filename -- filename to load tag data from
        known_frames -- dict mapping frame IDs to Frame objects
        translate -- Update all tags to ID3v2.4 internally. Mutagen is
                     only capable of writing ID3v2.4 tags, so if you
                     intend to save, this must be true.

        Example of loading a custom frame:
            my_frames = dict(mutagen.id3.Frames)
            class XMYF(Frame): ...
            my_frames["XMYF"] = XMYF
            mutagen.id3.ID3(filename, known_frames=my_frames)
        """

        from os.path import getsize
        self.filename = filename
        self.__known_frames = known_frames
        self.__fileobj = file(filename, 'rb')
        self.__filesize = getsize(filename)
        try:
            try:
                self.__load_header()
            except EOFError:
                self.size = 0
                raise ID3NoHeaderError("%s: too small (%d bytes)" %(
                    filename, self.__filesize))
            except (ID3NoHeaderError, ID3UnsupportedVersionError), err:
                self.size = 0
                import sys
                stack = sys.exc_info()[2]
                try: self.__fileobj.seek(-128, 2)
                except EnvironmentError: raise err, None, stack
                else:
                    frames = ParseID3v1(self.__fileobj.read(128))
                    if frames is not None:
                        self.version = (1, 1)
                        map(self.add, frames.values())
                    else: raise err, None, stack
            else:
                frames = self.__known_frames
                if frames is None:
                    if (2,3,0) <= self.version: frames = Frames
                    elif (2,2,0) <= self.version: frames = Frames_2_2
                data = self.__fullread(self.size - 10)
                for frame in self.__read_frames(data, frames=frames):
                    if isinstance(frame, Frame): self.add(frame)
                    else: self.unknown_frames.append(frame)
        finally:
            self.__fileobj.close()
            del self.__fileobj
            del self.__filesize
            if translate:
                self.update_to_v24()

    def getall(self, key):
        """Return all frames with a given name (the list may be empty).

        This is best explained by examples:
            id3.getall('TIT2') == [id3['TIT2']]
            id3.getall('TTTT') == []
            id3.getall('TXXX') == [TXXX(desc='woo', text='bar'),
                                   TXXX(desc='baz', text='quuuux'), ...]

        Since this is based on the frame's HashKey, which is
        colon-separated, you can use it to do things like
        getall('COMM:MusicMatch') or getall('TXXX:QuodLibet:').
        """
        if key in self: return [self[key]]
        else:
            key = key + ":"
            return [v for s,v in self.items() if s.startswith(key)]

    def delall(self, key):
        """Delete all tags of a given kind; see getall."""
        if key in self: del(self[key])
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
            TIT2=My Title
        However, ID3 frames can have multiple keys:
            POPM=user@example.org=3 128/255
        """
        return "\n".join(map(Frame.pprint, self.values()))

    def loaded_frame(self, tag):
        """Deprecated; use the add method."""
        # turn 2.2 into 2.3/2.4 tags
        if len(type(tag).__name__) == 3: tag = type(tag).__base__(tag)
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
            if (2,4,0) <= self.version and (flags & 0x0f):
                raise ValueError("'%s' has invalid flags %#02x" % (fn, flags))
            elif (2,3,0) <= self.version < (2,4,0) and (flags & 0x1f):
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
            elif self.version >= (2,4,0):
                # "Where the 'Extended header size' is the size of the whole
                # extended header, stored as a 32 bit synchsafe integer."
                self.__extsize = BitPaddedInt(extsize) - 4
            else:
                # "Where the 'Extended header size', currently 6 or 10 bytes,
                # excludes itself."
                self.__extsize = unpack('>L', extsize)[0]
            if self.__extsize:
                self.__extdata = self.__fullread(self.__extsize)
            else:
                self.__extdata = ""

    def __determine_bpi(self, data, frames, EMPTY="\x00" * 10):
        if self.version < (2, 4, 0):
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
        if self.version < (2,4,0) and self.f_unsynch:
            try: data = unsynch.decode(data)
            except ValueError: pass

        if (2,3,0) <= self.version:
            bpi = self.__determine_bpi(data, frames)
            while data:
                header = data[:10]
                try: name, size, flags = unpack('>4sLH', header)
                except struct.error: return # not enough header
                if name.strip('\x00') == '': return
                size = bpi(size)
                framedata = data[10:10+size]
                data = data[10+size:]
                if size == 0: continue # drop empty frames
                try: tag = frames[name]
                except KeyError: 
                    if is_valid_frame_id(name): yield header + framedata
                else:
                    try: yield self.__load_framedata(tag, flags, framedata)
                    except NotImplementedError: yield header + framedata
                    except ID3JunkFrameError: pass

        elif (2,2,0) <= self.version:
            while data:
                header = data[0:6]
                try: name, size = unpack('>3s3s', header)
                except struct.error: return # not enough header
                size, = struct.unpack('>L', '\x00'+size)
                if name.strip('\x00') == '': return
                framedata = data[6:6+size]
                data = data[6+size:]
                if size == 0: continue # drop empty frames
                try: tag = frames[name]
                except KeyError:
                    if is_valid_frame_id(name): yield header + framedata
                else:
                    try: yield self.__load_framedata(tag, 0, framedata)
                    except NotImplementedError: yield header + framedata
                    except ID3JunkFrameError: pass

    def __load_framedata(self, tag, flags, framedata):
        return tag.fromData(self, flags, framedata)
            
    f_unsynch = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    #f_crc = property(lambda s: bool(s.__extflags & 0x8000))

    def save(self, filename=None, v1=1):
        """Save changes to a file.

        If no filename is given, the one most recently loaded is used.

        Keyword arguments:
        v1 -- if 0, ID3v1 tags will be removed
              if 1, ID3v1 tags will be updated but not added
              if 2, ID3v1 tags will be created and/or updated

        The lack of a way to update only an ID3v1 tag is intentional.
        """

        # Sort frames by 'importance'
        order = ["TIT2", "TPE1", "TRCK", "TALB", "TPOS", "TDRC", "TCON"]
        order = dict(zip(order, range(len(order))))
        last = len(order)
        frames = self.items()
        frames.sort(lambda a, b: cmp(order.get(a[0][:4], last),
                                     order.get(b[0][:4], last)))

        framedata = [self.__save_frame(frame) for (key, frame) in frames]
        framedata.extend([data for data in self.unknown_frames
                if len(data) > 10])
        if not framedata:
            try:
                self.delete(filename)
            except EnvironmentError, err:
                from errno import ENOENT
                if err.errno != ENOENT: raise
            return

        framedata = ''.join(framedata)
        framesize = len(framedata)

        if filename is None: filename = self.filename
        try: f = open(filename, 'rb+')
        except IOError, err:
            from errno import ENOENT
            if err.errno != ENOENT: raise
            f = open(filename, 'ab') # create, then reopen
            f = open(filename, 'rb+')
        try:
            idata = f.read(10)
            try: id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
            except struct.error: id3, insize = '', 0
            insize = BitPaddedInt(insize)
            if id3 != 'ID3': insize = -10

            if insize >= framesize: outsize = insize
            else: outsize = (framesize + 1023) & ~0x3FF
            framedata += '\x00' * (outsize - framesize)

            framesize = BitPaddedInt.to_str(outsize, width=4)
            flags = 0
            header = pack('>3sBBB4s', 'ID3', 4, 0, flags, framesize)
            data = header + framedata

            if (insize < outsize):
                insert_bytes(f, outsize-insize, insize+10)
            f.seek(0)
            f.write(data)

            try:
                f.seek(-128, 2)
            except IOError, err:
                from errno import EINVAL
                if err.errno != EINVAL: raise
                f.seek(0, 2) # ensure read won't get "TAG"

            if f.read(3) == "TAG":
                f.seek(-128, 2)
                if v1 > 0: f.write(MakeID3v1(self))
                else: f.truncate()
            elif v1 == 2:
                f.seek(0, 2)
                f.write(MakeID3v1(self))

        finally:
            f.close()

    def delete(self, filename=None, delete_v1=True, delete_v2=True):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.

        Keyword arguments:
        delete_v1 -- delete any ID3v1 tag
        delete_v2 -- delete any ID3v2 tag
        """
        if filename is None:
            filename = self.filename
        delete(filename, delete_v1, delete_v2)
        self.clear()

    def __save_frame(self, frame):
        flags = 0
        if self.PEDANTIC and isinstance(frame, TextFrame):
            if len(str(frame)) == 0: return ''
        framedata = frame._writeData()
        usize = len(framedata)
        if usize > 2048:
            # Disabled as this causes iTunes and other programs
            # to fail to find these frames, which usually includes
            # e.g. APIC.
            #framedata = BitPaddedInt.to_str(usize) + framedata.encode('zlib')
            #flags |= Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN
            pass
        datasize = BitPaddedInt.to_str(len(framedata), width=4)
        header = pack('>4s4sH', type(frame).__name__, datasize, flags)
        return header + framedata

    def update_to_v24(self):
        """Convert older tags into an ID3v2.4 tag.

        This updates old ID3v2 frames to ID3v2.4 ones (e.g. TYER to
        TDRC). If you intend to save tags, you must call this function
        at some point; it is called by default when loading the tag.
        """

        if self.version < (2,3,0): del self.unknown_frames[:]
        # unsafe to write

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

        if "TCON" in self:
            # Get rid of "(xx)Foobr" format.
            self["TCON"].genres = self["TCON"].genres

        if self.version < (2, 3):
            # ID3v2.2 PIC frames are slightly different.
            pics = self.getall("APIC")
            mimes = { "PNG": "image/png", "JPG": "image/jpeg" }
            self.delall("APIC")
            for pic in pics:
                newpic = APIC(
                    encoding=pic.encoding, mime=mimes.get(pic.mime, pic.mime),
                    type=pic.type, desc=pic.desc, data=pic.data)
                self.add(newpic)

            # ID3v2.2 LNK frames are just way too different to upgrade.
            self.delall("LINK")

        # These can't be trivially translated to any ID3v2.4 tags, or
        # should have been removed already.
        for key in ["RVAD", "EQUA", "TRDA", "TSIZ", "TDAT", "TIME", "CRM"]:
            if key in self: del(self[key])

def delete(filename, delete_v1=True, delete_v2=True):
    """Remove tags from a file.

    Keyword arguments:
    delete_v1 -- delete any ID3v1 tag
    delete_v2 -- delete any ID3v2 tag
    """

    f = open(filename, 'rb+')

    if delete_v1:
        try:
            f.seek(-128, 2)
        except IOError: pass
        else:
            if f.read(3) == "TAG":
                f.seek(-128, 2)
                f.truncate()

    # technically an insize=0 tag is invalid, but we delete it anyway
    # (primarily because we used to write it)
    if delete_v2:
        f.seek(0, 0)
        idata = f.read(10)
        try: id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
        except struct.error: id3, insize = '', -1
        insize = BitPaddedInt(insize)
        if id3 == 'ID3' and insize >= 0:
            delete_bytes(f, insize + 10, 0)

class BitPaddedInt(int):
    def __new__(cls, value, bits=7, bigendian=True):
        "Strips 8-bits bits out of every byte"
        mask = (1<<(bits))-1
        if isinstance(value, (int, long)):
            bytes = []
            while value:
                bytes.append(value & ((1<<bits)-1))
                value = value >> 8
        if isinstance(value, str):
            bytes = [ord(byte) & mask for byte in value]
            if bigendian: bytes.reverse()
        numeric_value = 0
        for shift, byte in zip(range(0, len(bytes)*bits, bits), bytes):
            numeric_value += byte << shift
        if isinstance(numeric_value, long):
            self = long.__new__(BitPaddedLong, numeric_value)
        else:
            self = int.__new__(BitPaddedInt, numeric_value)
        self.bits = bits
        self.bigendian = bigendian
        return self

    def as_str(value, bits=7, bigendian=True, width=4):
        bits = getattr(value, 'bits', bits)
        bigendian = getattr(value, 'bigendian', bigendian)
        value = int(value)
        mask = (1<<bits)-1
        bytes = []
        while value:
            bytes.append(value & mask)
            value = value >> bits
        # PCNT and POPM use growing integers of at least 4 bytes as counters.
        if width == -1: width = max(4, len(bytes))
        if len(bytes) > width:
            raise ValueError, 'Value too wide (%d bytes)' % len(bytes)
        else: bytes.extend([0] * (width-len(bytes)))
        if bigendian: bytes.reverse()
        return ''.join(map(chr, bytes))
    to_str = staticmethod(as_str)

class BitPaddedLong(long):
    def as_str(value, bits=7, bigendian=True, width=4):
        return BitPaddedInt.to_str(value, bits, bigendian, width)
    to_str = staticmethod(as_str)

class unsynch(object):
    def decode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                safe = val != '\xFF'
            else:
                if val >= '\xE0': raise ValueError('invalid sync-safe string')
                elif val != '\x00': append(val)
                safe = True
        if not safe: raise ValueError('string ended unsafe')
        return ''.join(output)
    decode = staticmethod(decode)

    def encode(value):
        output = []
        safe = True
        append = output.append
        for val in value:
            if safe:
                append(val)
                if val == '\xFF': safe = False
            elif val == '\x00' or val >= '\xE0':
                append('\x00')
                append(val)
                safe = val != '\xFF'
            else:
                append(val)
                safe = True
        if not safe: append('\x00')
        return ''.join(output)
    encode = staticmethod(encode)

class Spec(object):
    def __init__(self, name): self.name = name
    def __hash__(self): raise TypeError("Spec objects are unhashable")

class ByteSpec(Spec):
    def read(self, frame, data): return ord(data[0]), data[1:]
    def write(self, frame, value): return chr(value)
    def validate(self, frame, value): return value

class IntegerSpec(Spec):
    def read(self, frame, data):
        return int(BitPaddedInt(data, bits=8)), ''
    def write(self, frame, value):
        return BitPaddedInt.to_str(value, bits=8, width=-1)
    def validate(self, frame, value):
        return value

class SizedIntegerSpec(Spec):
    def __init__(self, name, size):
        self.name, self.__sz = name, size
    def read(self, frame, data):
        return int(BitPaddedInt(data[:self.__sz], bits=8)), data[self.__sz:]
    def write(self, frame, value):
        return BitPaddedInt.to_str(value, bits=8, width=self.__sz)
    def validate(self, frame, value):
        return value

class EncodingSpec(ByteSpec):
    def read(self, frame, data):
        enc, data = super(EncodingSpec, self).read(frame, data)
        if enc < 16: return enc, data
        else: return 0, chr(enc)+data

    def validate(self, frame, value):
        if 0 <= value <= 3: return value
        if value is None: return None
        raise ValueError, 'Invalid Encoding: %r' % value

class StringSpec(Spec):
    def __init__(self, name, length):
        super(StringSpec, self).__init__(name)
        self.len = length
    def read(s, frame, data): return data[:s.len], data[s.len:]
    def write(s, frame, value):
        if value is None: return '\x00' * s.len
        else: return (str(value) + '\x00' * s.len)[:s.len]
    def validate(s, frame, value):
        if value is None: return None
        if isinstance(value, basestring) and len(value) == s.len: return value
        raise ValueError, 'Invalid StringSpec[%d] data: %r' % (s.len, value)

class BinaryDataSpec(Spec):
    def read(self, frame, data): return data, ''
    def write(self, frame, value): return str(value)
    def validate(self, frame, value): return str(value)

class EncodedTextSpec(Spec):
    # Okay, seriously. This is private and defined explicitly and
    # completely by the ID3 specification. You can't just add
    # encodings here however you want.
    _encodings = ( ('latin1', '\x00'), ('utf16', '\x00\x00'),
                   ('utf_16_be', '\x00\x00'), ('utf8', '\x00') )

    def read(self, frame, data):
        enc, term = self._encodings[frame.encoding]
        ret = ''
        if len(term) == 1:
            if term in data:
                data, ret = data.split(term, 1)
        else:
            offset = -1
            try:
                while True:
                    offset = data.index(term, offset+1)
                    if offset & 1: continue
                    data, ret = data[0:offset], data[offset+2:]; break
            except ValueError: pass

        if len(data) < len(term): return u'', ret
        return data.decode(enc), ret

    def write(self, frame, value):
        enc, term = self._encodings[frame.encoding]
        return value.encode(enc) + term

    def validate(self, frame, value): return unicode(value)

class MultiSpec(Spec):
    def __init__(self, name, *specs, **kw):
        super(MultiSpec, self).__init__(name)
        self.specs = specs
        self.sep = kw.get('sep')

    def read(self, frame, data):
        values = []
        while data:
            record = []
            for spec in self.specs:
                value, data = spec.read(frame, data)
                record.append(value)
            if len(self.specs) != 1: values.append(record)
            else: values.append(record[0])
        return values, data

    def write(self, frame, value):
        data = []
        if len(self.specs) == 1:
            for v in value:
                data.append(self.specs[0].write(frame, v))
        else:
            for record in value:
                for v, s in zip(record, self.specs):
                    data.append(s.write(frame, v))
        return ''.join(data)

    def validate(self, frame, value):
        if value is None: return []
        if self.sep and isinstance(value, basestring):
            value = value.split(self.sep)
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [ 
                    [s.validate(frame, v) for (v,s) in zip(val, self.specs)]
                    for val in value ]
        raise ValueError, 'Invalid MultiSpec data: %r' % value

class EncodedNumericTextSpec(EncodedTextSpec): pass
class EncodedNumericPartTextSpec(EncodedTextSpec): pass

class Latin1TextSpec(EncodedTextSpec):
    def read(self, frame, data):
        if '\x00' in data: data, ret = data.split('\x00',1)
        else: ret = ''
        return data.decode('latin1'), ret

    def write(self, data, value):
        return value.encode('latin1') + '\x00'

    def validate(self, frame, value): return unicode(value)

class ID3TimeStamp(object):
    """A time stamp in ID3v2 format.

    This is a restricted form of the ISO 8601 standard; time stamps
    take the form of:
        YYYY-MM-DD HH:MM:SS
    Or some partial form (YYYY-MM-DD HH, YYYY, etc.).

    The 'text' attribute contains the raw text data of the time stamp.
    """

    import re
    def __init__(self, text):
        if isinstance(text, ID3TimeStamp): text = text.text
        self.text = text

    __formats = ['%04d'] + ['%02d'] * 5
    __seps = ['-', '-', ' ', ':', ':', 'x']
    def get_text(self):
        parts = [self.year, self.month, self.day,
                self.hour, self.minute, self.second]
        pieces = []
        for i, part in enumerate(iter(iter(parts).next, None)):
            pieces.append(self.__formats[i]%part + self.__seps[i])
        return u''.join(pieces)[:-1]

    def set_text(self, text, splitre=re.compile('[-T:/.]|\s+')):
        year, month, day, hour, minute, second = \
                splitre.split(text + ':::::')[:6]
        for a in 'year month day hour minute second'.split():
            try: v = int(locals()[a])
            except ValueError: v = None
            setattr(self, a, v)

    text = property(get_text, set_text, doc="ID3v2.4 date and time.")

    def __str__(self): return self.text
    def __repr__(self): return repr(self.text)
    def __cmp__(self, other): return cmp(self.text, other.text)
    def encode(self, *args): return self.text.encode(*args)

class TimeStampSpec(EncodedTextSpec):
    def read(self, frame, data):
        value, data = super(TimeStampSpec, self).read(frame, data)
        return self.validate(frame, value), data

    def write(self, frame, data):
        return super(TimeStampSpec, self).write(frame,
                data.text.replace(' ', 'T'))

    def validate(self, frame, value):
        try: return ID3TimeStamp(value)
        except TypeError: raise ValueError, "Invalid ID3TimeStamp: %r" % value

class ChannelSpec(ByteSpec):
    (OTHER, MASTER, FRONTRIGHT, FRONTLEFT, BACKRIGHT, BACKLEFT, FRONTCENTRE,
     BACKCENTRE, SUBWOOFER) = range(9)

class VolumeAdjustmentSpec(Spec):
    def read(self, frame, data):
        value, = unpack('>h', data[0:2])
        return value/512.0, data[2:]

    def write(self, frame, value):
        return pack('>h', int(round(value * 512)))

    def validate(self, frame, value): return value

class VolumePeakSpec(Spec):
    def read(self, frame, data):
        # http://bugs.xmms.org/attachment.cgi?id=113&action=view
        peak = 0
        bits = ord(data[0])
        bytes = min(4, (bits + 7) >> 3)
        # not enough frame data
        if bytes + 1 > len(data): raise ID3JunkFrameError
        shift = ((8 - (bits & 7)) & 7) + (4 - bytes) * 8
        for i in range(1, bytes+1):
            peak *= 256
            peak += ord(data[i])
        peak *= 2**shift
        return (float(peak) / (2**31-1)), data[1+bytes:]

    def write(self, frame, value):
        # always write as 16 bits for sanity.
        return "\x10" + pack('>H', int(round(value * 32768)))

    def validate(self, frame, value): return value

class SynchronizedTextSpec(EncodedTextSpec):
    def read(self, frame, data):
        texts = []
        encoding, term = self._encodings[frame.encoding]
        while data:
            l = len(term)
            try:
                value_idx = data.index(term)
            except ValueError:
                raise ID3JunkFrameError
            value = data[:value_idx].decode(encoding)
            time, = struct.unpack(">I", data[value_idx+l:value_idx+l+4])
            texts.append((value, time))
            data = data[value_idx+l+4:]
        return texts, ""

    def write(self, frame, value):
        data = []
        encoding, term = self._encodings[frame.encoding]
        for text, time in frame.text:
            text = text.encode(encoding) + term
            data.append(text + struct.pack(">I", time))
        return "".join(data)

    def validate(self, frame, value):
        return value

class KeyEventSpec(Spec):
    def read(self, frame, data):
        events = []
        while len(data) >= 5:
            events.append(struct.unpack(">bI", data[:5]))
            data = data[5:]
        return events, data

    def write(self, frame, value):
        return "".join([struct.pack(">bI", *event) for event in value])

    def validate(self, frame, value):
        return value

class VolumeAdjustmentsSpec(Spec):
    # Not to be confused with VolumeAdjustmentSpec.
    def read(self, frame, data):
        adjustments = {}
        while len(data) >= 4:
            freq, adj = struct.unpack(">Hh", data[:4])
            data = data[4:]
            freq /= 2.0
            adj /= 512.0
            adjustments[freq] = adj
        adjustments = adjustments.items()
        adjustments.sort()
        return adjustments, data

    def write(self, frame, value):
        value.sort()
        return "".join([struct.pack(">Hh", int(freq * 2), int(adj * 512))
                        for (freq, adj) in value])

    def validate(self, frame, value):
        return value

class ASPIIndexSpec(Spec):
    def read(self, frame, data):
        if frame.b == 16:
            format = "H"
            size = 2
        elif frame.b == 8:
            format = "B"
            size = 1
        else:
            warn("invalid bit count in ASPI (%d)" % frame.b, ID3Warning)
            return [], data
        
        indexes = data[:frame.N * size]
        data = data[frame.N * size:]
        return list(struct.unpack(">" + format * frame.N, indexes)), data

    def write(self, frame, values):
        if frame.b == 16: format = "H"
        elif frame.b == 8: format = "B"
        else: raise ValueError("frame.b must be 8 or 16")
        return struct.pack(">" + format * frame.N, *values)

    def validate(self, frame, values):
        return values

class Frame(object):
    """Fundamental unit of ID3 data.

    ID3 tags are split into frames. Each frame has a potentially
    different structure, and so this base class is not very featureful.
    """

    FLAG23_ALTERTAG     = 0x8000
    FLAG23_ALTERFILE    = 0x4000
    FLAG23_READONLY     = 0x2000
    FLAG23_COMPRESS     = 0x0080
    FLAG23_ENCRYPT      = 0x0040
    FLAG23_GROUP        = 0x0020

    FLAG24_ALTERTAG     = 0x4000
    FLAG24_ALTERFILE    = 0x2000
    FLAG24_READONLY     = 0x1000
    FLAG24_GROUPID      = 0x0040
    FLAG24_COMPRESS     = 0x0008
    FLAG24_ENCRYPT      = 0x0004
    FLAG24_UNSYNCH      = 0x0002
    FLAG24_DATALEN      = 0x0001

    _framespec = []
    def __init__(self, *args, **kwargs):
        if len(args)==1 and len(kwargs)==0 and isinstance(args[0], type(self)):
            other = args[0]
            for checker in self._framespec:
                val = checker.validate(self, getattr(other, checker.name))
                setattr(self, checker.name, val)
        else:
            for checker, val in zip(self._framespec, args):
                setattr(self, checker.name, checker.validate(self, val))
            for checker in self._framespec[len(args):]:
                validated = checker.validate(
                    self, kwargs.get(checker.name, None))
                setattr(self, checker.name, validated)

    HashKey = property(
        lambda s: s.FrameID,
        doc="an internal key used to ensure frame uniqueness in a tag")
    FrameID = property(
        lambda s: type(s).__name__,
        doc="ID3v2 three or four character frame ID")

    def __repr__(self):
        """Python representation of a frame.

        The string returned is a valid Python expression to construct
        a copy of this frame.
        """
        kw = []
        for attr in self._framespec:
            kw.append('%s=%r' % (attr.name, getattr(self, attr.name)))
        return '%s(%s)' % (type(self).__name__, ', '.join(kw))

    def _readData(self, data):
        odata = data
        for reader in self._framespec:
            if len(data):
                try: value, data = reader.read(self, data)
                except UnicodeDecodeError:
                    raise ID3JunkFrameError
            else: raise ID3JunkFrameError
            setattr(self, reader.name, value)
        if data.strip('\x00'):
            warn('Leftover data: %s: %r (from %r)' % (
                    type(self).__name__, data, odata),
                    ID3Warning)

    def _writeData(self):
        data = []
        for writer in self._framespec:
            data.append(writer.write(self, getattr(self, writer.name)))
        return ''.join(data)

    def pprint(self):
        """Return a human-readable representation of the frame."""
        return "%s=%s" % (type(self).__name__, self._pprint())

    def _pprint(self):
        return "[unrepresentable data]"

    def fromData(cls, id3, tflags, data):
        """Construct this ID3 frame from raw string data."""

        if (2,4,0) <= id3.version:
            if tflags & (Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN):
                # The data length int is syncsafe in 2.4 (but not 2.3).
                # However, we don't actually need the data length int,
                # except to work around a QL 0.12 bug, and in that case
                # all we need are the raw bytes.
                datalen_bytes = data[:4]
                data = data[4:]
            if tflags & Frame.FLAG24_UNSYNCH or id3.f_unsynch:
                try: data = unsynch.decode(data)
                except ValueError, err:
                    if id3.PEDANTIC:
                        raise ID3BadUnsynchData, '%s: %r' % (err, data)
            if tflags & Frame.FLAG24_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG24_COMPRESS:
                try: data = data.decode('zlib')
                except zlibError, err:
                    # the initial mutagen that went out with QL 0.12 did not
                    # write the 4 bytes of uncompressed size. Compensate.
                    data = datalen_bytes + data
                    try: data = data.decode('zlib')
                    except zlibError, err:
                        if id3.PEDANTIC:
                            raise ID3BadCompressedData, '%s: %r' % (err, data)

        elif (2,3,0) <= id3.version:
            if tflags & Frame.FLAG23_COMPRESS:
                usize, = unpack('>L', data[:4])
                data = data[4:]
            if tflags & Frame.FLAG23_ENCRYPT:
                raise ID3EncryptionUnsupportedError
            if tflags & Frame.FLAG23_COMPRESS:
                try: data = data.decode('zlib')
                except zlibError, err:
                    if id3.PEDANTIC:
                        raise ID3BadCompressedData, '%s: %r' % (err, data)

        frame = cls()
        frame._rawdata = data
        frame._flags = tflags
        frame._readData(data)
        return frame
    fromData = classmethod(fromData)

    def __hash__(self):
        raise TypeError("Frame objects are unhashable")

class FrameOpt(Frame):
    """A frame with optional parts.

    Some ID3 frames have optional data; this class extends Frame to
    provide support for those parts.
    """
    _optionalspec = []

    def __init__(self, *args, **kwargs):
        super(FrameOpt, self).__init__(*args, **kwargs)
        for spec in self._optionalspec:
            if spec.name in kwargs:
                validated = spec.validate(self, kwargs[spec.name])
                setattr(self, spec.name, validated)
            else: break

    def _readData(self, data):
        odata = data
        for reader in self._framespec:
            if len(data): value, data = reader.read(self, data)
            else: raise ID3JunkFrameError
            setattr(self, reader.name, value)
        if data:
            for reader in self._optionalspec:
                if len(data): value, data = reader.read(self, data)
                else: break
                setattr(self, reader.name, value)
        if data.strip('\x00'):
            warn('Leftover data: %s: %r (from %r)' % (
                    type(self).__name__, data, odata),
                    ID3Warning)

    def _writeData(self):
        data = []
        for writer in self._framespec:
            data.append(writer.write(self, getattr(self, writer.name)))
        for writer in self._optionalspec:
            try: data.append(writer.write(self, getattr(self, writer.name)))
            except AttributeError: break
        return ''.join(data)

    def __repr__(self):
        kw = []
        for attr in self._framespec:
            kw.append('%s=%r' % (attr.name, getattr(self, attr.name)))
        for attr in self._optionalspec:
            if hasattr(self, attr.name):
                kw.append('%s=%r' % (attr.name, getattr(self, attr.name)))
        return '%s(%s)' % (type(self).__name__, ', '.join(kw))


class TextFrame(Frame):
    """Text strings.

    Text frames support casts to unicode or str objects, as well as
    list-like indexing, extend, and append.

    Iterating over a TextFrame iterates over its strings, not its
    characters.

    Text frames have a 'text' attribute which is the list of strings,
    and an 'encoding' attribute; 0 for ISO-8859 1, 1 UTF-16, 2 for
    UTF-16BE, and 3 for UTF-8. If you don't want to worry about
    encodings, just set it to 3.
    """

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return u'\u0000'.join(self.text)
    def __eq__(self, other):
        if isinstance(other, str): return str(self) == other
        elif isinstance(other, unicode): return unicode(self) == other
        return self.text == other
    def __getitem__(self, item): return self.text[item]
    def __iter__(self): return iter(self.text)
    def append(self, value): return self.text.append(value)
    def extend(self, value): return self.text.extend(value)
    def _pprint(self): return " / ".join(self.text)

class NumericTextFrame(TextFrame):
    """Numerical text strings.

    The numeric value of these frames can be gotten with unary plus, e.g.
        frame = TLEN('12345')
        length = +frame
    """

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedNumericTextSpec('text'), sep=u'\u0000') ]

    def __pos__(self):
        """Return the numerical value of the string."""
        return int(self.text[0])

class NumericPartTextFrame(TextFrame):
    """Multivalue numerical text strings.

    These strings indicate 'part (e.g. track) X of Y', and unary plus
    returns the first value:
        frame = TRCK('4/15')
        track = +frame # track == 4
    """

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', EncodedNumericPartTextSpec('text'), sep=u'\u0000') ]
    def __pos__(self):
        return int(self.text[0].split("/")[0])

class TimeStampTextFrame(TextFrame):
    """A list of time stamps.

    The 'text' attribute in this frame is a list of ID3TimeStamp
    objects, not a list of strings.
    """

    _framespec = [ EncodingSpec('encoding'),
        MultiSpec('text', TimeStampSpec('stamp'), sep=u',') ]
    def __str__(self): return self.__unicode__().encode('utf-8')
    def __unicode__(self): return ','.join([stamp.text for stamp in self.text])
    def _pprint(self):
        return " / ".join([stamp.text for stamp in self.text])

class UrlFrame(Frame):
    """A frame containing a URL string.

    The ID3 specification is silent about IRIs and normalized URL
    forms. Mutagen assumes all URLs in files are encoded as Latin 1,
    but string conversion of this frame returns a UTF-8 representation
    for compatibility with other string conversions.

    The only sane way to handle URLs in MP3s is to restrict them to
    ASCII.
    """

    _framespec = [ Latin1TextSpec('url') ]
    def __str__(self): return self.url.encode('utf-8')
    def __unicode__(self): return self.url
    def __eq__(self, other): return self.url == other
    def _pprint(self): return self.url

class UrlFrameU(UrlFrame):
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.url))

class TALB(TextFrame): "Album"
class TBPM(NumericTextFrame): "Beats per minute"
class TCOM(TextFrame): "Composer"

class TCON(TextFrame):
    """Content type (Genre)

    ID3 has several ways genres can be represented; for convenience,
    use the 'genres' property rather than the 'text' attribute.
    """

    from lib.mutagen._constants import GENRES

    def __get_genres(self):
        genres = []
        import re
        genre_re = re.compile(r"((?:\((?P<id>[0-9]+|RX|CR)\))*)(?P<str>.+)?")
        for value in self.text:
            if value.isdigit():
                try: genres.append(self.GENRES[int(value)])
                except IndexError: genres.append(u"Unknown")
            elif value == "CR": genres.append(u"Cover")
            elif value == "RX": genres.append(u"Remix")
            elif value:
                newgenres = []
                genreid, dummy, genrename = genre_re.match(value).groups()

                if genreid:
                    for gid in genreid[1:-1].split(")("):
                        if gid.isdigit() and int(gid) < len(self.GENRES):
                            gid = unicode(self.GENRES[int(gid)])
                            newgenres.append(gid)
                        elif gid == "CR": newgenres.append(u"Cover")
                        elif gid == "RX": newgenres.append(u"Remix")
                        else: newgenres.append(u"Unknown")

                if genrename:
                    # "Unescaping" the first parenthesis
                    if genrename.startswith("(("): genrename = genrename[1:]
                    if genrename not in newgenres: newgenres.append(genrename)

                genres.extend(newgenres)

        return genres

    def __set_genres(self, genres):
        if isinstance(genres, basestring): genres = [genres]
        self.text = map(self.__decode, genres)

    def __decode(self, value):
        if isinstance(value, str):
            enc = EncodedTextSpec._encodings[self.encoding][0]
            return value.decode(enc)
        else: return value

    genres = property(__get_genres, __set_genres, None,
                      "A list of genres parsed from the raw text data.")

    def _pprint(self):
        return " / ".join(self.genres)

class TCOP(TextFrame): "Copyright (c)"
class TCMP(NumericTextFrame): "iTunes Compilation Flag"
class TDAT(TextFrame): "Date of recording (DDMM)"
class TDEN(TimeStampTextFrame): "Encoding Time"
class TDOR(TimeStampTextFrame): "Original Release Time"
class TDLY(NumericTextFrame): "Audio Delay (ms)"
class TDRC(TimeStampTextFrame): "Recording Time"
class TDRL(TimeStampTextFrame): "Release Time"
class TDTG(TimeStampTextFrame): "Tagging Time"
class TENC(TextFrame): "Encoder"
class TEXT(TextFrame): "Lyricist"
class TFLT(TextFrame): "File type"
class TIME(TextFrame): "Time of recording (HHMM)"
class TIT1(TextFrame): "Content group description"
class TIT2(TextFrame): "Title"
class TIT3(TextFrame): "Subtitle/Description refinement"
class TKEY(TextFrame): "Starting Key"
class TLAN(TextFrame): "Audio Languages"
class TLEN(NumericTextFrame): "Audio Length (ms)"
class TMED(TextFrame): "Source Media Type"
class TMOO(TextFrame): "Mood"
class TOAL(TextFrame): "Original Album"
class TOFN(TextFrame): "Original Filename"
class TOLY(TextFrame): "Original Lyricist"
class TOPE(TextFrame): "Original Artist/Performer"
class TORY(NumericTextFrame): "Original Release Year"
class TOWN(TextFrame): "Owner/Licensee"
class TPE1(TextFrame): "Lead Artist/Performer/Soloist/Group"
class TPE2(TextFrame): "Band/Orchestra/Accompaniment"
class TPE3(TextFrame): "Conductor"
class TPE4(TextFrame): "Interpreter/Remixer/Modifier"
class TPOS(NumericPartTextFrame): "Part of set"
class TPRO(TextFrame): "Produced (P)"
class TPUB(TextFrame): "Publisher"
class TRCK(NumericPartTextFrame): "Track Number"
class TRDA(TextFrame): "Recording Dates"
class TRSN(TextFrame): "Internet Radio Station Name"
class TRSO(TextFrame): "Internet Radio Station Owner"
class TSIZ(NumericTextFrame): "Size of audio data (bytes)"
class TSO2(TextFrame): "iTunes Album Artist Sort"
class TSOA(TextFrame): "Album Sort Order key"
class TSOC(TextFrame): "iTunes Composer Sort"
class TSOP(TextFrame): "Perfomer Sort Order key"
class TSOT(TextFrame): "Title Sort Order key"
class TSRC(TextFrame): "International Standard Recording Code (ISRC)"
class TSSE(TextFrame): "Encoder settings"
class TSST(TextFrame): "Set Subtitle"
class TYER(NumericTextFrame): "Year of recording"

class TXXX(TextFrame):
    """User-defined text data.

    TXXX frames have a 'desc' attribute which is set to any Unicode
    value (though the encoding of the text and the description must be
    the same). Many taggers use this frame to store freeform keys.
    """
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))
    def _pprint(self): return "%s=%s" % (self.desc, " / ".join(self.text))

class WCOM(UrlFrameU): "Commercial Information"
class WCOP(UrlFrame): "Copyright Information"
class WOAF(UrlFrame): "Official File Information"
class WOAR(UrlFrameU): "Official Artist/Performer Information"
class WOAS(UrlFrame): "Official Source Information"
class WORS(UrlFrame): "Official Internet Radio Information"
class WPAY(UrlFrame): "Payment Information"
class WPUB(UrlFrame): "Official Publisher Information"

class WXXX(UrlFrame):
    """User-defined URL data.

    Like TXXX, this has a freeform description associated with it.
    """
    _framespec = [ EncodingSpec('encoding'), EncodedTextSpec('desc'),
        Latin1TextSpec('url') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))

class PairedTextFrame(Frame):
    """Paired text strings.

    Some ID3 frames pair text strings, to associate names with a more
    specific involvement in the song. The 'people' attribute of these
    frames contains a list of pairs:
        [['trumpet', 'Miles Davis'], ['bass', 'Paul Chambers']]

    Like text frames, these frames also have an encoding attribute.
    """

    _framespec = [ EncodingSpec('encoding'), MultiSpec('people',
        EncodedTextSpec('involvement'), EncodedTextSpec('person')) ]
    def __eq__(self, other):
        return self.people == other

class TIPL(PairedTextFrame): "Involved People List"
class TMCL(PairedTextFrame): "Musicians Credits List"
class IPLS(TIPL): "Involved People List"

class MCDI(Frame):
    """Binary dump of CD's TOC.

    The 'data' attribute contains the raw byte string.
    """
    _framespec = [ BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

class ETCO(Frame):
    """Event timing codes."""
    _framespec = [ ByteSpec("format"), KeyEventSpec("events") ]
    def __eq__(self, other): return self.events == other

class MLLT(Frame):
    """MPEG location lookup table.

    This frame's attributes may be changed in the future based on
    feedback from real-world use.
    """
    _framespec = [ SizedIntegerSpec('frames', 2),
                   SizedIntegerSpec('bytes', 3),
                   SizedIntegerSpec('milliseconds', 3),
                   ByteSpec('bits_for_bytes'),
                   ByteSpec('bits_for_milliseconds'),
                   BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

class SYTC(Frame):
    """Synchronised tempo codes.

    This frame's attributes may be changed in the future based on
    feedback from real-world use.
    """
    _framespec = [ ByteSpec("format"), BinaryDataSpec("data") ]
    def __eq__(self, other): return self.data == other

class USLT(Frame):
    """Unsynchronised lyrics/text transcription.

    Lyrics have a three letter ISO language code ('lang'), a
    description ('desc'), and a block of plain text ('text').
    """

    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('desc'), EncodedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%s:%r' % (s.FrameID, s.desc, s.lang))

    def __str__(self): return self.text.encode('utf-8')
    def __unicode__(self): return self.text
    def __eq__(self, other): return self.text == other
    
class SYLT(Frame):
    """Synchronised lyrics/text."""

    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        ByteSpec('format'), ByteSpec('type'), EncodedTextSpec('desc'),
        SynchronizedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%s:%r' % (s.FrameID, s.desc, s.lang))

    def __eq__(self, other):
        return str(self) == other

    def __str__(self):
        return "".join([text for (text, time) in self.text]).encode('utf-8')

class COMM(TextFrame):
    """User comment.

    User comment frames have a descrption, like TXXX, and also a three
    letter ISO language code in the 'lang' attribute.
    """
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('desc'),
        MultiSpec('text', EncodedTextSpec('text'), sep=u'\u0000') ]
    HashKey = property(lambda s: '%s:%s:%r' % (s.FrameID, s.desc, s.lang))
    def _pprint(self): return "%s=%r=%s" % (
        self.desc, self.lang, " / ".join(self.text))

class RVA2(Frame):
    """Relative volume adjustment (2).

    This frame is used to implemented volume scaling, and in
    particular, normalization using ReplayGain.

    Attributes:
    desc -- description or context of this adjustment
    channel -- audio channel to adjust (master is 1)
    gain -- a + or - dB gain relative to some reference level
    peak -- peak of the audio as a floating point number, [0, 1]

    When storing ReplayGain tags, use descriptions of 'album' and
    'track' on channel 1.
    """

    _framespec = [ Latin1TextSpec('desc'), ChannelSpec('channel'),
        VolumeAdjustmentSpec('gain'), VolumePeakSpec('peak') ]
    _channels = ["Other", "Master volume", "Front right", "Front left",
                 "Back right", "Back left", "Front centre", "Back centre",
                 "Subwoofer"]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))

    def __eq__(self, other):
        return ((str(self) == other) or
                (self.desc == other.desc and
                 self.channel == other.channel and
                 self.gain == other.gain and
                 self.peak == other.peak))

    def __str__(self):
        return "%s: %+0.4f dB/%0.4f" % (
            self._channels[self.channel], self.gain, self.peak)

class EQU2(Frame):
    """Equalisation (2).

    Attributes:
    method -- interpolation method (0 = band, 1 = linear)
    desc -- identifying description
    adjustments -- list of (frequency, vol_adjustment) pairs
    """
    _framespec = [ ByteSpec("method"), Latin1TextSpec("desc"),
                   VolumeAdjustmentsSpec("adjustments") ]
    def __eq__(self, other): return self.adjustments == other
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))

# class RVAD: unsupported
# class EQUA: unsupported

class RVRB(Frame):
    """Reverb."""
    _framespec = [ SizedIntegerSpec('left', 2), SizedIntegerSpec('right', 2),
                   ByteSpec('bounce_left'), ByteSpec('bounce_right'),
                   ByteSpec('feedback_ltl'), ByteSpec('feedback_ltr'),
                   ByteSpec('feedback_rtr'), ByteSpec('feedback_rtl'),
                   ByteSpec('premix_ltr'), ByteSpec('premix_rtl') ]

    def __eq__(self, other): return (self.left, self.right) == other

class APIC(Frame):
    """Attached (or linked) Picture.

    Attributes:
    encoding -- text encoding for the description
    mime -- a MIME type (e.g. image/jpeg) or '-->' if the data is a URI
    type -- the source of the image (3 is the album front cover)
    desc -- a text description of the image
    data -- raw image data, as a byte string

    Mutagen will automatically compress large images when saving tags.
    """
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('mime'),
        ByteSpec('type'), EncodedTextSpec('desc'), BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))
    def _pprint(self):
        return "%s (%s, %d bytes)" % (
            self.desc, self.mime, len(self.data))

class PCNT(Frame):
    """Play counter.

    The 'count' attribute contains the (recorded) number of times this
    file has been played.

    This frame is basically obsoleted by POPM.
    """
    _framespec = [ IntegerSpec('count') ]

    def __eq__(self, other): return self.count == other
    def __pos__(self): return self.count
    def _pprint(self): return unicode(self.count)

class POPM(FrameOpt):
    """Popularimeter.

    This frame keys a rating (out of 255) and a play count to an email
    address.

    Attributes:
    email -- email this POPM frame is for
    rating -- rating from 0 to 255
    count -- number of times the files has been played (optional)
    """
    _framespec = [ Latin1TextSpec('email'), ByteSpec('rating') ]
    _optionalspec = [ IntegerSpec('count') ]
                   
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.email))

    def __eq__(self, other): return self.rating == other
    def __pos__(self): return self.rating
    def _pprint(self): return "%s=%r %r/255" % (
        self.email, getattr(self, 'count', None), self.rating)

class GEOB(Frame):
    """General Encapsulated Object.

    A blob of binary data, that is not a picture (those go in APIC).

    Attributes:
    encoding -- encoding of the description
    mime -- MIME type of the data or '-->' if the data is a URI
    filename -- suggested filename if extracted
    desc -- text description of the data
    data -- raw data, as a byte string
    """
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('mime'),
        EncodedTextSpec('filename'), EncodedTextSpec('desc'), 
        BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.desc))

    def __eq__(self, other): return self.data == other

class RBUF(FrameOpt):
    """Recommended buffer size.

    Attributes:
    size -- recommended buffer size in bytes
    info -- if ID3 tags may be elsewhere in the file (optional)
    offset -- the location of the next ID3 tag, if any

    Mutagen will not find the next tag itself.
    """
    _framespec = [ SizedIntegerSpec('size', 3) ]
    _optionalspec = [ ByteSpec('info'), SizedIntegerSpec('offset', 4) ]

    def __eq__(self, other): return self.size == other
    def __pos__(self): return self.size

class AENC(FrameOpt):
    """Audio encryption.

    Attributes:
    owner -- key identifying this encryption type
    preview_start -- unencrypted data block offset
    preview_length -- number of unencrypted blocks
    data -- data required for decryption (optional)

    Mutagen cannot decrypt files.
    """
    _framespec = [ Latin1TextSpec('owner'),
                   SizedIntegerSpec('preview_start', 2),
                   SizedIntegerSpec('preview_length', 2) ]
    _optionalspec = [ BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.owner))

    def __str__(self): return self.owner.encode('utf-8')
    def __unicode__(self): return self.owner
    def __eq__(self, other): return self.owner == other

class LINK(FrameOpt):
    """Linked information.

    Attributes:
    frameid -- the ID of the linked frame
    url -- the location of the linked frame
    data -- further ID information for the frame
    """

    _framespec = [ StringSpec('frameid', 4), Latin1TextSpec('url') ]
    _optionalspec = [ BinaryDataSpec('data') ]
    def __HashKey(self):
        try:
            return "%s:%s:%s:%r" % (
                self.FrameID, self.frameid, self.url, self.data)
        except AttributeError:
            return "%s:%s:%s" % (self.FrameID, self.frameid, self.url)
    HashKey = property(__HashKey)
    def __eq__(self, other):
        try: return (self.frameid, self.url, self.data) == other
        except AttributeError: return (self.frameid, self.url) == other

class POSS(Frame):
    """Position synchronisation frame

    Attribute:
    format -- format of the position attribute (frames or milliseconds)
    position -- current position of the file
    """
    _framespec = [ ByteSpec('format'), IntegerSpec('position') ]

    def __pos__(self): return self.position
    def __eq__(self, other): return self.position == other

class UFID(Frame):
    """Unique file identifier.

    Attributes:
    owner -- format/type of identifier
    data -- identifier
    """

    _framespec = [ Latin1TextSpec('owner'), BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.owner))
    def __eq__(s, o):
        if isinstance(o, UFI): return s.owner == o.owner and s.data == o.data
        else: return s.data == o
    def _pprint(self):
        isascii = ord(max(self.data)) < 128
        if isascii: return "%s=%s" % (self.owner, self.data)
        else: return "%s (%d bytes)" % (self.owner, len(self.data))

class USER(Frame):
    """Terms of use.

    Attributes:
    encoding -- text encoding
    lang -- ISO three letter language code
    text -- licensing terms for the audio
    """
    _framespec = [ EncodingSpec('encoding'), StringSpec('lang', 3),
        EncodedTextSpec('text') ]
    HashKey = property(lambda s: '%s:%r' % (s.FrameID, s.lang))

    def __str__(self): return self.text.encode('utf-8')
    def __unicode__(self): return self.text
    def __eq__(self, other): return self.text == other
    def _pprint(self): return "%r=%s" % (self.lang, self.text)

class OWNE(Frame):
    """Ownership frame."""
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('price'),
                   StringSpec('date', 8), EncodedTextSpec('seller') ]

    def __str__(self): return self.seller.encode('utf-8')
    def __unicode__(self): return self.seller
    def __eq__(self, other): return self.seller == other

class COMR(FrameOpt):
    """Commercial frame."""
    _framespec = [ EncodingSpec('encoding'), Latin1TextSpec('price'),
                   StringSpec('valid_until', 8), Latin1TextSpec('contact'),
                   ByteSpec('format'), EncodedTextSpec('seller'),
                   EncodedTextSpec('desc')]
    _optionalspec = [ Latin1TextSpec('mime'), BinaryDataSpec('logo') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s._writeData()))
    def __eq__(self, other): return self._writeData() == other._writeData()

class ENCR(Frame):
    """Encryption method registration.

    The standard does not allow multiple ENCR frames with the same owner
    or the same method. Mutagen only verifies that the owner is unique.
    """
    _framespec = [ Latin1TextSpec('owner'), ByteSpec('method'),
                   BinaryDataSpec('data') ]
    HashKey = property(lambda s: "%s:%s" % (s.FrameID, s.owner))
    def __str__(self): return self.data
    def __eq__(self, other): return self.data == other

class GRID(FrameOpt):
    """Group identification registration."""
    _framespec = [ Latin1TextSpec('owner'), ByteSpec('group') ]
    _optionalspec = [ BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s' % (s.FrameID, s.group))
    def __pos__(self): return self.group
    def __str__(self): return self.owner.encode('utf-8')
    def __unicode__(self): return self.owner
    def __eq__(self, other): return self.owner == other or self.group == other
    

class PRIV(Frame):
    """Private frame."""
    _framespec = [ Latin1TextSpec('owner'), BinaryDataSpec('data') ]
    HashKey = property(lambda s: '%s:%s:%s' % (
        s.FrameID, s.owner, s.data.decode('latin1')))
    def __str__(self): return self.data
    def __eq__(self, other): return self.data == other
    def _pprint(self):
        isascii = ord(max(self.data)) < 128
        if isascii: return "%s=%s" % (self.owner, self.data)
        else: return "%s (%d bytes)" % (self.owner, len(self.data))

class SIGN(Frame):
    """Signature frame."""
    _framespec = [ ByteSpec('group'), BinaryDataSpec('sig') ]
    HashKey = property(lambda s: '%s:%c:%s' % (s.FrameID, s.group, s.sig))
    def __str__(self): return self.sig
    def __eq__(self, other): return self.sig == other

class SEEK(Frame):
    """Seek frame.

    Mutagen does not find tags at seek offsets.
    """
    _framespec = [ IntegerSpec('offset') ]
    def __pos__(self): return self.offset
    def __eq__(self, other): return self.offset == other

class ASPI(Frame):
    """Audio seek point index.

    Attributes: S, L, N, b, and Fi. For the meaning of these, see
    the ID3v2.4 specification. Fi is a list of integers.
    """
    _framespec = [ SizedIntegerSpec("S", 4), SizedIntegerSpec("L", 4),
                   SizedIntegerSpec("N", 2), ByteSpec("b"),
                   ASPIIndexSpec("Fi") ]
    def __eq__(self, other): return self.Fi == other

Frames = dict([(k,v) for (k,v) in globals().items()
        if len(k)==4 and isinstance(v, type) and issubclass(v, Frame)])
"""All supported ID3v2 frames, keyed by frame name."""
del(k); del(v)

# ID3v2.2 frames
class UFI(UFID): "Unique File Identifier"

class TT1(TIT1): "Content group description"
class TT2(TIT2): "Title"
class TT3(TIT3): "Subtitle/Description refinement"
class TP1(TPE1): "Lead Artist/Performer/Soloist/Group"
class TP2(TPE2): "Band/Orchestra/Accompaniment"
class TP3(TPE3): "Conductor"
class TP4(TPE4): "Interpreter/Remixer/Modifier"
class TCM(TCOM): "Composer"
class TXT(TEXT): "Lyricist"
class TLA(TLAN): "Audio Language(s)"
class TCO(TCON): "Content Type (Genre)"
class TAL(TALB): "Album"
class TPA(TPOS): "Part of set"
class TRK(TRCK): "Track Number"
class TRC(TSRC): "International Standard Recording Code (ISRC)"
class TYE(TYER): "Year of recording"
class TDA(TDAT): "Date of recording (DDMM)"
class TIM(TIME): "Time of recording (HHMM)"
class TRD(TRDA): "Recording Dates"
class TMT(TMED): "Source Media Type"
class TFT(TFLT): "File Type"
class TBP(TBPM): "Beats per minute"
class TCP(TCMP): "iTunes Compilation Flag"
class TCR(TCOP): "Copyright (C)"
class TPB(TPUB): "Publisher"
class TEN(TENC): "Encoder"
class TSS(TSSE): "Encoder settings"
class TOF(TOFN): "Original Filename"
class TLE(TLEN): "Audio Length (ms)"
class TSI(TSIZ): "Audio Data size (bytes)"
class TDY(TDLY): "Audio Delay (ms)"
class TKE(TKEY): "Starting Key"
class TOT(TOAL): "Original Album"
class TOA(TOPE): "Original Artist/Perfomer"
class TOL(TOLY): "Original Lyricist"
class TOR(TORY): "Original Release Year"

class TXX(TXXX): "User-defined Text"

class WAF(WOAF): "Official File Information"
class WAR(WOAR): "Official Artist/Performer Information"
class WAS(WOAS): "Official Source Information"
class WCM(WCOM): "Commercial Information"
class WCP(WCOP): "Copyright Information"
class WPB(WPUB): "Official Publisher Information"

class WXX(WXXX): "User-defined URL"

class IPL(IPLS): "Involved people list"
class MCI(MCDI): "Binary dump of CD's TOC"
class ETC(ETCO): "Event timing codes"
class MLL(MLLT): "MPEG location lookup table"
class STC(SYTC): "Synced tempo codes"
class ULT(USLT): "Unsychronised lyrics/text transcription"
class SLT(SYLT): "Synchronised lyrics/text"
class COM(COMM): "Comment"
#class RVA(RVAD)
#class EQU(EQUA)
class REV(RVRB): "Reverb"
class PIC(APIC):
    """Attached Picture.

    The 'mime' attribute of an ID3v2.2 attached picture must be either
    'PNG' or 'JPG'.
    """
    _framespec = [ EncodingSpec('encoding'), StringSpec('mime', 3),
        ByteSpec('type'), EncodedTextSpec('desc'), BinaryDataSpec('data') ]
class GEO(GEOB): "General Encapsulated Object"
class CNT(PCNT): "Play counter"
class POP(POPM): "Popularimeter"
class BUF(RBUF): "Recommended buffer size"

class CRM(Frame):
    """Encrypted meta frame"""
    _framespec = [ Latin1TextSpec('owner'), Latin1TextSpec('desc'),
                   BinaryDataSpec('data') ]
    def __eq__(self, other): return self.data == other

class CRA(AENC): "Audio encryption"

class LNK(LINK):
    """Linked information"""
    _framespec = [ StringSpec('frameid', 3), Latin1TextSpec('url') ]
    _optionalspec = [ BinaryDataSpec('data') ]

Frames_2_2 = dict([(k,v) for (k,v) in globals().items()
        if len(k)==3 and isinstance(v, type) and issubclass(v, Frame)])

# support open(filename) as interface
Open = ID3

# ID3v1.1 support.
def ParseID3v1(string):
    """Parse an ID3v1 tag, returning a list of ID3v2.4 frames."""
    from struct import error as StructError
    frames = {}
    try:
        tag, title, artist, album, year, comment, track, genre = unpack(
            "3s30s30s30s4s29sBB", string)
    except StructError: return None

    if tag != "TAG": return None
    def fix(string):
        return string.split("\x00")[0].strip().decode('latin1')
    title, artist, album, year, comment = map(
        fix, [title, artist, album, year, comment])

    if title: frames["TIT2"] = TIT2(encoding=0, text=title)
    if artist: frames["TPE1"] = TPE1(encoding=0, text=[artist])
    if album: frames["TALB"] = TALB(encoding=0, text=album)
    if year: frames["TDRC"] = TDRC(encoding=0, text=year)
    if comment: frames["COMM"] = COMM(
        encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)
    # Don't read a track number if it looks like the comment was
    # padded with spaces instead of nulls (thanks, WinAmp).
    if track and (track != 32 or string[-3] == '\x00'):
        frames["TRCK"] = TRCK(encoding=0, text=str(track))
    if genre != 255: frames["TCON"] = TCON(encoding=0, text=str(genre))
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
    else: cmnt = ""
    v1["comment"] = cmnt + ("\x00" * (29 - len(cmnt)))

    if "TRCK" in id3:
        try: v1["track"] = chr(+id3["TRCK"])
        except ValueError: v1["track"] = "\x00"
    else: v1["track"] = "\x00"

    if "TCON" in id3:
        try: genre = id3["TCON"].genres[0]
        except IndexError: pass
        else:
            if genre in TCON.GENRES:
                v1["genre"] = chr(TCON.GENRES.index(genre))
    if "genre" not in v1: v1["genre"] = "\xff"

    if "TDRC" in id3:
        v1["year"] = str(id3["TDRC"])[:4]
    elif "TYER" in id3:
        v1["year"] = str(id3["TYER"])[:4]
    else:
        v1["year"] = "\x00\x00\x00\x00"

    return ("TAG%(title)s%(artist)s%(album)s%(year)s%(comment)s"
            "%(track)s%(genre)s") % v1 

class ID3FileType(lib.mutagen.FileType):
    """An unknown type of file with ID3 tags."""

    ID3 = ID3
    
    class _Info(object):
        length = 0
        def __init__(self, fileobj, offset): pass
        pprint = staticmethod(lambda: "Unknown format with ID3 tag")

    def score(filename, fileobj, header):
        return header.startswith("ID3")
    score = staticmethod(score)

    def add_tags(self, ID3=None):
        """Add an empty ID3 tag to the file.

        A custom tag reader may be used in instead of the default
        mutagen.id3.ID3 object, e.g. an EasyID3 reader.
        """
        if ID3 is None:
            ID3 = self.ID3
        if self.tags is None:
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
        self.filename = filename
        try: self.tags = ID3(filename, **kwargs)
        except error: self.tags = None
        if self.tags is not None:
            try: offset = self.tags.size
            except AttributeError: offset = None
        else: offset = None
        try:
            fileobj = file(filename, "rb")
            self.info = self._Info(fileobj, offset)
        finally:
            fileobj.close()
