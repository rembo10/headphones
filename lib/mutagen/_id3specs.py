# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import struct
from struct import unpack, pack
from warnings import warn

from mutagen._id3util import ID3JunkFrameError, ID3Warning, BitPaddedInt


class Spec(object):
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        raise TypeError("Spec objects are unhashable")

    def _validate23(self, frame, value, **kwargs):
        """Return a possibly modified value which, if written,
        results in valid id3v2.3 data.
        """

        return value


class ByteSpec(Spec):
    def read(self, frame, data):
        return ord(data[0]), data[1:]

    def write(self, frame, value):
        return chr(value)

    def validate(self, frame, value):
        if value is not None:
            chr(value)
        return value


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
        if enc < 16:
            return enc, data
        else:
            return 0, chr(enc)+data

    def validate(self, frame, value):
        if 0 <= value <= 3:
            return value
        if value is None:
            return None
        raise ValueError('Invalid Encoding: %r' % value)

    def _validate23(self, frame, value, **kwargs):
        # only 0, 1 are valid in v2.3, default to utf-16
        return min(1, value)


class StringSpec(Spec):
    def __init__(self, name, length):
        super(StringSpec, self).__init__(name)
        self.len = length

    def read(s, frame, data):
        return data[:s.len], data[s.len:]

    def write(s, frame, value):
        if value is None:
            return '\x00' * s.len
        else:
            return (str(value) + '\x00' * s.len)[:s.len]

    def validate(s, frame, value):
        if value is None:
            return None
        if isinstance(value, basestring) and len(value) == s.len:
            return value
        raise ValueError('Invalid StringSpec[%d] data: %r' % (s.len, value))


class BinaryDataSpec(Spec):
    def read(self, frame, data):
        return data, ''

    def write(self, frame, value):
        return str(value)

    def validate(self, frame, value):
        return str(value)


class EncodedTextSpec(Spec):
    # Okay, seriously. This is private and defined explicitly and
    # completely by the ID3 specification. You can't just add
    # encodings here however you want.
    _encodings = (
        ('latin1', '\x00'),
        ('utf16', '\x00\x00'),
        ('utf_16_be', '\x00\x00'),
        ('utf8', '\x00')
    )

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
                    if offset & 1:
                        continue
                    data, ret = data[0:offset], data[offset+2:]
                    break
            except ValueError:
                pass

        if len(data) < len(term):
            return u'', ret
        return data.decode(enc), ret

    def write(self, frame, value):
        enc, term = self._encodings[frame.encoding]
        return value.encode(enc) + term

    def validate(self, frame, value):
        return unicode(value)


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
            if len(self.specs) != 1:
                values.append(record)
            else:
                values.append(record[0])
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
        if value is None:
            return []
        if self.sep and isinstance(value, basestring):
            value = value.split(self.sep)
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [
                    [s.validate(frame, v) for (v, s) in zip(val, self.specs)]
                    for val in value]
        raise ValueError('Invalid MultiSpec data: %r' % value)

    def _validate23(self, frame, value, **kwargs):
        if len(self.specs) != 1:
            return [[s._validate23(frame, v, **kwargs)
                     for (v, s) in zip(val, self.specs)]
                    for val in value]

        spec = self.specs[0]

        # Merge single text spec multispecs only.
        # (TimeStampSpec beeing the exception, but it's not a valid v2.3 frame)
        if not isinstance(spec, EncodedTextSpec) or \
                isinstance(spec, TimeStampSpec):
            return value

        value = [spec._validate23(frame, v, **kwargs) for v in value]
        if kwargs.get("sep") is not None:
            return [spec.validate(frame, kwargs["sep"].join(value))]
        return value


class EncodedNumericTextSpec(EncodedTextSpec):
    pass


class EncodedNumericPartTextSpec(EncodedTextSpec):
    pass


