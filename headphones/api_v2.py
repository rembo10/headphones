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

"""
Modern REST API v2 for Headphones React frontend
"""

import json
import cherrypy
from headphones import db, logger, importer, mb, searcher, librarysync


class APIV2:
    """Modern REST API for React frontend"""

    def __init__(self):
        self.db = db.DBConnection()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        return {"message": "Headphones API v2", "version": "2.0"}

    # ========== Artist Endpoints ==========

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def artists(self, id=None, **kwargs):
        """
        GET /api/v2/artists - Get all artists
        GET /api/v2/artists?id=xxx - Get artist by ID
        POST /api/v2/artists - Add new artist
        PUT /api/v2/artists?id=xxx - Update artist
        DELETE /api/v2/artists?id=xxx - Delete artist
        """
        method = cherrypy.request.method

        if method == "GET":
            if id:
                return self._get_artist(id)
            return self._get_all_artists()
        elif method == "POST":
            return self._add_artist(**kwargs)
        elif method == "PUT":
            if not id:
                raise cherrypy.HTTPError(400, "Artist ID required")
            return self._update_artist(id, **kwargs)
        elif method == "DELETE":
            if not id:
                raise cherrypy.HTTPError(400, "Artist ID required")
            return self._delete_artist(id)
        else:
            raise cherrypy.HTTPError(405, "Method not allowed")

    def _get_all_artists(self):
        """Get all artists from database"""
        try:
            artists = self.db.select(
                'SELECT * FROM artists ORDER BY ArtistSortName COLLATE NOCASE'
            )
            
            result = []
            for artist in artists:
                result.append({
                    'id': artist['ArtistID'],
                    'name': artist['ArtistName'],
                    'status': artist['Status'],
                    'albumCount': artist['HaveTracks'] or 0,
                    'trackCount': artist['TotalTracks'] or 0,
                    'dateAdded': artist['DateAdded'],
                    'imageUrl': f'/api/v2/artwork/artist/{artist["ArtistID"]}' if artist['ArtistID'] else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting artists: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _get_artist(self, artist_id):
        """Get single artist by ID"""
        try:
            artist = self.db.action(
                'SELECT * FROM artists WHERE ArtistID=?', [artist_id]
            ).fetchone()
            
            if not artist:
                raise cherrypy.HTTPError(404, "Artist not found")
            
            return {
                'id': artist['ArtistID'],
                'name': artist['ArtistName'],
                'status': artist['Status'],
                'albumCount': artist['HaveTracks'] or 0,
                'trackCount': artist['TotalTracks'] or 0,
                'dateAdded': artist['DateAdded'],
                'imageUrl': f'/api/v2/artwork/artist/{artist["ArtistID"]}',
            }
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Error getting artist {artist_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _add_artist(self, name=None, mbid=None):
        """Add new artist"""
        if not name and not mbid:
            raise cherrypy.HTTPError(400, "Artist name or MBID required")
        
        try:
            # Add artist to database
            if mbid:
                importer.addArtisttoDB(mbid)
            else:
                # Search for artist first
                results = mb.findArtist(name, limit=1)
                if results:
                    importer.addArtisttoDB(results[0]['id'])
                else:
                    raise cherrypy.HTTPError(404, "Artist not found")
            
            return {"success": True, "message": "Artist added"}
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Error adding artist: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _update_artist(self, artist_id, status=None):
        """Update artist"""
        try:
            if status:
                self.db.action(
                    'UPDATE artists SET Status=? WHERE ArtistID=?',
                    [status, artist_id]
                )
            
            return {"success": True, "message": "Artist updated"}
        except Exception as e:
            logger.error(f"Error updating artist {artist_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _delete_artist(self, artist_id):
        """Delete artist"""
        try:
            self.db.action('DELETE FROM artists WHERE ArtistID=?', [artist_id])
            self.db.action('DELETE FROM albums WHERE ArtistID=?', [artist_id])
            self.db.action('DELETE FROM tracks WHERE ArtistID=?', [artist_id])
            
            return {"success": True, "message": "Artist deleted"}
        except Exception as e:
            logger.error(f"Error deleting artist {artist_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    # ========== Album Endpoints ==========

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def albums(self, id=None, artist_id=None, **kwargs):
        """
        GET /api/v2/albums - Get all albums
        GET /api/v2/albums?id=xxx - Get album by ID
        GET /api/v2/albums?artist_id=xxx - Get albums by artist
        """
        method = cherrypy.request.method

        if method == "GET":
            if id:
                return self._get_album(id)
            if artist_id:
                return self._get_albums_by_artist(artist_id)
            return self._get_all_albums()
        else:
            raise cherrypy.HTTPError(405, "Method not allowed")

    def _get_all_albums(self):
        """Get all albums"""
        try:
            albums = self.db.select(
                'SELECT * FROM albums ORDER BY DateAdded DESC'
            )
            
            result = []
            for album in albums:
                result.append({
                    'id': album['AlbumID'],
                    'artistId': album['ArtistID'],
                    'artistName': album['ArtistName'],
                    'title': album['AlbumTitle'],
                    'releaseDate': album['ReleaseDate'],
                    'status': album['Status'],
                    'type': album['Type'] or 'album',
                    'trackCount': album['TotalTracks'] or 0,
                    'imageUrl': f'/api/v2/artwork/album/{album["AlbumID"]}' if album['AlbumID'] else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting albums: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _get_album(self, album_id):
        """Get single album by ID"""
        try:
            album = self.db.action(
                'SELECT * FROM albums WHERE AlbumID=?', [album_id]
            ).fetchone()
            
            if not album:
                raise cherrypy.HTTPError(404, "Album not found")
            
            return {
                'id': album['AlbumID'],
                'artistId': album['ArtistID'],
                'artistName': album['ArtistName'],
                'title': album['AlbumTitle'],
                'releaseDate': album['ReleaseDate'],
                'status': album['Status'],
                'type': album['Type'] or 'album',
                'trackCount': album['TotalTracks'] or 0,
                'imageUrl': f'/api/v2/artwork/album/{album["AlbumID"]}',
            }
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    def _get_albums_by_artist(self, artist_id):
        """Get all albums for an artist"""
        try:
            albums = self.db.select(
                'SELECT * FROM albums WHERE ArtistID=? ORDER BY ReleaseDate DESC',
                [artist_id]
            )
            
            result = []
            for album in albums:
                result.append({
                    'id': album['AlbumID'],
                    'artistId': album['ArtistID'],
                    'artistName': album['ArtistName'],
                    'title': album['AlbumTitle'],
                    'releaseDate': album['ReleaseDate'],
                    'status': album['Status'],
                    'type': album['Type'] or 'album',
                    'trackCount': album['TotalTracks'] or 0,
                    'imageUrl': f'/api/v2/artwork/album/{album["AlbumID"]}' if album['AlbumID'] else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting albums for artist {artist_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    # ========== Track Endpoints ==========

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def tracks(self, album_id=None):
        """
        GET /api/v2/tracks?album_id=xxx - Get tracks for an album
        """
        if not album_id:
            raise cherrypy.HTTPError(400, "Album ID required")
        
        try:
            tracks = self.db.select(
                'SELECT * FROM tracks WHERE AlbumID=? ORDER BY TrackNumber',
                [album_id]
            )
            
            result = []
            for track in tracks:
                result.append({
                    'id': track['TrackID'],
                    'albumId': track['AlbumID'],
                    'title': track['TrackTitle'],
                    'trackNumber': track['TrackNumber'],
                    'duration': track['TrackDuration'] or 0,
                    'status': 'downloaded' if track['Location'] else 'wanted',
                    'location': track['Location'],
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting tracks for album {album_id}: {e}")
            raise cherrypy.HTTPError(500, str(e))

    # ========== Search Endpoints ==========

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def search(self, query=None, type='artist'):
        """
        GET /api/v2/search?query=xxx&type=artist - Search for artists
        """
        if not query:
            raise cherrypy.HTTPError(400, "Search query required")
        
        try:
            if type == 'artist':
                results = mb.findArtist(query, limit=10)
                return [
                    {
                        'id': r['id'],
                        'name': r['name'],
                        'disambiguation': r.get('disambiguation', ''),
                    }
                    for r in results
                ]
            else:
                raise cherrypy.HTTPError(400, "Invalid search type")
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise cherrypy.HTTPError(500, str(e))

    # ========== Artwork Endpoints ==========

    @cherrypy.expose
    def artwork(self, type=None, id=None):
        """
        GET /api/v2/artwork/artist/:id - Get artist artwork
        GET /api/v2/artwork/album/:id - Get album artwork
        """
        from headphones import cache
        import os
        import sys

        if not type or not id:
            raise cherrypy.HTTPError(400, "Type and ID required")

        try:
            if type == 'artist':
                relpath = cache.getThumb(ArtistID=id, AlbumID=None)
            elif type == 'album':
                relpath = cache.getThumb(ArtistID=None, AlbumID=id)
            else:
                raise cherrypy.HTTPError(400, "Invalid artwork type")

            if not relpath:
                relpath = "data/interfaces/default/images/no-cover-artist.png"
                basedir = os.path.dirname(sys.argv[0])
                path = os.path.join(basedir, relpath)
                cherrypy.response.headers['Content-type'] = 'image/png'
                cherrypy.response.headers['Cache-Control'] = 'no-cache'
            else:
                import headphones
                relpath = relpath.replace('cache/', '', 1)
                path = os.path.join(headphones.CONFIG.CACHE_DIR, relpath)
                fileext = os.path.splitext(relpath)[1][1::]
                cherrypy.response.headers['Content-type'] = 'image/' + fileext
                cherrypy.response.headers['Cache-Control'] = 'max-age=31556926'

            with open(os.path.normpath(path), "rb") as fp:
                return fp.read()
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Error getting artwork: {e}")
            raise cherrypy.HTTPError(500, str(e))

    # ========== Stats Endpoints ==========

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stats(self):
        """Get library statistics"""
        try:
            artists_count = self.db.select('SELECT COUNT(*) as count FROM artists')[0]['count']
            albums_count = self.db.select('SELECT COUNT(*) as count FROM albums')[0]['count']
            tracks_count = self.db.select('SELECT COUNT(*) as count FROM tracks')[0]['count']
            
            return {
                'artists': artists_count,
                'albums': albums_count,
                'tracks': tracks_count,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise cherrypy.HTTPError(500, str(e))
