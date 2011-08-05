import os

import cherrypy

import time
import threading

import headphones
from headphones.mb import getReleaseGroup
from headphones import templates, logger, searcher, db, importer, helpers, mb, lastfm
from headphones.helpers import checked, radio


class WebInterface(object):

	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		page = [templates._header]
		if not headphones.CURRENT_VERSION:
			page.append('''<div class="updatebar">You're running an unknown version of Headphones. <a class="blue" href="update">Click here to update</a></div>''')
		elif headphones.CURRENT_VERSION != headphones.LATEST_VERSION and headphones.INSTALL_TYPE != 'win':
			page.append('''<div class="updatebar">A <a class="blue" href="http://github.com/rembo10/headphones/compare/%s...%s">
					newer version</a> is available. You're %s commits behind. <a class="blue" href="update">Click here to update</a></div>
					''' % (headphones.CURRENT_VERSION, headphones.LATEST_VERSION, headphones.COMMITS_BEHIND))
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		results = myDB.select('SELECT ArtistName, ArtistID, Status, LatestAlbum, ReleaseDate, AlbumID, TotalTracks, HaveTracks from artists order by ArtistSortName collate nocase')
		if len(results):
			page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr>
						<th align="left" width="170">Artist Name</th>
						<th align="center" width="100">Status</th>
						<th align="center" width="300">Upcoming Albums</th>
						<th align="center">Have</th>
						</tr>''')
			for artist in results:
				totaltracks = artist['TotalTracks']
				havetracks = artist['HaveTracks']
				if not havetracks:
					havetracks = 0
				try:
					percent = (havetracks*100.0)/totaltracks
					if percent > 100:
						percent = 100
				except (ZeroDivisionError, TypeError):
					percent = 0
					totaltracks = '?'

				if artist['LatestAlbum']:
					if artist['ReleaseDate'] > helpers.today():
						newalbumName = '<a class="green" href="albumPage?AlbumID=%s"><i><b>%s</b></i>' % (artist['AlbumID'], artist['LatestAlbum'])
						releaseDate = '(%s)</a>' % artist['ReleaseDate']
					else:
						newalbumName = '<a class="gray" href="albumPage?AlbumID=%s"><i>%s</i>' % (artist['AlbumID'], artist['LatestAlbum'])
						releaseDate = ""
				else:
						newalbumName = '<font color="#CFCFCF">None</font>'
						releaseDate = ""					
				
				if artist['Status'] == 'Paused':
					newStatus = '''<font color="red"><b>%s</b></font>(<A class="external" href="resumeArtist?ArtistID=%s">resume</a>)''' % (artist['Status'], artist['ArtistID'])
				elif artist['Status'] == 'Loading':
					newStatus = '''<a class="gray">Loading...</a>'''
				else:
					newStatus = '''%s(<A class="external" href="pauseArtist?ArtistID=%s">pause</a>)''' % (artist['Status'], artist['ArtistID'])
				
				page.append('''<tr><td align="left" width="300"><a href="artistPage?ArtistID=%s">%s</a> 
								(<A class="external" href="http://musicbrainz.org/artist/%s">link</a>) [<A class="externalred" href="deleteArtist?ArtistID=%s">delete</a>]</td>
								<td align="center" width="160">%s</td>
								<td align="center">%s %s</td>
								<td><div class="progress-container"><div style="width: %s%%"><div class="smalltext3">%s/%s</div></div></div></td></tr>
								''' % (artist['ArtistID'], artist['ArtistName'], artist['ArtistID'], 
										artist['ArtistID'], newStatus, newalbumName, releaseDate, 
										percent, havetracks, totaltracks))	

			page.append('''</table></div>''')
			page.append(templates._footer % headphones.CURRENT_VERSION)
			
		else:
			have = myDB.select('SELECT ArtistName from have')
			if len(have):
				page.append("""<div class="datanil">Scanning...</div>""")
			else:
				page.append("""<div class="datanil">Add some artists to the database!</div>""")
		return page
	home.exposed = True
	

	def artistPage(self, ArtistID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		myDB = db.DBConnection()
		
		artist = myDB.select('SELECT ArtistName, IncludeExtras, Status from artists WHERE ArtistID=?', [ArtistID])
		while not artist:
			time.sleep(1)
		page.append('''<div class="table"><table><p align="center">%s</p>
						''' % artist[0][0])
		if artist[0][2] == 'Loading':
			page.append('<p align="center"><i>Loading...</i></p>')
		
		if templates.displayAlbums(ArtistID, 'Album'):
			page.append(templates.displayAlbums(ArtistID, 'Album'))
		
		releasetypes = ['Compilation', 'EP', 'Single', 'Live', 'Remix']
		
		for type in releasetypes:
			if templates.displayAlbums(ArtistID, type):
				page.append(templates.displayAlbums(ArtistID, type))
				
		page.append('</table>')
		
		if not artist[0][1]:
			page.append('''<br /><div class="bluecenter"><a href="getExtras?ArtistID=%s">Get Extras for %s!</a></div>'''
							% (ArtistID, artist[0][0]))

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
				duration = helpers.convert_milliseconds(int(results[i][4]))
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
			if not artistResults:
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
		threading.Thread(target=lastfm.getSimilar).start()
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % artistid)
		
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
		if headphones.LASTFM_USERNAME:
			lastfm_user_text = headphones.LASTFM_USERNAME
		else:
			lastfm_user_text = 'Last.FM Username'
		if headphones.MUSIC_DIR:
			music_dir_input = '''<input type="text" value="%s" name="path" size="70" />''' % headphones.MUSIC_DIR
		else:
			music_dir_input = '''<input type="text" value="Enter a Music Directory to scan" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="path" size="70" />'''
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
			%s
			<input type="submit" /></form><br /><br /></div></div>
		<div class="tableleft"><div class="config"><h1>Import Last.FM Artists</h1><br />
		Enter the username whose artists you want to import:<br /><br />
		<form action="importLastFM" method="GET" align="center">
			<input type="text" value="%s" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="username" size="18" />
			<input type="submit" /></form><br /><br /></div></div>
		<div class="tableright"><div class="config"><h1>Placeholder :-)</h1><br />
		<br /><br />
		<form action="" method="GET" align="center">
			<input type="text" value="" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="" size="18" />
			<input type="submit" /></form><br /><br /></div></div><br />
			<div class="table"><div class="config"><h1>Force Search</h1><br />
			<a href="forceSearch">Force Check for Wanted Albums</a><br /><br />
			<a href="forceUpdate">Force Update Active Artists</a><br /><br />
			<a href="forcePostProcess">Force Post-Process Albums in Download Folder</a><br /><br /><br />
			<a href="checkGithub">Check for Headphones Updates</a><br /><br /><br /></div></div>''' % (music_dir_input, lastfm_user_text))
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	manage.exposed = True
	
	def importLastFM(self, username):
		headphones.LASTFM_USERNAME = username
		headphones.config_write()
		threading.Thread(target=lastfm.getArtists).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("home")
	importLastFM.exposed = True
	
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
	
	def forcePostProcess(self):
		from headphones import postprocessor
		threading.Thread(target=postprocessor.forcePostProcess).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forcePostProcess.exposed = True
	
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
		log_file = os.path.join(headphones.LOG_DIR, 'headphones.log')
		if os.path.isfile(log_file):
			fileHandle = open(log_file)
			lineList = fileHandle.readlines()
			fileHandle.close()
			lineList.reverse()
			for line in lineList[1:200]:
				page.append(line.decode('utf-8') + '<br /><br />')
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
		checked(headphones.NEWZBIN),
		headphones.NEWZBIN_UID,
		headphones.NEWZBIN_PASSWORD,
		radio(headphones.PREFERRED_QUALITY, 0),
		radio(headphones.PREFERRED_QUALITY, 1),
		radio(headphones.PREFERRED_QUALITY, 3),
		radio(headphones.PREFERRED_QUALITY, 2),
		headphones.PREFERRED_BITRATE,
		checked(headphones.DETECT_BITRATE),
		checked(headphones.MOVE_FILES),
		checked(headphones.RENAME_FILES),
		checked(headphones.CORRECT_METADATA),
		checked(headphones.CLEANUP_FILES),
		checked(headphones.ADD_ALBUM_ART),
		checked(headphones.EMBED_ALBUM_ART),
		headphones.DESTINATION_DIR,
		headphones.FOLDER_FORMAT,
		headphones.FILE_FORMAT,
		checked(headphones.INCLUDE_EXTRAS),
		headphones.LOG_DIR
		))
		page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
					
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None, blackhole=0, blackhole_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, newzbin=0, newzbin_uid=None, newzbin_password=None, preferred_quality=0, preferred_bitrate=None, detect_bitrate=0, move_files=0, 
		rename_files=0, correct_metadata=0, cleanup_files=0, add_album_art=0, embed_album_art=0, destination_dir=None, folder_format=None, file_format=None, include_extras=0, log_dir=None):
		
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
		headphones.NEWZBIN = newzbin
		headphones.NEWZBIN_UID = newzbin_uid
		headphones.NEWZBIN_PASSWORD = newzbin_password
		headphones.PREFERRED_QUALITY = int(preferred_quality)
		headphones.PREFERRED_BITRATE = preferred_bitrate
		headphones.DETECT_BITRATE = detect_bitrate
		headphones.MOVE_FILES = move_files
		headphones.CORRECT_METADATA = correct_metadata
		headphones.RENAME_FILES = rename_files
		headphones.CLEANUP_FILES = cleanup_files
		headphones.ADD_ALBUM_ART = add_album_art
		headphones.EMBED_ALBUM_ART = embed_album_art
		headphones.DESTINATION_DIR = destination_dir
		headphones.FOLDER_FORMAT = folder_format
		headphones.FILE_FORMAT = file_format
		headphones.INCLUDE_EXTRAS = include_extras
		headphones.LOG_DIR = log_dir
		
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
		
	def extras(self):
		myDB = db.DBConnection()
		cloudlist = myDB.select('SELECT * from lastfmcloud')
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		if len(cloudlist):
			page.append('''
			<div class="table"><div class="config"><h1>Artists You Might Like:</h1><br /><br />
			<div class="cloud">
				<ul id="cloud">''')
			for item in cloudlist:
				page.append('<li><a href="addArtist?artistid=%s" class="tag%i">%s</a></li>' % (item['ArtistID'], item['Count'], item['ArtistName']))
			page.append('</ul><br /><br /></div></div>')	
			page.append(templates._footer % headphones.CURRENT_VERSION)
		return page
	extras.exposed = True

	def addReleaseById(self, rid):
		threading.Thread(target=importer.addReleaseById, args=[rid]).start()
		raise cherrypy.HTTPRedirect("home")
	addReleaseById.exposed = True
	
	def updateCloud(self):
		
		lastfm.getSimilar()
		raise cherrypy.HTTPRedirect("extras")
		
	updateCloud.exposed = True