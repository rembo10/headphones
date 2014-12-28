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
    myDB = db.DBConnection()
    asin = myDB.action(
        'SELECT AlbumASIN from albums WHERE AlbumID=?', [albumid]).fetchone()[0]

    if asin:
        return 'http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg' % asin


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
