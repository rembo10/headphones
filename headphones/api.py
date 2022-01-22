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

import json

from headphones import db, mb, updater, importer, searcher, cache, postprocessor, versioncheck, \
    logger
import headphones

cmd_list = ['getIndex', 'getArtist', 'getAlbum', 'getUpcoming', 'getWanted', 'getSnatched',
            'getSimilar', 'getHistory', 'getLogs',
            'findArtist', 'findAlbum', 'addArtist', 'delArtist', 'pauseArtist', 'resumeArtist',
            'refreshArtist',
            'addAlbum', 'queueAlbum', 'unqueueAlbum', 'forceSearch', 'forceProcess',
            'forceActiveArtistsUpdate',
            'getVersion', 'checkGithub', 'shutdown', 'restart', 'update', 'getArtistArt',
            'getAlbumArt',
            'getArtistInfo', 'getAlbumInfo', 'getArtistThumb', 'getAlbumThumb', 'clearLogs',
            'choose_specific_download', 'download_specific_release']


class Api(object):
    def __init__(self):

        self.apikey = None
        self.cmd = None
        self.id = None

        self.kwargs = None

        self.data = None

        self.callback = None

    def checkParams(self, *args, **kwargs):

        if not headphones.CONFIG.API_ENABLED:
            self.data = 'API not enabled'
            return
        if not headphones.CONFIG.API_KEY:
            self.data = 'API key not generated'
            return
        if len(headphones.CONFIG.API_KEY) != 32:
            self.data = 'API key not generated correctly'
            return

        if 'apikey' not in kwargs:
            self.data = 'Missing api key'
            return

        if kwargs['apikey'] != headphones.CONFIG.API_KEY:
            self.data = 'Incorrect API key'
            return
        else:
            self.apikey = kwargs.pop('apikey')

        if 'cmd' not in kwargs:
            self.data = 'Missing parameter: cmd'
            return

        if kwargs['cmd'] not in cmd_list:
            self.data = 'Unknown command: %s' % kwargs['cmd']
            return
        else:
            self.cmd = kwargs.pop('cmd')

        self.kwargs = kwargs
        self.data = 'OK'

    def fetchData(self):

        if self.data == 'OK':
            logger.info('Received API command: %s', self.cmd)
            methodToCall = getattr(self, "_" + self.cmd)
            methodToCall(**self.kwargs)
            if 'callback' not in self.kwargs:
                if isinstance(self.data, str):
                    return self.data
                else:
                    return json.dumps(self.data)
            else:
                self.callback = self.kwargs['callback']
                self.data = json.dumps(self.data)
                self.data = self.callback + '(' + self.data + ');'
                return self.data
        else:
            return self.data

    def _dic_from_query(self, query):

        myDB = db.DBConnection()
        rows = myDB.select(query)

        rows_as_dic = []

        for row in rows:
            row_as_dic = dict(list(zip(list(row.keys()), row)))
            rows_as_dic.append(row_as_dic)

        return rows_as_dic

    def _getIndex(self, **kwargs):

        self.data = self._dic_from_query(
            'SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return

    def _getArtist(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        artist = self._dic_from_query(
            'SELECT * from artists WHERE ArtistID="' + self.id + '"')
        albums = self._dic_from_query(
            'SELECT * from albums WHERE ArtistID="' + self.id + '" order by ReleaseDate DESC')
        description = self._dic_from_query(
            'SELECT * from descriptions WHERE ArtistID="' + self.id + '"')

        self.data = {
            'artist': artist, 'albums': albums, 'description': description}
        return

    def _getAlbum(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        album = self._dic_from_query(
            'SELECT * from albums WHERE AlbumID="' + self.id + '"')
        tracks = self._dic_from_query(
            'SELECT * from tracks WHERE AlbumID="' + self.id + '"')
        description = self._dic_from_query(
            'SELECT * from descriptions WHERE ReleaseGroupID="' + self.id + '"')

        self.data = {
            'album': album, 'tracks': tracks, 'description': description}
        return

    def _getHistory(self, **kwargs):
        self.data = self._dic_from_query(
            'SELECT * from snatched WHERE status NOT LIKE "Seed%" order by DateAdded DESC')
        return

    def _getUpcoming(self, **kwargs):
        self.data = self._dic_from_query(
            "SELECT * from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")
        return

    def _getWanted(self, **kwargs):
        self.data = self._dic_from_query(
            "SELECT * from albums WHERE Status='Wanted'")
        return

    def _getSnatched(self, **kwargs):
        self.data = self._dic_from_query(
            "SELECT * from albums WHERE Status='Snatched'")
        return

    def _getSimilar(self, **kwargs):
        self.data = self._dic_from_query('SELECT * from lastfmcloud')
        return

    def _getLogs(self, **kwargs):
        self.data = headphones.LOG_LIST
        return

    def _clearLogs(self, **kwargs):
        headphones.LOG_LIST = []
        self.data = 'Cleared log'
        return

    def _findArtist(self, **kwargs):
        if 'name' not in kwargs:
            self.data = 'Missing parameter: name'
            return
        if 'limit' in kwargs:
            limit = kwargs['limit']
        else:
            limit = 50

        self.data = mb.findArtist(kwargs['name'], limit)

    def _findAlbum(self, **kwargs):
        if 'name' not in kwargs:
            self.data = 'Missing parameter: name'
            return
        if 'limit' in kwargs:
            limit = kwargs['limit']
        else:
            limit = 50

        self.data = mb.findRelease(kwargs['name'], limit)

    def _addArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        try:
            importer.addArtisttoDB(self.id)
        except Exception as e:
            self.data = e

        return

    def _delArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        myDB = db.DBConnection()
        myDB.action('DELETE from artists WHERE ArtistID="' + self.id + '"')
        myDB.action('DELETE from albums WHERE ArtistID="' + self.id + '"')
        myDB.action('DELETE from tracks WHERE ArtistID="' + self.id + '"')

    def _pauseArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': self.id}
        newValueDict = {'Status': 'Paused'}
        myDB.upsert("artists", newValueDict, controlValueDict)

    def _resumeArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': self.id}
        newValueDict = {'Status': 'Active'}
        myDB.upsert("artists", newValueDict, controlValueDict)

    def _refreshArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        try:
            importer.addArtisttoDB(self.id)
        except Exception as e:
            self.data = e

        return

    def _addAlbum(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        try:
            importer.addReleaseById(self.id)
        except Exception as e:
            self.data = e

        return

    def _queueAlbum(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        if 'new' in kwargs:
            new = kwargs['new']
        else:
            new = False

        if 'lossless' in kwargs:
            lossless = kwargs['lossless']
        else:
            lossless = False

        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': self.id}
        if lossless:
            newValueDict = {'Status': 'Wanted Lossless'}
        else:
            newValueDict = {'Status': 'Wanted'}
        myDB.upsert("albums", newValueDict, controlValueDict)
        searcher.searchforalbum(self.id, new)

    def _unqueueAlbum(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': self.id}
        newValueDict = {'Status': 'Skipped'}
        myDB.upsert("albums", newValueDict, controlValueDict)

    def _forceSearch(self, **kwargs):
        searcher.searchforalbum()

    def _forceProcess(self, **kwargs):
        if 'album_dir' in kwargs:
            album_dir = kwargs['album_dir']
            dir = None
            postprocessor.forcePostProcess(self, dir, album_dir)
        elif 'dir' in kwargs:
            self.dir = kwargs['dir']
            postprocessor.forcePostProcess(self.dir)
        else:
            postprocessor.forcePostProcess()

    def _forceActiveArtistsUpdate(self, **kwargs):
        updater.dbUpdate()

    def _getVersion(self, **kwargs):
        self.data = {
            'git_path': headphones.CONFIG.GIT_PATH,
            'install_type': headphones.INSTALL_TYPE,
            'current_version': headphones.CURRENT_VERSION,
            'latest_version': headphones.LATEST_VERSION,
            'commits_behind': headphones.COMMITS_BEHIND,
        }

    def _checkGithub(self, **kwargs):
        versioncheck.checkGithub()
        self._getVersion()

    def _shutdown(self, **kwargs):
        headphones.SIGNAL = 'shutdown'

    def _restart(self, **kwargs):
        headphones.SIGNAL = 'restart'

    def _update(self, **kwargs):
        headphones.SIGNAL = 'update'

    def _getArtistArt(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getArtwork(ArtistID=self.id)

    def _getAlbumArt(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getArtwork(AlbumID=self.id)

    def _getArtistInfo(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getInfo(ArtistID=self.id)

    def _getAlbumInfo(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getInfo(AlbumID=self.id)

    def _getArtistThumb(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getThumb(ArtistID=self.id)

    def _getAlbumThumb(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        self.data = cache.getThumb(AlbumID=self.id)

    def _choose_specific_download(self, **kwargs):

        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']

        results = searcher.searchforalbum(
            self.id, choose_specific_download=True)

        results_as_dicts = []

        for result in results:
            result_dict = {
                'title': result[0],
                'size': result[1],
                'url': result[2],
                'provider': result[3],
                'kind': result[4]
            }
            results_as_dicts.append(result_dict)

        self.data = results_as_dicts

    def _download_specific_release(self, **kwargs):

        expected_kwargs = ['id', 'title', 'size', 'url', 'provider', 'kind']

        for kwarg in expected_kwargs:
            if kwarg not in kwargs:
                self.data = 'Missing parameter: ' + kwarg
                return self.data

        title = kwargs['title']
        size = kwargs['size']
        url = kwargs['url']
        provider = kwargs['provider']
        kind = kwargs['kind']
        id = kwargs['id']

        for kwarg in expected_kwargs:
            del kwargs[kwarg]

        # Handle situations where the torrent url contains arguments that are
        # parsed
        if kwargs:
            import urllib.request
            import urllib.parse
            import urllib.error
            import urllib.request
            import urllib.error
            import urllib.parse
            url = urllib.parse.quote(
                url, safe=":?/=&") + '&' + urllib.parse.urlencode(kwargs)

        try:
            result = [(title, int(size), url, provider, kind)]
        except ValueError:
            result = [(title, float(size), url, provider, kind)]

        logger.info("Making sure we can download the chosen result")
        (data, bestqual) = searcher.preprocess(result)

        if data and bestqual:
            myDB = db.DBConnection()
            album = myDB.action(
                'SELECT * from albums WHERE AlbumID=?', [id]).fetchone()
            searcher.send_to_downloader(data, bestqual, album)
