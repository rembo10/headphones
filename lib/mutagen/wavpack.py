# A WavPack reader/tagger
#
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""WavPack reading and writing.

WavPack is a lossless format that uses APEv2 tags. Read
http://www.wavpack.com/ for more information.
"""

__all__ = ["WavPack", "Open", "delete"]

from mutagen.apev2 import APEv2File, error, delete
from mutagen._util import cdata


class WavPackHeaderError(error):
    pass

RATES = [6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100,
         48000, 64000, 88200, 96000, 192000]


class WavPackInfo(object):
    """WavPack stream information.

    Attributes:

    * channels - number of audio channels (1 or 2)
    * length - file length in seconds, as a float
    * sample_rate - audio sampling rate in Hz
    * version - WavPack stream version
    """

    def __init__(self, fileobj):
        header = fileobj.read(28)
        if len(header) != 28 or not header.startswith("wvpk"):
            raise WavPackHeaderError("not a WavPack file")
        samples = cdata.uint_le(header[12:16])
        flags = cdata.uint_le(header[24:28])
        self.version = cdata.short_le(header[8:10])
        self.channels = bool(flags & 4) or 2
        self.sample_rate = RATES[(flags >> 23) & 0xF]
        self.length = float(samples) / self.sample_rate

    def pprint(self):
        return "WavPack, %.2f seconds, %d Hz" % (self.length, self.sample_rate)


class WavPack(APEv2File):
    _Info = WavPackInfo
    _mimes = ["audio/x-wavpack"]

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith("wvpk") * 2


Open = WavPack
