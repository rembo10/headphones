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

import StringIO
import struct
from contextlib import closing
from six.moves.urllib.parse import urlencode
import requests as requests

import headphones
from headphones import db, request, logger


def getAlbumArt(albumid):

    artwork_path = None
    artwork = None

    # CAA
    logger.info("Searching for artwork at CAA")
    artwork_path = 'http://coverartarchive.org/release-group/%s/front' % albumid
    artwork = getartwork(artwork_path)
    if artwork:
        logger.info("Artwork found at CAA")
        return artwork_path, artwork

    # Amazon
    logger.info("Searching for artwork at Amazon")
    myDB = db.DBConnection()
    asin = myDB.action(
        'SELECT AlbumASIN from albums WHERE AlbumID=?', [albumid]).fetchone()[0]
    if asin:
        artwork_path = 'http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg' % asin
        artwork = getartwork(artwork_path)
        if artwork:
            logger.info("Artwork found at Amazon")
            return artwork_path, artwork

    # last.fm
    from headphones import lastfm

    logger.info("Searching for artwork at last.fm")
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
            artwork = getartwork(artwork_path)
            if artwork:
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


def getartwork(artwork_path):

    artwork = None
    minwidth = headphones.CONFIG.ALBUM_ART_MIN_WIDTH
    maxwidth = headphones.CONFIG.ALBUM_ART_MAX_WIDTH
    useproxy = False

    with closing(requests.get(artwork_path, stream=True)) as resp:

        # Get 1st block of artwork
        data = resp.iter_content(chunk_size=1024)
        artwork = b''
        for chunk in data:
            artwork += chunk
            if len(artwork) >= 32:
                break
        else:
            artwork = None

        # Check image and size
        if artwork:
            img_type, img_width, img_height = getImageInfo(artwork)

            if not img_type or minwidth and img_width < minwidth:
                logger.info("Artwork is not suitable or too small. Type: %s. Width: %s. Height: %s",
                            img_type, img_width, img_height)
                artwork = None
            elif maxwidth and img_width > maxwidth:
                useproxy = True
            else:
                # Get rest of artwork
                for chunk in data:
                    artwork += chunk

    # Downsize using proxy service to max width
    if useproxy:
        logger.info("Artwork is greater than the maximum width, downsizing using proxy service")
        artwork_path = '{0}?{1}'.format('http://images.weserv.nl/', urlencode({
            'url': artwork_path.replace('http://', ''),
            'w': maxwidth,
        }))
        artwork = request.request_content(artwork_path, timeout=20)

    return artwork


def getImageInfo(data):
    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = None

    # handle GIFs
    if size >= 10 and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif size >= 24 and data.startswith('\211PNG\r\n\032\n') and data[12:16] == 'IHDR':
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif size >= 16 and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif size >= 2 and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO.StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while b and ord(b) != 0xDA:
                while ord(b) != 0xFF:
                    b = jpeg.read(1)
                while ord(b) == 0xFF:
                    b = jpeg.read(1)
                if ord(b) >= 0xC0 and ord(b) <= 0xC3:
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0]) - 2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    return content_type, width, height
