# -*- coding: latin-1 -*-
#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

'''
Created on Aug 1, 2011

@author: Michael
'''
import platform
import operator
import os
import re

from headphones import version

#Identify Our Application
USER_AGENT = 'Headphones/-' + version.HEADPHONES_VERSION + ' (' + platform.system() + ' ' + platform.release() + ')'

### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Download album en cours"
notifyStrings[NOTIFY_DOWNLOAD] = "Download album finis"

### Release statuses
UNKNOWN = -1 # should never happen
UNAIRED = 1 # releases that haven't dropped yet
SNATCHED = 2 # qualified with quality
WANTED = 3 # releases we don't have but want to get
DOWNLOADED = 4 # qualified with quality
SKIPPED = 5 # releases we don't want
ARCHIVED = 6 # releases that you don't have locally (counts toward download completion stats)
IGNORED = 7 # releases that you don't want included in your download stats
SNATCHED_PROPER = 9 # qualified with quality


class Quality:

    NONE = 0
    B192 = 1 << 1     # 2
    VBR = 1 << 2     # 4
    B256 = 1 << 3     # 8
    B320 = 1 << 4     #16
    FLAC = 1 << 5     #32

    # put these bits at the other end of the spectrum, far enough out that they shouldn't interfere
    UNKNOWN = 1 << 15

    qualityStrings = {NONE: "N/A",
                      UNKNOWN: "Unknown",
                      B192: "MP3 192",
                      VBR: "MP3 VBR",
                      B256: "MP3 256",
                      B320: "MP3 320",
                      FLAC: "Flac"}

    statusPrefixes = {DOWNLOADED: "Downloaded",
                      SNATCHED: "Snatched"}

    @staticmethod
    def _getStatusStrings(status):
        toReturn = {}
        for x in Quality.qualityStrings.keys():
            toReturn[Quality.compositeStatus(status, x)] = Quality.statusPrefixes[status] + " (" + Quality.qualityStrings[x] + ")"
        return toReturn

    @staticmethod
    def combineQualities(anyQualities, bestQualities):
        anyQuality = 0
        bestQuality = 0
        if anyQualities:
            anyQuality = reduce(operator.or_, anyQualities)
        if bestQualities:
            bestQuality = reduce(operator.or_, bestQualities)
        return anyQuality | (bestQuality << 16)

    @staticmethod
    def splitQuality(quality):
        anyQualities = []
        bestQualities = []
        for curQual in Quality.qualityStrings.keys():
            if curQual & quality:
                anyQualities.append(curQual)
            if curQual << 16 & quality:
                bestQualities.append(curQual)

        return (anyQualities, bestQualities)

    @staticmethod
    def nameQuality(name):

        name = os.path.basename(name)

        # if we have our exact text then assume we put it there
        for x in Quality.qualityStrings:
            if x == Quality.UNKNOWN:
                continue

            regex = '\W' + Quality.qualityStrings[x].replace(' ', '\W') + '\W'
            regex_match = re.search(regex, name, re.I)
            if regex_match:
                return x

        checkName = lambda list, func: func([re.search(x, name, re.I) for x in list])

        #TODO: fix quality checking here
        if checkName(["mp3", "192"], any) and not checkName(["flac"], all):
            return Quality.B192
        elif checkName(["mp3", "256"], any) and not checkName(["flac"], all):
            return Quality.B256
        elif checkName(["mp3", "vbr"], any) and not checkName(["flac"], all):
            return Quality.VBR
        elif checkName(["mp3", "320"], any) and not checkName(["flac"], all):
            return Quality.B320
        else:
            return Quality.UNKNOWN

    @staticmethod
    def assumeQuality(name):

        if name.lower().endswith(".mp3"):
            return Quality.MP3
        elif name.lower().endswith(".flac"):
            return Quality.LOSSLESS
        else:
            return Quality.UNKNOWN

    @staticmethod
    def compositeStatus(status, quality):
        return status + 100 * quality

    @staticmethod
    def qualityDownloaded(status):
        return (status - DOWNLOADED) / 100

    @staticmethod
    def splitCompositeStatus(status):
        """Returns a tuple containing (status, quality)"""
        for x in sorted(Quality.qualityStrings.keys(), reverse=True):
            if status > x * 100:
                return (status - x * 100, x)

        return (Quality.NONE, status)

    @staticmethod
    def statusFromName(name, assume=True):
        quality = Quality.nameQuality(name)
        if assume and quality == Quality.UNKNOWN:
            quality = Quality.assumeQuality(name)
        return Quality.compositeStatus(DOWNLOADED, quality)

    DOWNLOADED = None
    SNATCHED = None
    SNATCHED_PROPER = None

Quality.DOWNLOADED = [Quality.compositeStatus(DOWNLOADED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED = [Quality.compositeStatus(SNATCHED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED_PROPER = [Quality.compositeStatus(SNATCHED_PROPER, x) for x in Quality.qualityStrings.keys()]

MP3 = Quality.combineQualities([Quality.B192, Quality.B256, Quality.B320, Quality.VBR], [])
LOSSLESS = Quality.combineQualities([Quality.FLAC], [])
ANY = Quality.combineQualities([Quality.B192, Quality.B256, Quality.B320, Quality.VBR, Quality.FLAC], [])

qualityPresets = (MP3, LOSSLESS, ANY)
qualityPresetStrings = {MP3: "MP3 (All bitrates 192+)",
                        LOSSLESS: "Lossless (flac)",
                        ANY: "Any"}
