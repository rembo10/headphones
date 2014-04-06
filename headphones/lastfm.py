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

from headphones import db, logger, helpers

from collections import defaultdict

API_KEY = '395e6ec6bb557382fc41fde867bce66f'

def getSimilar():
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists ORDER BY HaveTracks DESC')

    artistlist = []

    for result in results[:12]:
        params = {
            "method": "artist.getsimilar",
            "mbid": result['ArtistID'],
            "api_key": API_KEY
        }

        url = 'http://ws.audioscrobbler.com/2.0/'
        dom = request_minidom(url, timeout=20, params=params)

        if not dom:
            logger.debug("Could not parse similar artist data from Last.FM")
            continue

        artists = dom.getElementsByTagName("artist")
        logger.debug("Fetched %d artists from Last.FM", len(artists))

        for artist in artists:
            namenode = artist.getElementsByTagName("name")[0].childNodes
            mbidnode = artist.getElementsByTagName("mbid")[0].childNodes

            for node in namenode:
                artist_name = node.data
            for node in mbidnode:
                artist_mbid = node.data

            try:
                if not any(artist_mbid in x for x in results):
                    artistlist.append((artist_name, artist_mbid))
            except Exception:
                logger.exception("Unhandled exception")
                continue

    count = defaultdict(int)

    for artist, mbid in artistlist:
        count[artist, mbid] += 1

    items = count.items()
    top_list = sorted(items, key=lambda x: x[1], reverse=True)[:25]

    random.shuffle(top_list)

    myDB.action('''DELETE from lastfmcloud''')
    for tuple in top_list:
        artist_name, artist_mbid = tuple[0]
        count = tuple[1]
        myDB.action('INSERT INTO lastfmcloud VALUES( ?, ?, ?)', [artist_name, artist_mbid, count])

def getArtists():
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    if not headphones.LASTFM_USERNAME:
        logger.warn("Last.FM username not set")
        return

    params = {
        "method": "library.getartists",
        "limit": 10000,
        "api_key": API_KEY,
        "user": headphones.LASTFM_USERNAME
    }

    url = 'http://ws.audioscrobbler.com/2.0/'
    dom = request_minidom(url, timeout=20, params=params)

    if not dom:
        logger.debug("Could not parse artist list from Last.FM")
        return

    artists = dom.getElementsByTagName("artist")
    logger.debug("Fetched %d artists from Last.FM", len(artists))

    artistlist = []

    for artist in artists:
        mbidnode = artist.getElementsByTagName("mbid")[0].childNodes

        for node in mbidnode:
            artist_mbid = node.data

        try:
            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)
        except Exception:
            logger.exception("Unhandled exception")
            continue

    from headphones import importer

    for artistid in artistlist:
        importer.addArtisttoDB(artistid)

    logger.info("Imported %d new artists from Last.FM", len(artistid))

def getTagTopArtists(tag, limit=50):
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    params = {
        "method": "tag.gettopartists",
        "limit": limit,
        "tag": tag,
        "api_key": API_KEY
    }

    url = 'http://ws.audioscrobbler.com/2.0/'
    dom = request_minidom(url, timeout=20, params=param)

    if not dom:
        logger.debug("Could not parse artist list from Last.FM")
        return

    artists = d.getElementsByTagName("artist")
    logger.debug("Fetched %d artists from Last.FM", len(artists))

    artistlist = []

    for artist in artists:
        mbidnode = artist.getElementsByTagName("mbid")[0].childNodes

        for node in mbidnode:
            artist_mbid = node.data

        try:
            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)
        except Exception:
            logger.exception("Unhandled exception")
            continue

    from headphones import importer

    for artistid in artistlist:
        importer.addArtisttoDB(artistid)

def getAlbumDescription(rgid, artist, album):
    myDB = db.DBConnection()
    result = myDB.select('SELECT Summary from descriptions WHERE ReleaseGroupID=?', [rgid])

    if result:
        logger.info("No summary found for release group id: %s", rgid)
        return

    params = {
        "method": 'album.getInfo',
        "api_key": api_key,
        "artist": artist.encode('utf-8'),
        "album": album.encode('utf-8')
    }

    url = 'http://ws.audioscrobbler.com/2.0/'
    dom = helpers.request_minidom(url, timeout=20, params=params)

    if not dom:
        logger.debug("Could not parse album description from Last.FM")
        return

    if dom.getElementsByTagName("error"):
        logger.debug("Last.FM returned error")
        return

    albuminfo = dom.getElementsByTagName("album")
    logger.debug("Fetched %d albums from Last.FM", len(artists))

    for item in albuminfo:
        try:
            summarynode = item.getElementsByTagName("summary")[0].childNodes
            contentnode = item.getElementsByTagName("content")[0].childNodes

            for node in summarynode:
                summary = node.data
            for node in contentnode:
                content = node.data

            controlValueDict = {'ReleaseGroupID': rgid}
            newValueDict = {'Summary': summary,
                            'Content': content}
            myDB.upsert("descriptions", newValueDict, controlValueDict)
        except:
            logger.exception("Unhandled exception")
            return