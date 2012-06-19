import headphones

from headphones import db, mb, importer, searcher, postprocessor, versioncheck, logger

import lib.simplejson as simplejson
from xml.dom.minidom import Document
import copy

cmd_list = [ 'getIndex', 'getArtist', 'getAlbum', 'getUpcoming', 'getWanted', 'getSimilar', 'getHistory', 'getLogs', 
            'findArtist', 'findAlbum', 'addArtist', 'delArtist', 'pauseArtist', 'resumeArtist', 'refreshArtist',
            'queueAlbum', 'unqueueAlbum', 'forceSearch', 'forceProcess', 'getVersion', 'checkGithub', 
            'shutdown', 'restart', 'update', ]

class Api(object):

    def __init__(self):
    
        self.apikey = None
        self.cmd = None
        self.id = None
        
        self.kwargs = None

        self.data = None

        self.callback = None

        
    def checkParams(self,*args,**kwargs):
        
        if not headphones.API_ENABLED:
            self.data = 'API not enabled'
            return
        if not headphones.API_KEY:
            self.data = 'API key not generated'
            return
        if len(headphones.API_KEY) != 32:
            self.data = 'API key not generated correctly'
            return
        
        if 'apikey' not in kwargs:
            self.data = 'Missing api key'
            return
            
        if kwargs['apikey'] != headphones.API_KEY:
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
            logger.info('Recieved API command: ' + self.cmd)
            methodToCall = getattr(self, "_" + self.cmd)
            result = methodToCall(**self.kwargs)
            if 'callback' not in self.kwargs:
                if type(self.data) == type(''):
                    return self.data
                else:
                    return simplejson.dumps(self.data)
            else:
                self.callback = self.kwargs['callback']
                self.data = simplejson.dumps(self.data)
                self.data = self.callback + '(' + self.data + ');'
                return self.data
        else:
            return self.data
        
    def _dic_from_query(self,query):
    
        myDB = db.DBConnection()
        rows = myDB.select(query)
        
        rows_as_dic = []
        
        for row in rows:
            row_as_dic = dict(zip(row.keys(), row))
            rows_as_dic.append(row_as_dic)
            
        return rows_as_dic
        
    def _getIndex(self, **kwargs):
        
        self.data = self._dic_from_query('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return  
    
    def _getArtist(self, **kwargs):
    
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']
    
        artist = self._dic_from_query('SELECT * from artists WHERE ArtistID="' + self.id + '"')
        albums = self._dic_from_query('SELECT * from albums WHERE ArtistID="' + self.id + '" order by ReleaseDate DESC')
        
        self.data = { 'artist': artist, 'albums': albums }
        return
    
    def _getAlbum(self, **kwargs):
    
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']
            
        album = self._dic_from_query('SELECT * from albums WHERE AlbumID="' + self.id + '"')
        tracks = self._dic_from_query('SELECT * from tracks WHERE AlbumID="' + self.id + '"')
        description = self._dic_from_query('SELECT * from descriptions WHERE ReleaseGroupID="' + self.id + '"')
        
        self.data = { 'album' : album, 'tracks' : tracks, 'description' : description }
        return
        
    def _getHistory(self, **kwargs):
        self.data = self._dic_from_query('SELECT * from snatched order by DateAdded DESC')
        return
    
    def _getUpcoming(self, **kwargs):
        self.data = self._dic_from_query("SELECT * from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")
        return
    
    def _getWanted(self, **kwargs):
        self.data = self._dic_from_query("SELECT * from albums WHERE Status='Wanted'")
        return
        
    def _getSimilar(self, **kwargs):
        self.data = self._dic_from_query('SELECT * from lastfmcloud')
        return
        
    def _getLogs(self, **kwargs):
        pass
    
    def _findArtist(self, **kwargs):
        if 'name' not in kwargs:
            self.data = 'Missing parameter: name'
            return
        if 'limit' in kwargs:
            limit = kwargs['limit']
        else:
            limit=50
        
        self.data = mb.findArtist(kwargs['name'], limit)

    def _findAlbum(self, **kwargs):
        if 'name' not in kwargs:
            self.data = 'Missing parameter: name'
            return
        if 'limit' in kwargs:
            limit = kwargs['limit']
        else:
            limit=50
        
        self.data = mb.findRelease(kwargs['name'], limit)
        
    def _addArtist(self, **kwargs):
        if 'id' not in kwargs:
            self.data = 'Missing parameter: id'
            return
        else:
            self.id = kwargs['id']
            
        try:
            importer.addArtisttoDB(self.id)
        except Exception, e:
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
        except Exception, e:
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
        postprocessor.forcePostProcess()    
        
    def _getVersion(self, **kwargs):
        self.data = { 
            'git_path' : headphones.GIT_PATH,
            'install_type' : headphones.INSTALL_TYPE,
            'current_version' : headphones.CURRENT_VERSION,
            'latest_version' : headphones.LATEST_VERSION,
            'commits_behind' : headphones.COMMITS_BEHIND,
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
