import templates
import config
import cherrypy
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
import os
import string
import time
import datetime
import sqlite3
import sys
import configobj
from headphones import FULL_PATH, config_file
import logger
from Cheetah.Template import Template

database = os.path.join(FULL_PATH, 'headphones.db')

class Headphones:
	
	def __init__(self,templatePath):
		"""docstring for __init__"""
		self.templatePath = templatePath

	def index(self):
		
		filename = os.path.join(self.templatePath,"index.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		#Display Database if it exists:
		if os.path.exists(database):
			#logger.log(u"Loading artists from the database...")
			conn=sqlite3.connect(database)
			c=conn.cursor()
			c.execute('SELECT ArtistName, ArtistID, Status from artists order by ArtistSortName collate nocase')
			results = c.fetchall()
			i = 0
			template.artists = []
			while i < len(results):
				c.execute('''SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumID from albums WHERE ArtistID='%s' order by ReleaseDate DESC''' % results[i][1])
				latestalbum = c.fetchall()
				today = datetime.date.today()
				if len(latestalbum) == 0:
					results[i][3] = '<font color="#CFCFCF">None</font>'
					results[i][4] = ""
				elif latestalbum[0][1] > datetime.date.isoformat(today):
					results[i][3] = '<font color="#5DFC0A" size="3px"><a href="albumPage?AlbumID=%s"><i>%s</i>' % (latestalbum[0][3], latestalbum[0][0])
					results[i][4] = '(%s)</a></font>' % latestalbum[0][1]
					
				template.artists.append(results[i])
				i = i+1
			c.close()
		return str(template)
	index.exposed = True

	def artistPage(self, ArtistID):
		filename = os.path.join(self.templatePath,"artistPage.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		template.artistID = ArtistID
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('''SELECT ArtistName from artists WHERE ArtistID="%s"''' % ArtistID)
		artistname = c.fetchall()
		template.artistName = artistname[0]
		c.execute('''SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID="%s" order by ReleaseDate DESC''' % ArtistID)
		results = c.fetchall()
		c.close()
		i = 0
		template.albums = []
		while i < len(results):
			template.albums.append(results[i])
			i = i+1
		return str(template)
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):
		
		filename = os.path.join(self.templatePath,"albumPage.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('''SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN from tracks WHERE AlbumID="%s"''' % AlbumID)
		results = c.fetchall()
		c.close()
		template.albumASIN = results[0][6]
		template.artistID = results[0][0]
		template.artistName = results[0][1]
		template.albumTitle = results[0][2]
		template.tracks = []
		i = 0
		while i < len(results):
			track = list(results[i])
			track.append(i+1)
			template.tracks.append(track)
			i = i+1

		return str(template)
	albumPage.exposed = True
	
	
	def findArtist(self, name):
	
		page = [templates._header]
		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("/")
		else:
			artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&', '%38'), limit=8))
			if len(artistResults) == 0:
				logger.log(u"No results found for " + name)
				page.append('''No results!<a class="blue" href="/">Go back</a>''')
				return page
			elif len(artistResults) > 1:
				page.append('''Search returned multiple artists. Click the artist you want to add:<br /><br />''')
				for result in artistResults:
					artist = result.artist
					page.append('''<a href="/addArtist?artistid=%s">%s</a> (<a class="externalred" href="/artistInfo?artistid=%s">more info</a>)<br />''' % (u.extractUuid(artist.id), artist.name, u.extractUuid(artist.id)))
				return page
			else:
				for result in artistResults:
					artist = result.artist
					logger.log(u"Found one artist matching your search term: " + artist.name +" ("+ artist.id+")")			
					raise cherrypy.HTTPRedirect("/addArtist?artistid=%s" % u.extractUuid(artist.id))
		
	findArtist.exposed = True

	def artistInfo(self, artistid):
		
		filename = os.path.join(self.templatePath,"artistInfo.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		artist = ws.Query().getArtistById(artistid, inc)
		template.artistName = artist.name
		template.artistUuid = artistid
		template.releaseGroups = artist.getReleaseGroups()
		return str(template)
	artistInfo.exposed = True

	def addArtist(self, artistid):
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=False)
		artist = ws.Query().getArtistById(artistid, inc)
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT)')
		c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
		c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT)')
		c.execute('SELECT ArtistID from artists')
		artistlist = c.fetchall()
		if any(artistid in x for x in artistlist):
			page = [templates._header]
			page.append('''%s has already been added. Go <a href="/">back</a>.''' % artist.name)
			logger.log(artist.name + u" is already in the database!", logger.WARNING)
			c.close()
			return page
		
		else:
			logger.log(u"Adding " + artist.name + " to the database.")
			c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
			
			for release in artist.getReleases():
				releaseid = u.extractUuid(release.id)
				inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
				results = ws.Query().getReleaseById(releaseid, inc)
				time.sleep(0.6)
				
				for event in results.releaseEvents:
					if event.country == 'US':
						logger.log(u"Now adding album: " + results.title+ " to the database")
						c.execute('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', (artistid, results.artist.name, results.title, results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id), 'Skipped'))
						c.execute('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID="%s"' % u.extractUuid(results.id))
						latestrelease = c.fetchall()
						
						if latestrelease[0][0] > latestrelease[0][1]:
							logger.log(results.title + u" is an upcoming album. Setting its status to 'Wanted'...")
							c.execute('UPDATE albums SET Status = "Wanted" WHERE AlbumID="%s"' % u.extractUuid(results.id))
						else:
							pass
						
						for track in results.tracks:
							c.execute('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', (artistid, results.artist.name, results.title, results.asin, u.extractUuid(results.id), track.title, track.duration, u.extractUuid(track.id)))
					else:
						logger.log(results.title + " is not a US release. Skipping it for now", logger.DEBUG)
			
			conn.commit()
			c.close()
			raise cherrypy.HTTPRedirect("/")
		
		
	addArtist.exposed = True
	
		#page for pausing an artist
	def pauseArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		logger.log(u"Pausing artist: " + ArtistID)
		c.execute('UPDATE artists SET status = "Paused" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/")
		
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		logger.log(u"Resuming artist: " + ArtistID)
		c.execute('UPDATE artists SET status = "Active" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/")
		
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		logger.log(u"Deleting all traces of artist: " + ArtistID)
		c.execute('''DELETE from artists WHERE ArtistID="%s"''' % ArtistID)
		c.execute('''DELETE from albums WHERE ArtistID="%s"''' % ArtistID)
		c.execute('''DELETE from tracks WHERE ArtistID="%s"''' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/")
		
	deleteArtist.exposed = True
	
	
	def queueAlbum(self, AlbumID, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		logger.log(u"Marking album: " + AlbumID + "as wanted...")
		c.execute('UPDATE albums SET status = "Wanted" WHERE AlbumID="%s"' % AlbumID)
		conn.commit()
		c.close()
		import searcher
		searcher.searchNZB(AlbumID)
		raise cherrypy.HTTPRedirect("/artistPage?ArtistID=%s" % ArtistID)

		
	queueAlbum.exposed = True

	def unqueueAlbum(self, AlbumID, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		logger.log(u"Marking album: " + AlbumID + "as skipped...")
		c.execute('UPDATE albums SET status = "Skipped" WHERE AlbumID="%s"' % AlbumID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/artistPage?ArtistID=%s" % ArtistID)
		
	unqueueAlbum.exposed = True
	
	def upcoming(self):
		filename = os.path.join(self.templatePath,"upcoming.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		return str(template)
	upcoming.exposed = True
	
	def manage(self):
		filename = os.path.join(self.templatePath,"manage.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		config = configobj.ConfigObj(config_file)
		try:
			path = config['General']['path_to_xml']
		except:
			path = 'Absolute path to iTunes XML or Top-Level Music Directory'
		template.path = path
		return str(template)
	manage.exposed = True
	
	def importItunes(self, path):
		config = configobj.ConfigObj(config_file)
		config['General']['path_to_xml'] = path
		config.write()
		import itunesimport
		itunesimport.itunesImport(path)
		raise cherrypy.HTTPRedirect("/")
	importItunes.exposed = True
	
	def forceUpdate(self):
		import updater
		updater.dbUpdate()
		raise cherrypy.HTTPRedirect("/")
	forceUpdate.exposed = True
	
	def forceSearch(self):
		import searcher
		searcher.searchNZB()
		raise cherrypy.HTTPRedirect("/")
	forceSearch.exposed = True
		
	
	def history(self):
		filename = os.path.join(self.templatePath,"history.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		return str(template)
	history.exposed = True
	
	def config(self):
		filename = os.path.join(self.templatePath,"config.tmpl")
		template = Template(file=filename)
		template.rootPath = "."
		template.appPath = "."
		return str(template)
	config.exposed = True
	
	
	def configUpdate(self, http_host='127.0.0.1', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, music_download_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, include_lossless=0,flac_to_mp3=0, move_to_itunes=0, path_to_itunes=None, rename_mp3s=0, cleanup=0, add_album_art=0):
		
		configs = configobj.ConfigObj(config_file)
		SABnzbd = configs['SABnzbd']
		General = configs['General']
		NZBMatrix = configs['NZBMatrix']	
		Newznab = configs['Newznab']
		NZBsorg = configs['NZBsorg']
		General['http_host'] = http_host
		General['http_port'] = http_port
		General['http_username'] = http_username
		General['http_password'] = http_password
		General['launch_browser'] = launch_browser
		SABnzbd['sab_host'] = sab_host
		SABnzbd['sab_username'] = sab_username
		SABnzbd['sab_password'] = sab_password		
		SABnzbd['sab_apikey'] = sab_apikey
		SABnzbd['sab_category'] = sab_category
		General['music_download_dir'] = music_download_dir
		General['usenet_retention'] = usenet_retention
		NZBMatrix['nzbmatrix'] = nzbmatrix
		NZBMatrix['nzbmatrix_username'] = nzbmatrix_username
		NZBMatrix['nzbmatrix_apikey'] = nzbmatrix_apikey
		Newznab['newznab'] = newznab
		Newznab['newznab_host'] = newznab_host
		Newznab['newznab_apikey'] = newznab_apikey
		NZBsorg['nzbsorg'] = nzbsorg
		NZBsorg['nzbsorg_uid'] = nzbsorg_uid
		NZBsorg['nzbsorg_hash'] = nzbsorg_hash
		General['include_lossless'] = include_lossless
		General['flac_to_mp3'] = flac_to_mp3
		General['move_to_itunes'] = move_to_itunes
		General['path_to_itunes'] = path_to_itunes
		General['rename_mp3s'] = rename_mp3s
		General['cleanup'] = cleanup
		General['add_album_art'] = add_album_art
		
		configs.write()
		reload(config)
		raise cherrypy.HTTPRedirect("/config")
		
		
	configUpdate.exposed = True

	def shutdown(self):
		sys.exit(0)

	shutdown.exposed = True
