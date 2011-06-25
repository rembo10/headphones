import urllib
from webServer import database
from headphones import config_file
from configobj import ConfigObj
import string
import feedparser
import sqlite3
import re
import logger


config = ConfigObj(config_file)
General = config['General']
NZBMatrix = config['NZBMatrix']
SABnzbd = config['SABnzbd']
Newznab = config['Newznab']
NZBsorg = config['NZBsorg']
usenet_retention = General['usenet_retention']
include_lossless = General['include_lossless']
nzbmatrix = NZBMatrix['nzbmatrix']
nzbmatrix_username = NZBMatrix['nzbmatrix_username']
nzbmatrix_apikey = NZBMatrix['nzbmatrix_apikey']
newznab = Newznab['newznab']
newznab_host = Newznab['newznab_host']
newznab_apikey = Newznab['newznab_apikey']
nzbsorg = NZBsorg['nzbsorg']
nzbsorg_uid = NZBsorg['nzbsorg_uid']
nzbsorg_hash = NZBsorg['nzbsorg_hash']
sab_host = SABnzbd['sab_host']
sab_username = SABnzbd['sab_username']
sab_password = SABnzbd['sab_password']
sab_apikey = SABnzbd['sab_apikey']
sab_category = SABnzbd['sab_category']



def searchNZB(albumid=None):

	conn=sqlite3.connect(database)
	c=conn.cursor()
	
	if albumid:
		c.execute('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted" AND AlbumID="%s"' % albumid)
	else:
		c.execute('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted"')
	
	results = c.fetchall()
	
	for albums in results:
		
		reldate = albums[3]
		year = reldate[:4]
		clname = string.replace(albums[0], ' & ', ' ')	
		clalbum = string.replace(albums[1], ' & ', ' ')
		term1 = re.sub('[\.\-]', ' ', '%s %s %s' % (clname, clalbum, year)).encode('utf-8')
		term = string.replace(term1, '"', '')
		
		logger.log(u"Searching for "+term+" since it was marked as wanted")
		
		resultlist = []
		
		if nzbmatrix == '1':

			if include_lossless == '1':
				categories = "23,22"
				maxsize = 2000000000
			else:
				categories = "22"
				maxsize = 250000000
			
			
			params = {	"page": "download",
						"username": nzbmatrix_username,
						"apikey": nzbmatrix_apikey,
						"subcat": categories,
						"age": usenet_retention,
						"english": 1,
						"ssl": 1,
						"scenename": 1,
						"term": term
						}
						
			searchURL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)
			logger.log(u"Parsing results from "+searchURL)
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.log(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.log(title + u" is larger than the maxsize for this category, skipping. (Size: " + size+")", logger.WARNING)
						
				
				except:
					logger.log(u"No results found", logger.WARNING)
			
		if newznab == '1':
		
			if include_lossless == '1':
				categories = "3040,3010"
				maxsize = 2000000000
			else:
				categories = "3010"
				maxsize = 250000000		

			params = {	"t": "search",
						"apikey": newznab_apikey,
						"cat": categories,
						"maxage": usenet_retention,
						"q": term
						}
		
			searchURL = newznab_host + '/api?' + urllib.urlencode(params)
			logger.log(u"Parsing results from "+searchURL)
			
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.log(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.log(title + u" is larger than the maxsize for this category, skipping. (Size: " + size+")", logger.WARNING)
				
				except:
					logger.log(u"No results found", logger.WARNING)
					
		if nzbsorg == '1':
		
			if include_lossless == '1':
				categories = "5,3010"
				maxsize = 2000000000
			else:
				categories = "5"
				maxsize = 250000000		

			params = {	"action": "search",
						"dl": 1,
						"i": nzbsorg_uid,
						"h": nzbsorg_hash,
						"age": usenet_retention,
						"q": term
						}
		
			searchURL = 'https://secure.nzbs.org/rss.php?' + urllib.urlencode(params)
			
			logger.log(u"Parsing results from "+searchURL)
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.log(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.log(title + u" is larger than the maxsize for this category, skipping. (Size: " + size +")", logger.WARNING)
						
				
				except:
					logger.log(u"No results found", logger.WARNING)
		
		if len(resultlist):	
			bestqual = sorted(resultlist, key=lambda title: title[1], reverse=True)[0]
		
			logger.log(bestqual[0] + u" seems to be the best quality at: " + bestqual[1])
			downloadurl = bestqual[2]
				
			linkparams = {}
			
			linkparams["mode"] = "addurl"
			
			if sab_apikey != '':
				linkparams["apikey"] = sab_apikey
			if sab_username != '':
				linkparams["ma_username"] = sab_username
			if sab_password != '':
				linkparams["ma_password"] = sab_password
			if sab_category != '':
				linkparams["cat"] = sab_category
							
			linkparams["name"] = downloadurl
				
			saburl = 'http://' + sab_host + '/sabnzbd/api?' + urllib.urlencode(linkparams)
			logger.log(u"Sending link to SABNZBD: " + saburl)
			
			try:
				urllib.urlopen(saburl)
				
			except:
				logger.log(u"Unable to send link. Are you sure the host address is correct?", logger.ERROR)
				
			c.execute('UPDATE albums SET status = "Snatched" WHERE AlbumID="%s"' % albums[2])
			c.execute('CREATE TABLE IF NOT EXISTS snatched (AlbumID, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT)')
			c.execute('INSERT INTO snatched VALUES( ?, ?, ?, ?, CURRENT_DATE, ?)', (albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched"))
			conn.commit()
		
		else:
			pass
			
	c.close()
	