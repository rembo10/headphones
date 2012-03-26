import headphones

from headphones import db, mb, logger

import lib.simplejson as simplejson
from xml.dom.minidom import Document
import copy

cmd_list = [ 'getIndex', 'findArtist']

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
		
		#if 'format' not in kwargs:
		#	self.format = 'json'
		#else:
		#	if kwargs['format'] not in ['json', 'xml']:
		#		self.data = 'Unknown format: %s' % kwargs['format']
		#		return
		#	else:
		#		self.format = kwargs.pop('format')
			
		self.kwargs = kwargs
		self.data = 'OK'

	def fetchData(self):
	
		if self.cmd == 'getIndex':
			self._getIndex()
			
		if self.cmd == 'findArtist':
			self._findArtist(**self.kwargs)
			
		return simplejson.dumps(self.data)
		
	def _getIndex(self):
		myDB = db.DBConnection()
		artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
		
		artists_as_dic = []
		for artist in artists:
			artist_as_dic = {
				'ArtistID' : artist['ArtistID'],
				'ArtistName' : artist['ArtistName'],
				'ArtistSortName' : artist['ArtistSortName'],
				'DateAdded' : artist['DateAdded'],
				'Status' : artist['Status'],
				'IncludeExtras' : artist['IncludeExtras'],
				'LatestAlbum' : artist['LatestAlbum'],
				'ReleaseDate' : artist['ReleaseDate'],
				'AlbumID' : artist['AlbumID'],
				'HaveTracks' : artist['HaveTracks'],
				'TotalTracks' : artist['TotalTracks']}
			artists_as_dic.append(artist_as_dic)
		
		self.data = artists_as_dic
		
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
		