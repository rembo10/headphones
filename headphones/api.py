import headphones

from headphones import db, mb, logger

import lib.simplejson as simplejson
from xml.dom.minidom import Document
import copy

cmd_list = [ 'getIndex', 'getArtist', 'getAlbum', 'findArtist', 'findAlbum']

class Api(object):

	def __init__(self):
	
		self.apikey = None
		self.cmd = None
		self.id = None
		
		self.kwargs = None

		self.data = None
		
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
			methodToCall = getattr(self, "_" + self.cmd)
			result = methodToCall(**self.kwargs)

			return simplejson.dumps(self.data)
			
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
		
	def _getIndex(self):
		
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
		