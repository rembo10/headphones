import headphones

from headphones import db, mb, logger

import lib.simplejson as simplejson

cmd_list = [ 'findArtist']

class Api(object):

	def __init__(self):
	
		self.apikey = None
		self.cmd = None
		self.format = 'json'
		self.id = None
		
		self.kwargs = None
		
		self.rawdata = None
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
		
		if 'format' not in kwargs:
			self.format = 'json'
		else:
			if kwargs['format'] not in ['json', 'xml']:
				self.data = 'Unknown format: %s' % kwargs['format']
				return
			else:
				self.format = kwargs.pop('format')
			
		self.kwargs = kwargs
		self.data = 'OK'
		
	def formatData(self):
	
		self.data = '%s' % self.data
		
	def fetchData(self):
	
		if self.cmd == 'findArtist':
			self.findArtist(**self.kwargs)
			
		return simplejson.dumps(self.data)
		
	def findArtist(self, **kwargs):
		if 'type' not in kwargs:
			self.data = 'Missing parameter: type'
			return
		if 'name' not in kwargs:
			self.data = 'Missing parameter: name'
			return
		if kwargs['type'] not in ['artist','album']:
			self.data = 'Incorrect type: %s' % kwargs['type']
			return
		if 'limit' in kwargs:
			limit = kwargs['limit']
		else:
			limit=50
		if kwargs['type'] == 'artist':
			self.data = mb.findArtist(kwargs['name'], limit)
		else:
			self.data = mb.findRelease(kwargs['name'], limit)
		
	
		
		
		