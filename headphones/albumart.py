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

import struct
from six.moves.urllib.parse import urlencode
from io import BytesIO

import headphones
from headphones import db, request, logger


def getAlbumArt(albumid):

    artwork_path = None
    artwork = None

    # CAA
    logger.info("Searching for artwork at CAA")
    #artwork_path = 'https://coverartarchive.org/release-group/%s/front' % albumid
    artwork_path = 'https://coverartarchive.org/release-group/%s' % albumid

    data = request.request_json(artwork_path, timeout=20, whitelist_status_code=404)

    image_url = None
    if data:
        for item in data.get("images", []):
            try:
                if "Front" not in item["types"]:
                    continue

                # Use desired size
                image_url = item["image"]
                if headphones.CONFIG.ALBUM_ART_MAX_WIDTH:
                    if isinstance(item.get("thumbnails"), dict):
                        image_url = item["thumbnails"].get(
                            headphones.CONFIG.ALBUM_ART_MAX_WIDTH, image_url
                        )
                break
            except KeyError:
                pass

    if image_url:
        artwork = getartwork(image_url)
        if artwork:
            logger.info("Artwork found at CAA")
            return artwork_path, artwork

    # Amazon
    logger.info("Searching for artwork at Amazon")
    myDB = db.DBConnection()
    dbalbum = myDB.action(
        'SELECT ArtistName, AlbumTitle, ReleaseID, AlbumASIN FROM albums WHERE AlbumID=?',
        [albumid]).fetchone()
    if dbalbum['AlbumASIN']:
        artwork_path = 'https://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg' % dbalbum['AlbumASIN']
        artwork = getartwork(artwork_path)
        if artwork:
            logger.info("Artwork found at Amazon")
            return artwork_path, artwork

    # last.fm
    from headphones import lastfm
    logger.info("Searching for artwork at last.fm")
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


def jpeg(bites):
    fhandle = BytesIO(bites)
    try:
        fhandle.seek(0)
        size = 2
        ftype = 0
        while not 0xc0 <= ftype <= 0xcf:
            fhandle.seek(size, 1)
            byte = fhandle.read(1)
            while ord(byte) == 0xff:
                byte = fhandle.read(1)
            ftype = ord(byte)
            size = struct.unpack('>H', fhandle.read(2))[0] - 2
        fhandle.seek(1, 1)
        height, width = struct.unpack('>HH', fhandle.read(4))
        return width, height
    except struct.error:
        return None, None
    except TypeError:
        return None, None


def png(bites):
    try:
        check = struct.unpack('>i', bites[4:8])[0]
        if check != 0x0d0a1a0a:
            return None, None
        return struct.unpack('>ii', bites[16:24])
    except struct.error:
        return None, None


def get_image_data(bites):
    type = None
    width = None
    height = None
    if len(bites) < 24:
        return None, None, None

    peek = bites[0:2]
    if peek == b'\xff\xd8':
        width, height = jpeg(bites)
        type = 'jpg'
    elif peek == b'\x89P':
        width, height = png(bites)
        type = 'png'
    return type, width, height


def getartwork(artwork_path):
    artwork = bytes()
    minwidth = 0
    maxwidth = 0
    if headphones.CONFIG.ALBUM_ART_MIN_WIDTH:
        minwidth = int(headphones.CONFIG.ALBUM_ART_MIN_WIDTH)
    if headphones.CONFIG.ALBUM_ART_MAX_WIDTH:
        maxwidth = int(headphones.CONFIG.ALBUM_ART_MAX_WIDTH)

    resp = request.request_response(artwork_path, timeout=20, stream=True, whitelist_status_code=404)

    if resp:
        img_width = None
        for chunk in resp.iter_content(chunk_size=1024):
            artwork += chunk
            if not img_width and (minwidth or maxwidth):
                img_type, img_width, img_height = get_image_data(artwork)
            # Check min/max
            if img_width and (minwidth or maxwidth):
                if minwidth and img_width < minwidth:
                    logger.info("Artwork is too small. Type: %s. Width: %s. Height: %s",
                                img_type, img_width, img_height)
                    artwork = None
                    break
                elif maxwidth and img_width > maxwidth:
                    # Downsize using proxy service to max width
                    artwork = bytes()
                    url = "https://images.weserv.nl"
                    params = {
                        "url": artwork_path,
                        "w": maxwidth
                    }
                    headers = {"User-Agent": "Headphones"}
                    r = request.request_response(
                        url,
                        params=params,
                        timeout=20,
                        stream=True,
                        whitelist_status_code=404,
                        headers=headers
                    )
                    if r:
                        for chunk in r.iter_content(chunk_size=1024):
                            artwork += chunk
                        r.close()
                        logger.info("Artwork is greater than the maximum width, downsized using proxy service")
                    break
        resp.close()

    return artwork


def getCachedArt(albumid):
    from headphones import cache

    c = cache.Cache()
    artwork_path = c.get_artwork_from_cache(AlbumID=albumid)

    if not artwork_path:
        return

    if artwork_path.startswith("http"):
        artwork = request.request_content(artwork_path, timeout=20)

        if not artwork:
            logger.warn("Unable to open url: %s", artwork_path)
            return
    else:
        with open(artwork_path, "r") as fp:
            return fp.read()
