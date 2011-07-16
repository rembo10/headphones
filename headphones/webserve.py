import os, sys

import cherrypy

import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u

import time
import datetime
import threading

import headphones
from headphones.mb import getReleaseGroup
from headphones import templates, logger, searcher, db, importer, helpers, mb
from headphones.helpers import checked


class WebInterface(object):

	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		page = [templates._header]
		if not headphones.CURRENT_VERSION:
			page.append('''<div class="updatebar">You're running an unknown version of Heapdhones. <a class="blue" href="update">Click here to update</a></div>''')
		elif headphones.CURRENT_VERSION != headphones.LATEST_VERSION and headphones.INSTALL_TYPE != 'win':
			page.append('''<div class="updatebar">A <a class="blue" href="http://github.com/rembo10/headphones/compare/%s...%s">
					newer version</a> is available. You're %s commits behind. <a class="blue" href="update">Click here to update</a></div>
					''' % (headphones.CURRENT_VERSION, headphones.LATEST_VERSION, headphones.COMMITS_BEHIND))
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		results = myDB.select('SELECT ArtistName, ArtistID, Status from artists order by ArtistSortName collate nocase')
		if len(results):
			i = 0
			page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr>
						<th align="left" width="170">Artist Name</th>
						<th align="center" width="100">Status</th>
						<th align="center" width="300">Upcoming Albums</th>
						<th align="center">Have</th>
						</tr>''')
			while i < len(results):
				latestalbum = myDB.select('SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumID from albums WHERE ArtistID=? order by ReleaseDate DESC', [results[i][1]])
				totaltracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=?', [results[i][1]]))
				havetracks = len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [results[i][0]]))
				try:
					percent = (havetracks*100.0)/totaltracks
					if percent > 100:
						percent = 100
				except ZeroDivisionError:
					percent = 100
				today = datetime.date.today()
				if len(latestalbum) > 0:
					if latestalbum[0][1] > datetime.date.isoformat(today):
						newalbumName = '<a class="green" href="albumPage?AlbumID=%s"><i><b>%s</b></i>' % (latestalbum[0][3], latestalbum[0][0])
						releaseDate = '(%s)</a>' % latestalbum[0][1]
					else:
						newalbumName = '<a class="gray" href="albumPage?AlbumID=%s"><i>%s</i>' % (latestalbum[0][3], latestalbum[0][0])
						releaseDate = ""
				if len(latestalbum) == 0:
						newalbumName = '<font color="#CFCFCF">None</font>'
						releaseDate = ""					
				if results[i][2] == 'Paused':
					newStatus = '''<font color="red"><b>%s</b></font>(<A class="external" href="resumeArtist?ArtistID=%s">resume</a>)''' % (results[i][2], results[i][1])
				elif results[i][2] == 'Loading':
					newStatus = '''<a class="gray">Loading...</a>'''
				else:
					newStatus = '''%s(<A class="external" href="pauseArtist?ArtistID=%s">pause</a>)''' % (results[i][2], results[i][1])
				page.append('''<tr><td align="left" width="300"><a href="artistPage?ArtistID=%s">%s</a> 
								(<A class="external" href="http://musicbrainz.org/artist/%s">link</a>) [<A class="externalred" href="deleteArtist?ArtistID=%s">delete</a>]</td>
								<td align="center" width="160">%s</td>
								<td align="center">%s %s</td>
								<td><div class="progress-container"><div style="width: %s%%"></div></div></td></tr>
								''' % (results[i][1], results[i][0], results[i][1], results[i][1], newStatus, newalbumName, releaseDate, percent))	
				i = i+1

			page.append('''</table></div>''')
			page.append(templates._footer % headphones.CURRENT_VERSION)
			
		else:
			page.append("""<div class="datanil">Add some artists to the database!</div>""")
		return page
	home.exposed = True
	

	def artistPage(self, ArtistID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		
		results = myDB.select('SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])
		
		i = 0
		page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr><p align="center">%s <br /></p></tr>
						<tr>
						<th align="left" width="30"></th>
						<th align="left" width="120">Album Name</th>
						<th align="center" width="100">Release Date</th>
						<th align="center" width="180">Status</th>
						<th align="center">Have</th>
						</tr>''' % (results[0][4]))
		while i < len(results):
			totaltracks = len(myDB.select('SELECT TrackTitle from tracks WHERE AlbumID=?', [results[i][2]]))
			havetracks = len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ? AND AlbumTitle like ?', [results[i][4], results[i][0]]))
			try:
				percent = (havetracks*100)/totaltracks
				if percent > 100:
					percent = 100
			except ZeroDivisionError:
					percent = 100
			if results[i][3] == 'Skipped':
				newStatus = '''%s [<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">want</a>]''' % (results[i][3], results[i][2], ArtistID)
			elif results[i][3] == 'Wanted':
				newStatus = '''<b>%s</b>[<A class="external" href="unqueueAlbum?AlbumID=%s&ArtistID=%s">skip</a>]''' % (results[i][3], results[i][2], ArtistID)				
			elif results[i][3] == 'Downloaded':
				newStatus = '''<b>%s</b>[<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">retry</a>]''' % (results[i][3], results[i][2], ArtistID)
			elif results[i][3] == 'Snatched':
				newStatus = '''<b>%s</b>[<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">retry</a>]''' % (results[i][3], results[i][2], ArtistID)
			else:
				newStatus = '%s' % (results[i][3])
			page.append('''<tr><td align="left"><img src="http://ec1.images-amazon.com/images/P/%s.01.MZZZZZZZ.jpg" height="50" width="50"></td>
							<td align="left" width="240"><a href="albumPage?AlbumID=%s">%s</a> 
							(<A class="external" href="http://musicbrainz.org/release/%s.html">link</a>)</td>
							<td align="center" width="160">%s</td>
							<td align="center">%s</td>
							<td><div class="progress-container"><div style="width: %s%%"></div></div></td></tr>''' % (results[i][5], results[i][2], results[i][0], results[i][2], results[i][1], newStatus, percent))	
			i = i+1

		page.append('''</table></div>''')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		results = myDB.select('SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN from tracks WHERE AlbumID=?', [AlbumID])
		
		if results[0][6]:
			albumart = '''<br /><img src="http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg" height="200" width="200"><br /><br />''' % results[0][6]
		else:
			albumart = ''
		i = 0
		page.append('''<div class="table" align="center"><table border="0" cellpadding="3">
					<tr><a href="artistPage?ArtistID=%s">%s</a> - %s<br />
					<a href="queueAlbum?AlbumID=%s&ArtistID=%s">Download<br />%s</tr>
					<br /><tr>
					<th align="left" width="100">Track #</th>
					<th align="left" width="300">Track Title</th>
					<th align="center" width="100">Duration</th>
					<th>      </th>
					</tr>''' % (results[0][0], results[0][1], results[0][2], AlbumID, results[0][0], albumart))
		while i < len(results):
			trackmatches = myDB.select('SELECT TrackTitle from have WHERE ArtistName like ? AND AlbumTitle like ? AND TrackTitle like ?', [results[i][1], results[i][2], results[i][3]])

			if len(trackmatches):
				have = '<img src="images/checkmark.png" width="20px">'
			else:
				have = ''
			if results[i][4]:
				duration = helpers.convert_milliseconds(results[i][4])
			else:
				duration = 'n/a'
			page.append('''<tr><td align="left" width="120">%s</td>
							<td align="left" width="240">%s (<A class="external" href="http://musicbrainz.org/recording/%s.html">link</a>)</td>
							<td align="center">%s</td>
							<td>%s</td></tr>''' % (i+1, results[i][3], results[i][5], duration, have))	
			i = i+1

		page.append('''</table></div>''')
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	
	albumPage.exposed = True
	
	
	def findArtist(self, name):
	
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("home")
		else:
			artistResults = mb.findArtist(name, limit=10)
			if len(artistResults) == 0:
				logger.info(u"No results found for " + name)
				page.append('''<div class="table"><p class="center">No results! <a class="blue" href="home">Go back</a></p></div>''')
				return page
			elif len(artistResults) > 1:
				page.append('''<div class="table"><p class="center">Search returned multiple artists. Click the artist you want to add:</p>''')
				for result in artistResults:
					page.append('''<p class="mediumtext"><a href="addArtist?artistid=%s">%s</a> (<a class="externalred" href="artistInfo?artistid=%s">more info</a>)</p>''' % (result['id'], result['uniquename'], result['id']))
				page.append('''</div>''')
				return page
			else:
				for result in artistResults:
					logger.info(u"Found one artist matching your search term: " + result['name'] +" ("+ result['id']+")")			
					raise cherrypy.HTTPRedirect("addArtist?artistid=%s" % result['id'])
		
	findArtist.exposed = True

	def artistInfo(self, artistid):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		artist = mb.getArtist(artistid)
		page.append('''<div class="table"><p class="center">Artist Information:</p>''')
		page.append('''<p class="mediumtext">Artist Name: %s </br> ''' % artist['artist_name'])
		page.append('''Unique ID: %s </br></br>Albums:<br />''' % artist['artist_id'])
		for rg in artist['releasegroups']:
			page.append('''%s <br />''' % rg['title'])
		return page
		
	artistInfo.exposed = True

	def addArtist(self, artistid):
		
		threading.Thread(target=importer.addArtisttoDB, args=[artistid]).start()
		time.sleep(2)
		raise cherrypy.HTTPRedirect("home")
		
	addArtist.exposed = True
	
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
	
	def queueAlbum(self, AlbumID, ArtistID):

		logger.info(u"Marking album: " + AlbumID + "as wanted...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Wanted'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		import searcher
		searcher.searchNZB(AlbumID)
		
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
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		albums = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")

		wanted = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE Status='Wanted'")

		page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr>
						<th align="center" width="300"></th>
						<th align="center" width="300"><div class="bigtext">Upcoming Albums<br /><br /></div></th>
						<th align="center" width="300"></th>
						<th>      </th>
						</tr>''')
		if len(albums) == 0:
			page.append("""</table><div class="center">No albums are coming out soon :(<br />
							(try adding some more artists!)</div><table>""")

		i = 0
		while i < len(albums):
		
			if albums[i][3]:
				albumart = '''<br /><a href="http://www.amazon.com/dp/%s"><img src="http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg" height="200" width="200"></a><br /><br />''' % (albums[i][3], albums[i][3])
			else:
				albumart = 'No Album Art... yet.'

			page.append('''<tr><td align="center" width="300">%s</td>
								<td align="center" width="300"><a href="artistPage?ArtistID=%s">%s</a></td>
								<td align="center" width="300"><a href="albumPage?AlbumID=%s"><i>%s</i> (%s)</a></td></tr>
								''' % (albumart, albums[i][6], albums[i][5], albums[i][4], albums[i][0], albums[i][1]))
			i += 1
		page.append('''</table></div>''')
		if len(wanted):
			page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr>
						<th align="center" width="300"></th>
						<th align="center" width="300"><div class="bigtext">Wanted Albums<br /><br /></div></th>
						<th align="center" width="300"></th>
						<th>      </th>
						</tr>''')
			i = 0
			while i < len(wanted):
		
				if wanted[i][3]:
					albumart = '''<br /><a href="http://www.amazon.com/dp/%s"><img src="http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg" height="200" width="200"></a><br /><br />''' % (wanted[i][3], wanted[i][3])
				else:
					albumart = 'No Album Art... yet.'

				page.append('''<tr><td align="center" width="300">%s</td>
								<td align="center" width="300"><a href="artistPage?ArtistID=%s">%s</a></td>
								<td align="center" width="300"><a href="albumPage?AlbumID=%s"><i>%s</i> (%s)</a></td></tr>
								''' % (albumart, wanted[i][6], wanted[i][5], wanted[i][4], wanted[i][0], wanted[i][1]))
				i += 1
		page.append('''</table></div>''')
		if len(albums):
			page.append(templates._footer % headphones.CURRENT_VERSION)
		
		return page
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
						<tr>
						<th align="center" width="300"></th>
						<th align="center" width="300"><div class="bigtext">History <a class="external" href="clearhistory">clear all</a><br /><br /></div></th>
						<th align="center" width="300"></th>
						<th>      </th>
						</tr>''')
		if len(snatched) == 0:
			page.append("""</table><div class="center"></div><table>""")

		i = 0
		while i < len(snatched):
			mb = snatched[i][2] / 1048576
			size = '%.2fM' % mb
			page.append('''<tr><td align="center" width="300">%s</td>
								<td align="center" width="300">%s</td>
								<td align="center" width="300">%s</td>
								<td align="center" width="300">%s</td>
								</tr>
								''' % (snatched[i][5], snatched[i][1], size, snatched[i][4]))
			i += 1
		page.append('''</table></div>''')
		if len(snatched):
			page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	history.exposed = True
	
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
		checked(headphones.PREFER_LOSSLESS),
		checked(headphones.FLAC_TO_MP3),
		checked(headphones.MOVE_FILES),
		headphones.MUSIC_DIR,
		checked(headphones.RENAME_FILES),
		checked(headphones.CLEANUP_FILES),
		checked(headphones.ADD_ALBUM_ART)
		))
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
					
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None, blackhole=0, blackhole_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, prefer_lossless=0, flac_to_mp3=0, move_files=0, music_dir=None, rename_files=0, cleanup_files=0, add_album_art=0):
		
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
		headphones.PREFER_LOSSLESS = prefer_lossless
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
		page = [templates._shutdownheader % 10]
		page.append('Shutting down Headphones...')
		return page

	shutdown.exposed = True

	def restart(self):
		logger.info(u"Headphones is restarting...")
		threading.Timer(2, headphones.shutdown, [True]).start()
		page = [templates._shutdownheader % 20]
		page.append('Restarting Headphones...')
		return page
	 
	restart.exposed = True
	
	def update(self):
		logger.info('Headphones is updating...')
		threading.Timer(2, headphones.shutdown, [True, True]).start()
		page = [templates._shutdownheader % 60]
		page.append('Updating Headphones...')
		return page
		
	update.exposed = True