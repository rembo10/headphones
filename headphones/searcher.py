import urllib
import lib.feedparser as feedparser
from xml.dom import minidom
import os, re

import headphones
from headphones import logger, db, helpers

def searchNZB(albumid=None, new=False):

	myDB = db.DBConnection()
	
	if albumid:
		results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted" AND AlbumID=?', [albumid])
	else:
		results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted"')
		new = True
		
	for albums in results:
		
		albumid = albums[2]
		reldate = albums[3]
		
		try:
			year = reldate[:4]
		except TypeError:
			year = ''
		
		dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '!':'', ' + ':' ', '"':'', ',':''}

		cleanartistalbum = helpers.latinToAscii(helpers.replace_all(albums[0]+' '+albums[1], dic))

		# FLAC usually doesn't have a year for some reason so I'll leave it out:
		term = re.sub('[\.\-]', ' ', '%s' % (cleanartistalbum)).encode('utf-8')
		altterm = re.sub('[\.\-]', ' ', '%s %s' % (cleanartistalbum, year)).encode('utf-8')
		
		# Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
		if albums[0] in albums[1] or len(albums[0]) < 4 or len(albums[1]) < 4:
			term = altterm	
		
		logger.info("Searching for %s since it was marked as wanted" % term)
		
		resultlist = []
		
		if headphones.NZBMATRIX:

			if headphones.PREFERRED_QUALITY == 3:
				categories = "23"
				maxsize = 10000000000	
			elif headphones.PREFERRED_QUALITY:
				categories = "23,22"
				maxsize = 2000000000
			else:
				categories = "22"
				maxsize = 300000000
			
			
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
				
				except AttributeError, e:
					logger.info(u"No results found from NZBMatrix for %s" % term)
			
		if headphones.NEWZNAB:
		
			if headphones.PREFERRED_QUALITY == 3:
				categories = "3040"
				maxsize = 10000000000
			elif headphones.PREFERRED_QUALITY:
				categories = "3040,3010"
				maxsize = 2000000000
			else:
				categories = "3010"
				maxsize = 300000000		

			params = {	"t": "search",
						"apikey": headphones.NEWZNAB_APIKEY,
						"cat": categories,
						"maxage": headphones.USENET_RETENTION,
						"q": term
						}
		
			searchURL = headphones.NEWZNAB_HOST + '/api?' + urllib.urlencode(params)
			logger.info(u"Parsing results from "+searchURL)
				
			d = feedparser.parse(searchURL)
			
			if not len(d.entries):
				logger.info(u"No results found from %s for %s" % (headphones.NEWZNAB_HOST, term))
				pass
			
			else:
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
						logger.error(u"An unknown error occured trying to parse the feed: %s" % e)
					
		if headphones.NZBSORG:
		
			if headphones.PREFERRED_QUALITY == 3:
				categories = "5"
				maxsize = 10000000000
				term = term + ' flac'
			elif headphones.PREFERRED_QUALITY:
				categories = "5"
				maxsize = 2000000000
			else:
				categories = "5"
				maxsize = 300000000		

			params = {	"action": "search",
						"dl": 1,
						"catid": categories,
						"i": headphones.NZBSORG_UID,
						"h": headphones.NZBSORG_HASH,
						"age": headphones.USENET_RETENTION,
						"q": term
						}
		
			searchURL = 'https://secure.nzbs.org/rss.php?' + urllib.urlencode(params)
			
			data = urllib.urlopen(searchURL).read()
			
			logger.info(u"Parsing results from "+searchURL)
			d = minidom.parseString(data)

			node = d.documentElement
			items = d.getElementsByTagName("item")
			
			if len(items):
			
				for item in items:
		
					sizenode = item.getElementsByTagName("report:size")[0].childNodes
					titlenode = item.getElementsByTagName("title")[0].childNodes
					linknode = item.getElementsByTagName("link")[0].childNodes
	
					for node in sizenode:
						size = int(node.data)
					for node in titlenode:
						title = node.data
					for node in linknode:
						url = node.data
	
					if size < maxsize:
						resultlist.append((title, size, url))
						logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
					else:
						logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))	
				
			else:
			
				logger.info('No results found from NZBs.org for %s' % term)
		
		if len(resultlist):	
			
			if headphones.PREFERRED_QUALITY == 2 and headphones.PREFERRED_BITRATE:

				logger.debug('Target bitrate: %s kbps' % headphones.PREFERRED_BITRATE)

				tracks = myDB.select('SELECT TrackDuration from tracks WHERE AlbumID=?', [albumid])

				try:
					albumlength = sum([pair[0] for pair in tracks])
					logger.debug('Album length = %s' % albumlength)
					targetsize = albumlength/1000 * int(headphones.PREFERRED_BITRATE) * 128
					logger.info('Target size: %s' % helpers.bytes_to_mb(targetsize))
	
					newlist = []

					for result in resultlist:
						delta = abs(targetsize - result[1])
						newlist.append((result[0], result[1], result[2], delta))
		
					nzblist = sorted(newlist, key=lambda title: title[3])
				
				except Exception, e:
					
					logger.debug('Error: %s' % str(e))
					logger.info('No track information for %s - %s. Defaulting to highest quality' % (albums[0], albums[1]))
					
					nzblist = sorted(resultlist, key=lambda title: title[1], reverse=True)
			
			else:
			
				nzblist = sorted(resultlist, key=lambda title: title[1], reverse=True)
			
			
			if new:
				# Checks to see if it's already downloaded
				i = 0
	
				while i < len(nzblist):
					alreadydownloaded = myDB.select('SELECT * from snatched WHERE URL=?', [nzblist[i][2]])
					
					if len(alreadydownloaded) >= 1:
						logger.info('%s has already been downloaded. Skipping.' % nzblist[i][0])
						i += 1
					
					else:
						bestqual = nzblist[i]
						break
						
				try:
					x = bestqual[0]
				except UnboundLocalError:
					logger.info('No more matches for %s' % term)
					return
						
			else:
				bestqual = nzblist[0]
			
			
			logger.info(u"Found best result: %s (%s) - %s" % (bestqual[0], bestqual[2], helpers.bytes_to_mb(bestqual[1])))
			
			downloadurl = bestqual[2]
			nzb_folder_name = '%s - %s [%s]' % (helpers.latinToAscii(albums[0]).encode('UTF-8'), helpers.latinToAscii(albums[1]).encode('UTF-8'), year)

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

				linkparams["nzbname"] = nzb_folder_name
					
				saburl = 'http://' + headphones.SAB_HOST + '/sabnzbd/api?' + urllib.urlencode(linkparams)
				logger.info(u"Sending link to SABNZBD: " + saburl)
				
				try:
					urllib.urlopen(saburl)
					
				except:
					logger.error(u"Unable to send link. Are you sure the host address is correct?")
					break
					
				myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [albums[2]])
				myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?)', [albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched", nzb_folder_name])

			
			elif headphones.BLACKHOLE:
			
				nzb_name = nzb_folder_name + '.nzb'
				download_path = os.path.join(headphones.BLACKHOLE_DIR, nzb_name)
				
				try:
					urllib.urlretrieve(downloadurl, download_path)
				except Exception, e:
					logger.error('Couldn\'t retrieve NZB: %s' % e)
					break
					
				myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [albums[2]])
				myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?)', [albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched", nzb_folder_name])