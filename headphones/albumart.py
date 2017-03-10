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

from headphones import request, db, logger


def getAlbumArt(albumid):

    artwork_path = None
    artwork = None

    # CAA
    artwork_path = 'http://coverartarchive.org/release-group/%s/front' % albumid
    artwork = request.request_content(artwork_path, timeout=20)
    if artwork and len(artwork) >= 100:
        logger.info("Artwork found at CAA")
        return artwork_path, artwork

    # Amazon
    myDB = db.DBConnection()
    asin = myDB.action(
        'SELECT AlbumASIN from albums WHERE AlbumID=?', [albumid]).fetchone()[0]
    if asin:
        artwork_path = 'http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg' % asin
        artwork = request.request_content(artwork_path, timeout=20)
        if artwork and len(artwork) >= 100:
            logger.info("Artwork found at Amazon")
            return artwork_path, artwork

    # last.fm
    from headphones import lastfm

    myDB = db.DBConnection()
    dbalbum = myDB.action(
        'SELECT ArtistName, AlbumTitle, ReleaseID FROM albums WHERE AlbumID=?',
        [albumid]).fetchone()
    if dbalbum['ReleaseID'] != albumid:
        data = lastfm.request_lastfm("album.getinfo", mbid=dbalbum['ReleaseID'])
        if not data:
            data = lastfm.request_lastfm("album.getinfo", artist=dbalbum['ArtistName'],
                                         album=dbalbum['AlbumTitle'])
    else:
        data = lastfm.request_lastfm("album.getinfo", artist=dbalbum['ArtistName'],
                                     album=dbalbum['AlbumTitle'])

    if data:
        try:
            images = data['album']['image']
            for image in images:
                if image['size'] == 'extralarge':
                    artwork_path = image['#text']
                elif image['size'] == 'mega':
                    artwork_path = image['#text']
                    break
        except KeyError:
            artwork_path = None

        if artwork_path:
            artwork = request.request_content(artwork_path, timeout=20)
            if artwork and len(artwork) >= 100:
                logger.info("Artwork found at last.fm")
                return artwork_path, artwork

    logger.info("No suitable album art found.")
    return None, None


def getCachedArt(albumid):
    from headphones import cache

    c = cache.Cache()
    artwork_path = c.get_artwork_from_cache(AlbumID=albumid)

    if not artwork_path:
        return

    if artwork_path.startswith('http://'):
        artwork = request.request_content(artwork_path, timeout=20)

        if not artwork:
            logger.warn("Unable to open url: %s", artwork_path)
            return
    else:
        with open(artwork_path, "r") as fp:
            return fp.read()
