import urllib
import string
import feedparser as feedparser
import sqlite3
import re

import headphones
from headphones import logger

def searchNZB(albumid=None):

	conn=sqlite3.connect(headphones.DB_FILE)
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
		
		logger.info(u"Searching for "+term+" since it was marked as wanted")
		
		resultlist = []
		
		if headphones.NZBMATRIX:

			if headphones.PREFER_LOSSLESS:
				categories = "23,22"
				maxsize = 2000000000
			else:
				categories = "22"
				maxsize = 250000000
			
			
			params = {	"page": "download",
						"username": headphones.NZBMATRIX_USERNAME,
						"apikey": headphones.NZBMATRIX_APIKEY,
						"subcat": categories,
						"age": headphones.USENET_RETENTION,
						"english": 1,
						"ssl": 1,
						"scenename": 1,
						"term": term
						}
						
			searchURL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)
			logger.info(u"Parsing results from "+searchURL)
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.info(title + u" is larger than the maxsize for this category, skipping. (Size: " + size+")")
						
				
				except:
					logger.info(u"No results found")
			
		if headphones.NEWZNAB:
		
			if headphones.PREFER_LOSSLESS:
				categories = "3040,3010"
				maxsize = 2000000000
			else:
				categories = "3010"
				maxsize = 250000000		

			params = {	"t": "search",
						"apikey": headphones.NEWZNAB_APIKEY,
						"cat": categories,
						"maxage": headphones.USENET_RETENTION,
						"q": term
						}
		
			searchURL = headphones.NEWZNAB_HOST + '/api?' + urllib.urlencode(params)
			logger.info(u"Parsing results from "+searchURL)
			
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.info(title + u" is larger than the maxsize for this category, skipping. (Size: " + size+")")
				
				except:
					logger.info(u"No results found")
					
		if headphones.NZBSORG:
		
			if headphones.PREFER_LOSSLESS:
				categories = "5,3010"
				maxsize = 2000000000
			else:
				categories = "5"
				maxsize = 250000000		

			params = {	"action": "search",
						"dl": 1,
						"catid": categories,
						"i": headphones.NZBSORG_UID,
						"h": headphones.NZBSORG_HASH,
						"age": headphones.USENET_RETENTION,
						"q": term
						}
		
			searchURL = 'https://secure.nzbs.org/rss.php?' + urllib.urlencode(params)
			
			logger.info(u"Parsing results from "+searchURL)
			d = feedparser.parse(searchURL)
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info(u"Found " + title +" : " + url + " (Size: " + size + ")")
					else:
						logger.info(title + u" is larger than the maxsize for this category, skipping. (Size: " + size +")")
						
				
				except:
					logger.info(u"No results found")
		
		if len(resultlist):	
			bestqual = sorted(resultlist, key=lambda title: title[1], reverse=True)[0]
		
			logger.info(u"Downloading: " + bestqual[0])
			downloadurl = bestqual[2]
				
			linkparams = {}
			
			linkparams["mode"] = "addurl"
			
			if headphones.SAB_APIKEY:
				linkparams["apikey"] = headphones.SAB_APIKEY
			if headphones.SAB_USERNAME:
				linkparams["ma_username"] = headphones.SAB_USERNAME
			if headphones.SAB_PASSWORD:
				linkparams["ma_password"] = headphones.SAB_PASSWORD
			if headphones.SAB_CATEGORY:
				linkparams["cat"] = headphones.SAB_CATEGORY
							
			linkparams["name"] = downloadurl
				
			saburl = 'http://' + headphones.SAB_HOST + '/sabnzbd/api?' + urllib.urlencode(linkparams)
			logger.info(u"Sending link to SABNZBD: " + saburl)
			
			try:
				urllib.urlopen(saburl)
				
			except:
				logger.error(u"Unable to send link. Are you sure the host address is correct?")
				
			c.execute('UPDATE albums SET status = "Snatched" WHERE AlbumID="%s"' % albums[2])
			c.execute('INSERT INTO snatched VALUES( ?, ?, ?, ?, CURRENT_DATE, ?)', (albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched"))
			conn.commit()
		
		else:
			pass
			
	c.close()
	