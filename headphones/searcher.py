import urllib
import string
import lib.feedparser as feedparser
import os, re

import headphones
from headphones import logger, db, helpers

def searchNZB(albumid=None):

	myDB = db.DBConnection()
	
	if albumid:
		results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted" AND AlbumID=?', [albumid])
	else:
		results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted"')
	
	for albums in results:
		
		albumid = albums[2]
		reldate = albums[3]
		year = reldate[:4]
		clname = string.replace(helpers.latinToAscii(albums[0]), ' & ', ' ')	
		clalbum = string.replace(helpers.latinToAscii(albums[1]), ' & ', ' ')
		term1 = re.sub('[\.\-]', ' ', '%s %s %s' % (clname, clalbum, year)).encode('utf-8')
		term = string.replace(term1, '"', '')
		
		logger.info("Searching for %s since it was marked as wanted" % term)
		
		resultlist = []
		
		if headphones.NZBMATRIX:

			if headphones.PREFERRED_QUALITY:
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
						logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
					else:
						logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))	
				
				except Exception, e:
					logger.info(u"No results found. %s" % e)
			
		if headphones.NEWZNAB:
		
			if headphones.PREFERRED_QUALITY:
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
			
			try:	
				d = feedparser.parse(searchURL)
			except Exception, e:
				logger.error('Error parsing data from ' + headphones.NEWZNAB_HOST + ' : ' + str(e))
			
			for item in d.entries:
				try:
					url = item.link
					title = item.title
					size = int(item.links[1]['length'])
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
					else:
						logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))	
				
				except Exception, e:
					logger.info(u"No results found. %s" % e)
					
		if headphones.NZBSORG:
		
			if headphones.PREFERRED_QUALITY:
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
					size = int(item.report_size)
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
					else:
						logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))	
				
				except Exception, e:
					logger.info(u"No results found. %s" % e)
		
		if len(resultlist):	
			
			if headphones.PREFERRED_QUALITY == 2 and headphones.PREFERRED_BITRATE:
				
				bestqual = helpers.sortNZBList(resultlist, albumid)
			
			else:
				bestqual = sorted(resultlist, key=lambda title: title[1], reverse=True)[0]
			
			logger.info(u"Found best result: %s (%s) - %s" % (bestqual[0], bestqual[2], helpers.bytes_to_mb(bestqual[1])))
			downloadurl = bestqual[2]
				
			if headphones.SAB_HOST and not headphones.BLACKHOLE:
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
				linkparams["nzbname"] = ('%s - %s [%s]' % (albums[0], albums[1], year))
					
				saburl = 'http://' + headphones.SAB_HOST + '/sabnzbd/api?' + urllib.urlencode(linkparams)
				logger.info(u"Sending link to SABNZBD: " + saburl)
				
				try:
					urllib.urlopen(saburl)
					
				except:
					logger.error(u"Unable to send link. Are you sure the host address is correct?")
					break
					
				myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [albums[2]])
				myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, CURRENT_DATE, ?)', [albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched"])

			
			elif headphones.BLACKHOLE:
			
				nzb_name = ('%s - %s [%s].nzb' % (albums[0], albums[1], year))
				download_path = os.path.join(headphones.BLACKHOLE_DIR, nzb_name)
				
				try:
					urllib.urlretrieve(downloadurl, download_path)
				except Exception, e:
					logger.error('Couldn\'t retrieve NZB: %s' % e)
					break
					
				myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [albums[2]])
				myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, CURRENT_DATE, ?)', [albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched"])

				
				
			
			
	