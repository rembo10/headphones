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

import random
import time
import headphones

from headphones import db, logger, request

from collections import defaultdict

ENTRY_POINT = 'http://ws.audioscrobbler.com/2.0/'
API_KEY = '395e6ec6bb557382fc41fde867bce66f'

def request_lastfm(method, **kwargs):
    """
    Call a Last.FM API method. Automatically sets the method and API key. Method
    will return the result if no error occured.

    By default, this method will request the JSON format, since it is lighter
    than XML.
    """

    # Prepare request
    kwargs["method"] = method
    kwargs.setdefault("api_key", API_KEY)
    kwargs.setdefault("format", "json")

    # Send request
    logger.debug("Calling Last.FM method: %s", method)
    data = request.request_json(ENTRY_POINT, timeout=20, params=kwargs)

    # Parse response and check for errors.
    if not data:
        logger.error("Error calling Last.FM method: %s", method)
        return

    if "error" in data:
        logger.debug("Last.FM returned an error: %s", data["message"])
        return

    return data

def getSimilar():
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists ORDER BY HaveTracks DESC')

    logger.info("Fetching similar artists from Last.FM for tag cloud")
    artistlist = []

    for result in results[:12]:
        data = request_lastfm("artist.getsimilar", mbid=result['ArtistId'])
        time.sleep(10)

        if data and "similarartists" in data:
            artists = data["similarartists"]["artist"]

            for artist in artists:
                try:
                    artist_mbid = artist["mbid"]
                    artist_name = artist["name"]
                except TypeError:
                    continue

                if not any(artist_mbid in x for x in results):
                    artistlist.append((artist_name, artist_mbid))

    # Add new artists to tag cloud
    logger.debug("Fetched %d artists from Last.FM", len(artistlist))
    count = defaultdict(int)

    for artist, mbid in artistlist:
        count[artist, mbid] += 1

    items = count.items()
    top_list = sorted(items, key=lambda x: x[1], reverse=True)[:25]

    random.shuffle(top_list)

    myDB.action("DELETE from lastfmcloud")
    for item in top_list:
        artist_name, artist_mbid = item[0]
        count = item[1]

        myDB.action('INSERT INTO lastfmcloud VALUES( ?, ?, ?)', [artist_name, artist_mbid, count])

    logger.debug("Inserted %d artists into Last.FM tag cloud", len(top_list))

def getArtists():
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    if not headphones.LASTFM_USERNAME:
        logger.warn("Last.FM username not set, not importing artists.")
        return

    logger.info("Fetching artists from Last.FM for username: %s", headphones.LASTFM_USERNAME)
    data = request_lastfm("library.getartists", limit=10000, user=headphones.LASTFM_USERNAME)

    if data and "artists" in data:
        artistlist = []
        artists = data["artists"]["artist"]
        logger.debug("Fetched %d artists from Last.FM", len(artists))

        for artist in artists:
            artist_mbid = artist["mbid"]

            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)

        from headphones import importer

        for artistid in artistlist:
            importer.addArtisttoDB(artistid)

        logger.info("Imported %d new artists from Last.FM", len(artistlist))

def getTagTopArtists(tag, limit=50):
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    logger.info("Fetching top artists from Last.FM for tag: %s", tag)
    data = request_lastfm("tag.gettopartists", limit=limit, tag=tag)

    if data and "topartists" in data:
        artistlist = []
        artists = data["topartists"]["artist"]
        logger.debug("Fetched %d artists from Last.FM", len(artists))

        for artist in artists:
            artist_mbid = artist["mbid"]

            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)

        from headphones import importer

        for artistid in artistlist:
            importer.addArtisttoDB(artistid)

        logger.debug("Added %d new artists from Last.FM", len(artistlist))