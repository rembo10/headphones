import os

import cherrypy
from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import time
import threading

import headphones
from headphones import templates, logger, db, importer, helpers, mb
from headphones.helpers import checked, radio

_hplookup = TemplateLookup(directories=[os.path.join(str(headphones.PROG_DIR), 'data/interfaces/default/')], output_encoding='utf-8')

def serve_template(templatename, **kwargs):
	try:
		template = _hplookup.get_template(templatename)
		kwargs['hpRoot'] = headphones.HTTP_ROOT
		return template.render(**kwargs)
	except:
		return exceptions.html_error_template().render()
	
class WebInterface(object):
	
	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		myDB = db.DBConnection()
		results = myDB.select('SELECT ArtistName, ArtistID, Status, LatestAlbum, ReleaseDate, AlbumID, TotalTracks, HaveTracks from artists order by ArtistSortName COLLATE NOCASE')
		return serve_template(templatename="index.html", title='Home', artists=results)
	home.exposed = True
	

	def artistPage(self, ArtistID):
		myDB = db.DBConnection()
		
		artist = myDB.action('SELECT ArtistName, IncludeExtras FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
		albums = myDB.select('SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])

		return serve_template(templatename="artist.html", title=artist['ArtistName'], artist=artist, albums=albums, artistID=ArtistID)
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):

		myDB = db.DBConnection()
		
		album = myDB.action('SELECT * FROM albums WHERE AlbumID=?', [AlbumID]).fetchone()
		tracks = myDB.select('SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN FROM tracks WHERE AlbumID=?', [AlbumID])
		
		return serve_template(templatename="album.html", title=album['AlbumTitle'],tracks=tracks, album=album)
	
	albumPage.exposed = True
	
	
	def findArtist(self, name):

		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("home")
		else:
			artistResults = mb.findArtist(name, limit=10)
			if len(artistResults) == 1:
				logger.info(u"Found one artist matching your search term: " + artistResults[0]['name'] +" ("+ artistResults[0]['id']+")")			
				raise cherrypy.HTTPRedirect("addArtist?artistid=%s" % artistResults[0]['id'])
		return serve_template(templatename="artistsearch.html", title="Search", results=artistResults)
	findArtist.exposed = True

	def artistInfo(self, artistid):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		artist = mb.getArtist(artistid)
		if artist['artist_begindate']:
			begindate = artist['artist_begindate']
		else:
			begindate = ''
		if artist['artist_enddate']:
			enddate = artist['artist_enddate']
		else:
			enddate = ''
		page.append('''<div class="table"><p class="center">Artist Information:</p>''')
		page.append('''<p class="mediumtext">Artist Name: %s (%s)</br> ''' % (artist['artist_name'], artist['artist_type']))
		page.append('''<p class="mediumtext">Years Active: %s - %s <br /><br />''' % (begindate, enddate))
		page.append('''MusicBrainz Link: <a class="external" href="http://www.musicbrainz.org/artist/%s">http://www.musicbrainz.org/artist/%s</a></br></br><b>Albums:</b><br />''' % (artistid, artistid))
		for rg in artist['releasegroups']:
			page.append('''%s <br />''' % rg['title'])
		page.append('''<div class="center"><a href="addArtist?artistid=%s">Add this artist!</a></div>''' % artistid)
		return page
		
	artistInfo.exposed = True

	def addArtist(self, artistid):
		
		threading.Thread(target=importer.addArtisttoDB, args=[artistid]).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
		
	addArtist.exposed = True
	
	def getExtras(self, ArtistID):
		
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'IncludeExtras': 1}
		myDB.upsert("artists", newValueDict, controlValueDict)
		
		threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, True]).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		
	getExtras.exposed = True
	
	def pauseArtist(self, ArtistID):
	
		logger.info(u"Pausing artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Paused'}
		myDB.upsert("artists", newValueDict, controlValueDict)
		
		raise cherrypy.HTTPRedirect("home")
		
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):

		logger.info(u"Resuming artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Active'}
		myDB.upsert("artists", newValueDict, controlValueDict)

		raise cherrypy.HTTPRedirect("home")
		
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):

		logger.info(u"Deleting all traces of artist: " + ArtistID)
		myDB = db.DBConnection()
		myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

		raise cherrypy.HTTPRedirect("home")
		
	deleteArtist.exposed = True
	
	def queueAlbum(self, AlbumID, ArtistID, new=False):

		logger.info(u"Marking album: " + AlbumID + "as wanted...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Wanted'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		import searcher
		searcher.searchNZB(AlbumID, new)
		
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		
	queueAlbum.exposed = True

	def unqueueAlbum(self, AlbumID, ArtistID):

		logger.info(u"Marking album: " + AlbumID + "as skipped...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Skipped'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		
	unqueueAlbum.exposed = True
	
	def upcoming(self):
		myDB = db.DBConnection()

		upcoming = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")
		wanted = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE Status='Wanted'")
		
		return serve_template(templatename="upcoming.html", title="Upcoming Albums", upcoming=upcoming, wanted=wanted)
	upcoming.exposed = True
	
	def manage(self):
		if headphones.PATH_TO_XML:
			path = headphones.PATH_TO_XML
		else:
			path = 'Absolute path to iTunes XML or Top-Level Music Directory'
		if headphones.MUSIC_DIR:
			path2 = headphones.MUSIC_DIR
		else:
			path2 = 'Enter a directory to scan'
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append('''
		<div class="table"><div class="config"><h1>Scan Music Library</h1><br />
		Where do you keep your music?<br /><br />
		You can put in any directory, and it will scan for audio files in that folder
		(including all subdirectories)<br /><br />		For example: '/Users/name/Music'
		<br /> <br />
		It may take a while depending on how many files you have. You can navigate away from the page<br />
		as soon as you click 'Submit'
		<br /><br />

		<form action="musicScan" method="GET" align="center">
			<input type="text" value="%s" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="path" size="70" />
			<input type="submit" /></form><br /><br /></div></div>
		<div class="table"><div class="config"><h1>Import or Sync Your iTunes Library/Music Folder</h1><br />
		This is here for legacy purposes (try the Music Scanner above!) <br /><br />
		If you'd rather import an iTunes .xml file, you can enter the full path here. <br /><br />
		<form action="importItunes" method="GET" align="center">
			<input type="text" value="%s" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="path" size="70" />
			<input type="submit" /></form><br /><br /></div></div>
			<div class="table"><div class="config"><h1>Force Search</h1><br />
			<a href="forceSearch">Force Check for Wanted Albums</a><br /><br />
			<a href="forceUpdate">Force Update Active Artists</a><br /><br />
			<a href="checkGithub">Check for Headphones Updates</a><br /><br /><br /></div></div>''' % (path2, path))
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	manage.exposed = True
	
	def importItunes(self, path):
		headphones.PATH_TO_XML = path
		headphones.config_write()
		threading.Thread(target=importer.itunesImport, args=[path]).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("home")
	importItunes.exposed = True
	
	def musicScan(self, path):
		headphones.MUSIC_DIR = path
		headphones.config_write()
		try:	
			threading.Thread(target=importer.scanMusic, args=[path]).start()
		except Exception, e:
			logger.error('Unable to complete the scan: %s' % e)
		time.sleep(10)
		raise cherrypy.HTTPRedirect("home")
	musicScan.exposed = True
	
	def forceUpdate(self):
		from headphones import updater
		threading.Thread(target=updater.dbUpdate).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forceUpdate.exposed = True
	
	def forceSearch(self):
		from headphones import searcher
		threading.Thread(target=searcher.searchNZB).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forceSearch.exposed = True
	
	def checkGithub(self):
		from headphones import versioncheck
		versioncheck.checkGithub()
		raise cherrypy.HTTPRedirect("home")
	checkGithub.exposed = True
	
	def history(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		snatched = myDB.select('''SELECT AlbumID, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT from snatched order by DateAdded DESC''')

		page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr><p align="center">History <a class="external" href="clearhistory">clear all</a><br /><br /></p></tr>
						<tr>
						<th align="center" width="150"></th>
						<th align="center" width="300"></th>
						<th align="center" width="200"></th>
						<th align="right" width="200"></th>
						</tr>''')
		if len(snatched) == 0:
			page.append("""</table><div class="center"></div><table>""")

		i = 0
		while i < len(snatched):
			mb = snatched[i][2] / 1048576
			size = '%.2fM' % mb
			page.append('''<tr><td align="center" width="150">%s</td>
								<td align="center" width="300">%s</td>
								<td align="center" width="200">%s</td>
								<td align="center" width="200">%s</td>
								</tr>
								''' % (snatched[i][5], snatched[i][1], size, snatched[i][4]))
			i += 1
		page.append('''</table></div>''')
		if len(snatched):
			page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	history.exposed = True
	
	def logs(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append('''<div class="table"><p class="logtext">''')
		if os.path.isfile(os.path.join(headphones.LOG_DIR, 'headphones.log')):
			fileHandle = open(os.path.join(headphones.LOG_DIR, 'headphones.log'))
			lineList = fileHandle.readlines()
			fileHandle.close()
			i = -1
			if len(lineList) < 100:
				limit = -len(lineList)
			else:
				limit = -100
			while i > limit:
				page.append(lineList[i] + '<br /><br />')
				i -= 1
		page.append('''</p></div>''')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	
	logs.exposed = True
	
	def clearhistory(self):

		logger.info(u"Clearing history")
		myDB = db.DBConnection()
		myDB.action('''DELETE from snatched''')

		raise cherrypy.HTTPRedirect("history")
	clearhistory.exposed = True
	
	def config(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append(templates.configform % (
		headphones.HTTP_HOST,
		headphones.HTTP_USERNAME,
		headphones.HTTP_PORT,
		headphones.HTTP_PASSWORD,
		checked(headphones.LAUNCH_BROWSER),
		headphones.SAB_HOST,
		headphones.SAB_USERNAME,
		headphones.SAB_APIKEY,
		headphones.SAB_PASSWORD,
		headphones.SAB_CATEGORY,
		headphones.DOWNLOAD_DIR,
		checked(headphones.BLACKHOLE),
		headphones.BLACKHOLE_DIR,
		headphones.USENET_RETENTION,
		checked(headphones.NZBMATRIX),
		headphones.NZBMATRIX_USERNAME,
		headphones.NZBMATRIX_APIKEY,
		checked(headphones.NEWZNAB),
		headphones.NEWZNAB_HOST,
		headphones.NEWZNAB_APIKEY,
		checked(headphones.NZBSORG),
		headphones.NZBSORG_UID,
		headphones.NZBSORG_HASH,
		radio(headphones.PREFERRED_QUALITY, 0),
		radio(headphones.PREFERRED_QUALITY, 1),
		radio(headphones.PREFERRED_QUALITY, 3),
		radio(headphones.PREFERRED_QUALITY, 2),
		headphones.PREFERRED_BITRATE,
		checked(headphones.DETECT_BITRATE),
		checked(headphones.MOVE_FILES),
		checked(headphones.FLAC_TO_MP3),
		checked(headphones.RENAME_FILES),
		checked(headphones.CLEANUP_FILES),
		checked(headphones.ADD_ALBUM_ART),
		headphones.MUSIC_DIR
		))
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
					
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None, blackhole=0, blackhole_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, preferred_quality=0, preferred_bitrate=None, detect_bitrate=0, flac_to_mp3=0, move_files=0, music_dir=None, rename_files=0, cleanup_files=0, add_album_art=0):
		
		headphones.HTTP_HOST = http_host
		headphones.HTTP_PORT = http_port
		headphones.HTTP_USERNAME = http_username
		headphones.HTTP_PASSWORD = http_password
		headphones.LAUNCH_BROWSER = launch_browser
		headphones.SAB_HOST = sab_host
		headphones.SAB_USERNAME = sab_username
		headphones.SAB_PASSWORD = sab_password		
		headphones.SAB_APIKEY = sab_apikey
		headphones.SAB_CATEGORY = sab_category
		headphones.DOWNLOAD_DIR = download_dir
		headphones.BLACKHOLE = blackhole
		headphones.BLACKHOLE_DIR = blackhole_dir
		headphones.USENET_RETENTION = usenet_retention
		headphones.NZBMATRIX = nzbmatrix
		headphones.NZBMATRIX_USERNAME = nzbmatrix_username
		headphones.NZBMATRIX_APIKEY = nzbmatrix_apikey
		headphones.NEWZNAB = newznab
		headphones.NEWZNAB_HOST = newznab_host
		headphones.NEWZNAB_APIKEY = newznab_apikey
		headphones.NZBSORG = nzbsorg
		headphones.NZBSORG_UID = nzbsorg_uid
		headphones.NZBSORG_HASH = nzbsorg_hash
		headphones.PREFERRED_QUALITY = int(preferred_quality)
		headphones.PREFERRED_BITRATE = preferred_bitrate
		headphones.DETECT_BITRATE = detect_bitrate
		headphones.FLAC_TO_MP3 = flac_to_mp3
		headphones.MOVE_FILES = move_files
		headphones.MUSIC_DIR = music_dir
		headphones.RENAME_FILES = rename_files
		headphones.CLEANUP_FILES = cleanup_files
		headphones.ADD_ALBUM_ART = add_album_art
		
		headphones.config_write()

		raise cherrypy.HTTPRedirect("config")
		
	configUpdate.exposed = True

	def shutdown(self):
		logger.info(u"Headphones is shutting down...")
		threading.Timer(2, headphones.shutdown).start()
		page = [templates._shutdownheader % 15]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append('<div class="table"><div class="configtable">Shutting down Headphones...</div></div>')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page

	shutdown.exposed = True

	def restart(self):
		logger.info(u"Headphones is restarting...")
		threading.Timer(2, headphones.shutdown, [True]).start()
		page = [templates._shutdownheader % 30]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append('<div class="table"><div class="configtable">Restarting Headphones...</div></div>')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	 
	restart.exposed = True
	
	def update(self):
		logger.info('Headphones is updating...')
		threading.Timer(2, headphones.shutdown, [True, True]).start()
		page = [templates._shutdownheader % 120]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append('<div class="table"><div class="configtable">Updating Headphones...</div></div>')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
		
	update.exposed = True