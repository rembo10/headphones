import os, sys

import cherrypy

import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u

import string
import time
import datetime
import sqlite3
from threading import Thread

import headphones
from headphones.mb import getReleaseGroup
from headphones import templates, logger, searcher
from headphones.helpers import checked


class WebInterface(object):

	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		page = [templates._header]
		if headphones.LATEST_VERSION and headphones.CURRENT_VERSION:
			if headphones.CURRENT_VERSION != headphones.LATEST_VERSION:
				page.append('''<div class="updatebar">A <a class="blue" href="http://github.com/rembo10/headphones/compare/%s...%s">
					newer version</a> is available. You're %s commits behind. <a class="blue" href="update">Click here to update</a></div>
					''' % (headphones.CURRENT_VERSION, headphones.LATEST_VERSION, headphones.COMMITS_BEHIND))
		page.append(templates._logobar)
		page.append(templates._nav)

		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('SELECT ArtistName, ArtistID, Status from artists order by ArtistSortName collate nocase')
		results = c.fetchall()
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
				c.execute('''SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumID from albums WHERE ArtistID='%s' order by ReleaseDate DESC''' % results[i][1])
				latestalbum = c.fetchall()
				c.execute('''SELECT TrackTitle from tracks WHERE ArtistID="%s"''' % results[i][1])
				totaltracks = len(c.fetchall())
				c.execute('''SELECT TrackTitle from have WHERE ArtistName like "%s"''' % results[i][0])
				havetracks = len(c.fetchall())
				try:
					percent = (havetracks*100)/totaltracks
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
				else:
					newStatus = '''%s(<A class="external" href="pauseArtist?ArtistID=%s">pause</a>)''' % (results[i][2], results[i][1])
				page.append('''<tr><td align="left" width="300"><a href="artistPage?ArtistID=%s">%s</a> 
								(<A class="external" href="http://musicbrainz.org/artist/%s">link</a>) [<A class="externalred" href="deleteArtist?ArtistID=%s">delete</a>]</td>
								<td align="center" width="160">%s</td>
								<td align="center">%s %s</td>
								<td><div class="progress-container"><div style="width: %s%%"></div></div></td></tr>
								''' % (results[i][1], results[i][0], results[i][1], results[i][1], newStatus, newalbumName, releaseDate, percent))	
				i = i+1
			c.close()
			page.append('''</table></div>''')
			page.append(templates._footer)
			
		else:
			page.append("""<div class="datanil">Add some artists to the database!</div>""")
		return page
	home.exposed = True
	

	def artistPage(self, ArtistID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('''SELECT ArtistName from artists WHERE ArtistID="%s"''' % ArtistID)
		artistname = c.fetchall()
		c.execute('''SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID="%s" order by ReleaseDate DESC''' % ArtistID)
		results = c.fetchall()
		i = 0
		page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr><p align="center">%s <br /></p></tr>
						<tr>
						<th align="left" width="30"></th>
						<th align="left" width="120">Album Name</th>
						<th align="center" width="100">Release Date</th>
						<th align="center" width="180">Status</th>
						<th align="center">Have</th>
						</tr>''' % (artistname[0]))
		while i < len(results):
			c.execute('''SELECT TrackTitle from tracks WHERE AlbumID="%s"''' % results[i][2])
			totaltracks = len(c.fetchall())
			c.execute('''SELECT TrackTitle from have WHERE ArtistName like ? AND AlbumTitle like ?''', (results[i][4], results[i][0]))
			havetracks = len(c.fetchall())
			try:
				percent = (havetracks*100)/totaltracks
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
		c.close()
		page.append('''</table></div>''')
		page.append(templates._footer)
		return page
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('''SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN from tracks WHERE AlbumID="%s"''' % AlbumID)
		results = c.fetchall()
		
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
			c.execute('''SELECT TrackTitle from have WHERE ArtistName like ? AND AlbumTitle like ? AND TrackTitle like ?''', (results[i][1], results[i][2], results[i][3]))
			trackmatches = c.fetchall()
			if len(trackmatches):
				have = '<img src="images/checkmark.png" width="20px">'
			else:
				have = ''
			if results[i][4]:
				duration = time.strftime("%M:%S", time.gmtime(int(results[i][4])/1000))
			else:
				duration = 'n/a'
			page.append('''<tr><td align="left" width="120">%s</td>
							<td align="left" width="240">%s (<A class="external" href="http://musicbrainz.org/recording/%s.html">link</a>)</td>
							<td align="center">%s</td>
							<td>%s</td></tr>''' % (i+1, results[i][3], results[i][5], duration, have))	
			i = i+1
		c.close()
		page.append('''</table></div>''')
		page.append(templates._footer)
		return page
	
	albumPage.exposed = True
	
	
	def findArtist(self, name):
	
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("home")
		else:
			artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&', '%38'), limit=8))
			if len(artistResults) == 0:
				logger.info(u"No results found for " + name)
				page.append('''No results!<a class="blue" href="home">Go back</a>''')
				return page
			elif len(artistResults) > 1:
				page.append('''<div class="table">Search returned multiple artists. Click the artist you want to add:<br /><br />''')
				for result in artistResults:
					artist = result.artist
					detail = artist.getDisambiguation()
					if detail:
						disambiguation = '(%s)' % detail
					else:
						disambiguation = ''
					page.append('''<a href="addArtist?artistid=%s">%s %s</a> (<a class="externalred" href="artistInfo?artistid=%s">more info</a>)<br />''' % (u.extractUuid(artist.id), artist.name, disambiguation, u.extractUuid(artist.id)))
				page.append('''</div>''')xs
				return page
			else:
				for result in artistResults:
					artist = result.artist
					logger.info(u"Found one artist matching your search term: " + artist.name +" ("+ artist.id+")")			
					raise cherrypy.HTTPRedirect("addArtist?artistid=%s" % u.extractUuid(artist.id))
		
	findArtist.exposed = True

	def artistInfo(self, artistid):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		artist = ws.Query().getArtistById(artistid, inc)
		page.append('''Artist Name: %s </br> ''' % artist.name)
		page.append('''Unique ID: %s </br></br>Albums:<br />''' % u.extractUuid(artist.id))
		for rg in artist.getReleaseGroups():
			page.append('''%s <br />''' % rg.title)
		return page
		
	artistInfo.exposed = True

	def addArtist(self, artistid):
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		artist = ws.Query().getArtistById(artistid, inc)
		time.sleep(1)
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('SELECT ArtistID from artists')
		artistlist = c.fetchall()
		if any(artistid in x for x in artistlist):
			page = [templates._header]
			page.append
			page.append('''%s has already been added. Go <a href="home">back</a>.''' % artist.name)
			logger.info(artist.name + u" is already in the database!")
			c.close()
			return page
		
		else:
			logger.info(u"Adding " + artist.name + " to the database.")
			c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
			for rg in artist.getReleaseGroups():
				rgid = u.extractUuid(rg.id)
				
				releaseid = getReleaseGroup(rgid)
				
				inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
				results = ws.Query().getReleaseById(releaseid, inc)
				time.sleep(1)
				logger.info(u"Now adding album: " + results.title+ " to the database")
				c.execute('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', (artistid, results.artist.name, results.title, results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id), 'Skipped'))
				c.execute('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID="%s"' % u.extractUuid(results.id))
				latestrelease = c.fetchall()
						
				if latestrelease[0][0] > latestrelease[0][1]:
					logger.info(results.title + u" is an upcoming album. Setting its status to 'Wanted'...")
					c.execute('UPDATE albums SET Status = "Wanted" WHERE AlbumID="%s"' % u.extractUuid(results.id))
				else:
					pass
					
				for track in results.tracks:
					c.execute('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', (artistid, results.artist.name, results.title, results.asin, u.extractUuid(results.id), track.title, track.duration, u.extractUuid(track.id)))
			
			conn.commit()
			c.close()
			raise cherrypy.HTTPRedirect("home")
		
	addArtist.exposed = True
	
	def pauseArtist(self, ArtistID):
	
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Pausing artist: " + ArtistID)
		c.execute('UPDATE artists SET status = "Paused" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("home")
		
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Resuming artist: " + ArtistID)
		c.execute('UPDATE artists SET status = "Active" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("home")
		
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Deleting all traces of artist: " + ArtistID)
		c.execute('''DELETE from artists WHERE ArtistID="%s"''' % ArtistID)
		c.execute('''DELETE from albums WHERE ArtistID="%s"''' % ArtistID)
		c.execute('''DELETE from tracks WHERE ArtistID="%s"''' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("home")
		
	deleteArtist.exposed = True
	
	def queueAlbum(self, AlbumID, ArtistID):
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Marking album: " + AlbumID + "as wanted...")
		c.execute('UPDATE albums SET status = "Wanted" WHERE AlbumID="%s"' % AlbumID)
		conn.commit()
		c.close()
		import searcher
		searcher.searchNZB(AlbumID)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		
	queueAlbum.exposed = True

	def unqueueAlbum(self, AlbumID, ArtistID):
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Marking album: " + AlbumID + "as skipped...")
		c.execute('UPDATE albums SET status = "Skipped" WHERE AlbumID="%s"' % AlbumID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		
	unqueueAlbum.exposed = True
	
	def upcoming(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		today = datetime.date.today()
		todaysql = datetime.date.isoformat(today)
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('''SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC''')
		albums = c.fetchall()
		c.execute('''SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE Status="Wanted"''')
		wanted = c.fetchall()
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
			page.append(templates._footer)
		
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
		page.append(templates._footer)
		return page
	manage.exposed = True
	
	def importItunes(self, path):
		headphones.PATH_TO_XML = path
		headphones.config_write()
		from headphones import itunesimport
		itunesimport.itunesImport(path)
		raise cherrypy.HTTPRedirect("home")
	importItunes.exposed = True
	
	def musicScan(self, path):
		from headphones import itunesimport
		headphones.MUSIC_DIR = path
		headphones.config_write()
		try:	
			itunesimport.scanMusic(path)
		except Exception, e:
			logger.error('Unable to complete the scan: %s' % e)
		raise cherrypy.HTTPRedirect("home")
	musicScan.exposed = True
	
	def forceUpdate(self):
		from headphones import updater
		updater.dbUpdate()
		raise cherrypy.HTTPRedirect("home")
	forceUpdate.exposed = True
	
	def forceSearch(self):
		from headphones import searcher
		searcher.searchNZB()
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
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('''SELECT AlbumID, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT from snatched order by DateAdded DESC''')
		snatched = c.fetchall()
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
			page.append(templates._footer)
		return page
	history.exposed = True
	
	def clearhistory(self):
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		logger.info(u"Clearing history")
		c.execute('''DELETE from snatched''')
		conn.commit()
		c.close()
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
		#page.append(templates._footer)
		return page
					
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None,
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
		headphones.shutdown()
		return 'Shutting down Headphones...'

	shutdown.exposed = True

	def restart(self):
		logger.info(u"Headphones is restarting...")
		headphones.shutdown(restart=True)
		return 'Restarting Headphones...'
	 
	restart.exposed = True
	
	def update(self):
		logger.info('Headphones is updating...')
		headphones.shutdown(restart=True, update=True)
		return 'Updating Headphones...'
		
	update.exposed = True