class Latin1TextSpec(EncodedTextSpec):
    def read(self, frame, data):
        if '\x00' in data:
            data, ret = data.split('\x00', 1)
        else:
            ret = ''
        return data.decode('latin1'), ret

    def write(self, data, value):
        return value.encode('latin1') + '\x00'

    def validate(self, frame, value):
        return unicode(value)


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
        if isinstance(text, ID3TimeStamp):
            text = text.text
        self.text = text

    __formats = ['%04d'] + ['%02d'] * 5
    __seps = ['-', '-', ' ', ':', ':', 'x']

    def get_text(self):
        parts = [self.year, self.month, self.day,
                 self.hour, self.minute, self.second]
        pieces = []
        for i, part in enumerate(iter(iter(parts).next, None)):
            pieces.append(self.__formats[i] % part + self.__seps[i])
        return u''.join(pieces)[:-1]

    def set_text(self, text, splitre=re.compile('[-T:/.]|\s+')):
        year, month, day, hour, minute, second = \
            splitre.split(text + ':::::')[:6]
        for a in 'year month day hour minute second'.split():
            try:
                v = int(locals()[a])
            except ValueError:
                v = None
            setattr(self, a, v)

    text = property(get_text, set_text, doc="ID3v2.4 date and time.")

    def __str__(self):
        return self.text

    def __repr__(self):
        return repr(self.text)

    def __cmp__(self, other):
        return cmp(self.text, other.text)

    __hash__ = object.__hash__

    def encode(self, *args):
        return self.text.encode(*args)


class TimeStampSpec(EncodedTextSpec):
    def read(self, frame, data):
        value, data = super(TimeStampSpec, self).read(frame, data)
        return self.validate(frame, value), data

    def write(self, frame, data):
        return super(TimeStampSpec, self).write(frame,
                                                data.text.replace(' ', 'T'))

    def validate(self, frame, value):
        try:
            return ID3TimeStamp(value)
        except TypeError:
            raise ValueError("Invalid ID3TimeStamp: %r" % value)


class ChannelSpec(ByteSpec):
    (OTHER, MASTER, FRONTRIGHT, FRONTLEFT, BACKRIGHT, BACKLEFT, FRONTCENTRE,
     BACKCENTRE, SUBWOOFER) = range(9)


class VolumeAdjustmentSpec(Spec):
    def read(self, frame, data):
        value, = unpack('>h', data[0:2])
        return value/512.0, data[2:]

    def write(self, frame, value):
        return pack('>h', int(round(value * 512)))

    def validate(self, frame, value):
        if value is not None:
            try:
                self.write(frame, value)
            except struct.error:
                raise ValueError("out of range")
        return value


class VolumePeakSpec(Spec):
    def read(self, frame, data):
        # http://bugs.xmms.org/attachment.cgi?id=113&action=view
        peak = 0
        bits = ord(data[0])
        bytes = min(4, (bits + 7) >> 3)
        # not enough frame data
        if bytes + 1 > len(data):
            raise ID3JunkFrameError
        shift = ((8 - (bits & 7)) & 7) + (4 - bytes) * 8
        for i in range(1, bytes+1):
            peak *= 256
            peak += ord(data[i])
        peak *= 2 ** shift
        return (float(peak) / (2**31-1)), data[1+bytes:]

    def write(self, frame, value):
        # always write as 16 bits for sanity.
        return "\x10" + pack('>H', int(round(value * 32768)))

    def validate(self, frame, value):
        if value is not None:
            try:
                self.write(frame, value)
            except struct.error:
                raise ValueError("out of range")
        return value


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
            if len(data) < value_idx + l + 4:
                raise ID3JunkFrameError
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
        if frame.b == 16:
            format = "H"
        elif frame.b == 8:
            format = "B"
        else:
            raise ValueError("frame.b must be 8 or 16")
        return struct.pack(">" + format * frame.N, *values)

    def validate(self, frame, values):
        return values
