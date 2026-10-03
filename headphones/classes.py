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

#######################################
# Stolen from Sick-Beard's classes.py #
#######################################

class SearchResult:
    """
    Represents a search result from an indexer.
    """

    def __init__(self):
        self.provider = -1

        # URL to the NZB/torrent file
        self.url = ""

        # used by some providers to store extra info associated with the result
        self.extraInfo = []

        # quality of the release
        self.quality = -1

        # release name
        self.name = ""

    def __str__(self):

        if self.provider is None:
            return "Invalid provider, unable to print self"

        myString = self.provider.name + " @ " + self.url + "\n"
        myString += "Extra Info:\n"
        for extra in self.extraInfo:
            myString += "  " + extra + "\n"
        return myString


class NZBSearchResult(SearchResult):
    """
    Regular NZB result with an URL to the NZB
    """
    resultType = "nzb"


class NZBDataSearchResult(SearchResult):
    """
    NZB result where the actual NZB XML data is stored in the extraInfo
    """
    resultType = "nzbdata"


class TorrentSearchResult(SearchResult):
    """
    Torrent result with an URL to the torrent
    """
    resultType = "torrent"


class Proper:
    def __init__(self, name, url, date):
        self.name = name
        self.url = url
        self.date = date
        self.provider = None
        self.quality = -1

        self.tvdbid = -1
        self.season = -1
        self.episode = -1

    def __str__(self):
        return str(self.date) + " " + self.name + " " + str(self.season) + "x" + str(
            self.episode) + " of " + str(self.tvdbid)
