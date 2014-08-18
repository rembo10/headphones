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

import threading
import headphones
from headphones import db, utorrent, transmission

postprocessor_lock = threading.Lock()

# Remove Torrent + data if Post Processed and finished Seeding
def checkTorrentFinished():

    with postprocessor_lock:

        myDB = db.DBConnection()
        results = myDB.select('SELECT * from snatched WHERE Status="Seed_Processed"')

        for album in results:
            hash = album['FolderName']
            albumid = album['AlbumID']
            torrent_removed = False
            if headphones.TORRENT_DOWNLOADER == 1:
                torrent_removed = transmission.removeTorrent(hash, True)
            else:
                torrent_removed = utorrent.removeTorrent(hash, True)

            if torrent_removed:
                myDB.action('DELETE from snatched WHERE status = "Seed_Processed" and AlbumID=?', [albumid])
