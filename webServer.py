import templates
import config
import cherrypy
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
import os
import string
import time
import sqlite3
import sys
import configobj
from headphones import FULL_PATH, config_file

database = os.path.join(FULL_PATH, 'headphones.db')

class Headphones:

	def index(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		#Display Database if it exists:
		if os.path.exists(database):
			conn=sqlite3.connect(database)
			c=conn.cursor()
			c.execute('SELECT ArtistName, ArtistID, Status from artists order by ArtistSortName')
			results = c.fetchall()
			c.close()
			i = 0
			page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr>
						<th align="left" width="170">Artist Name</th>
						<th align="center" width="100">Status</th>
						<th align="center" width="300">Upcoming Albums</th>
						<th>      </th>
						</tr>''')
			while i < len(results):
				c.execute('''SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumID from albums WHERE ArtistName="%s" order by ReleaseDate DESC''' % results[i][0])
				latestalbum = c.fetchall()
				if latestalbum[0][1] > latestalbum[0][2]:
					newalbumName = '<font color="#5DFC0A" size="3px"><a href="albumPage?name=%s"><i>%s</i>' % (latestalbum[0][3], latestalbum[0][0])
					releaseDate = '(%s)</a></font>' % latestalbum[0][1]
				else:
					newalbumName = '<font color="#CFCFCF">None</font>'
					releaseDate = ""
				if results[i][2] == 'Paused':
					newStatus = '''<font color="red"><b>%s</b></font>(<A class="external" href="resumeArtist?ArtistID=%s">resume</a>)''' % (results[i][2], results[i][1])
				else:
					newStatus = '''%s(<A class="external" href="pauseArtist?ArtistID=%s">pause</a>)''' % (results[i][2], results[i][1])
				page.append('''<tr><td align="left" width="300"><a href="artistPage?ArtistID=%s">%s</a> 
								(<A class="external" href="http://musicbrainz.org/artist/%s">link</a>) [<A class="externalred" href="deleteArtist?ArtistID=%s">delete</a>]</td>
								<td align="center" width="160">%s</td>
								<td align="center">%s %s</td></tr>''' % (results[i][1], results[i][0], results[i][1], results[i][1], newStatus, newalbumName, releaseDate))	
				i = i+1
			page.append('''</table></div>''')
		else:
			page.append("""<div class="datanil">Add some artists to the database!</div>""")
		page.append(templates._footer)
		return page
	index.exposed = True
	

	def artistPage(self, ArtistID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('''SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID="%s" order by ReleaseDate DESC''' % ArtistID)
		results = c.fetchall()
		c.close()
		i = 0
		page.append('''<div class="table"><table border="0" cellpadding="3">
						<tr><p align="center">%s <br /></p></tr>
						<tr>
						<th align="left" width="50"></th>
						<th align="left" width="120">Album Name</th>
						<th align="center" width="100">Release Date</th>
						<th align="center" width="300">Status</th>
						<th>      </th>
						</tr>''' % (results[0][4]))
		while i < len(results):
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
							<td align="center">%s</td></tr>''' % (results[i][5], results[i][2], results[i][0], results[i][2], results[i][1], newStatus))	
			i = i+1
		page.append('''</table></div>''')
		page.append(templates._footer)
		return page
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('''SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN from tracks WHERE AlbumID="%s"''' % AlbumID)
		results = c.fetchall()
		if results[0][6]:
			albumart = '''<br /><img src="http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg" height="200" width="200"><br /><br />''' % results[0][6]
		else:
			albumart = ''
		c.close()
		i = 0
		page.append('''<div class="table" align="center"><table border="0" cellpadding="3">
					<tr><a href="artistPage?ArtistID=%s">%s</a> - %s<br />%s</tr>
					<br /><tr>
					<th align="left" width="100">Track #</th>
					<th align="left" width="100">Track Title</th>
					<th align="center" width="300">Duration</th>
					<th>      </th>
					</tr>''' % (results[0][0], results[0][1], results[0][2], albumart))
		while i < len(results):
			page.append('''<tr><td align="left" width="120">%s</td>
							<td align="left" width="240">%s (<A class="external" href="http://musicbrainz.org/recording/%s.html">link</a>)</td>
							<td align="center">%s</td></tr>''' % (i+1, results[i][3], results[i][5], results[i][4]))	
			i = i+1
		page.append('''</table></div>''')

		
		page.append(templates._footer)
		return page
	
	albumPage.exposed = True
	
	
	def findArtist(self, name):
	
		page = [templates._header]
		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("/")
		else:
			artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&', '%38'), limit=8))
			if len(artistResults) == 0:
				page.append('''No results!<a class="blue" href="/">Go back</a>''')
				
			elif len(artistResults) > 1:
				page.append('''Search returned multiple artists. Click the artist you want to add:<br /><br />''')
				for result in artistResults:
					artist = result.artist
					page.append('''<a href="/addArtist?artistid=%s">%s</a> (<a class="externalred" href="/artistInfo?artistid=%s">more info</a>)<br />''' % (u.extractUuid(artist.id), artist.name, u.extractUuid(artist.id)))
				return page
			else:
				for result in artistResults:
					artist = result.artist
					raise cherrypy.HTTPRedirect("/addArtist?artistid=%s" % u.extractUuid(artist.id))
		
	findArtist.exposed = True

	def artistInfo(self, artistid):
		page = [templates._header]
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		artist = ws.Query().getArtistById(artistid, inc)
		page.append('''Artist Name: %s </br> ''' % artist.name)
		page.append('''Unique ID: %s </br></br>Albums:<br />''' % u.extractUuid(artist.id))
		for rg in artist.getReleaseGroups():
			page.append('''%s <br />''' % rg.title)
		return page
		
	artistInfo.exposed = True

	def addArtist(self, artistid):
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=False)
		artist = ws.Query().getArtistById(artistid, inc)
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT)')
		c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
		c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration TEXT, TrackID TEXT)')
		c.execute('SELECT ArtistID from artists')
		artistlist = c.fetchall()
		if any(artistid in x for x in artistlist):
			page = [templates._header]
			page.append('''%s has already been added. Go <a href="/">back</a>.''' % artist.name)
			return page
		else:
			c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
			for release in artist.getReleases():
				releaseid = u.extractUuid(release.id)
				inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
				results = ws.Query().getReleaseById(releaseid, inc)
				time.sleep(0.6)
				for event in results.releaseEvents:
					if event.country == 'US':
						c.execute('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', (artistid, results.artist.name, results.title, results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id), 'Skipped'))
						conn.commit()
						c.execute('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID="%s"' % u.extractUuid(results.id))
						latestrelease = c.fetchall()
						if latestrelease[0][0] > latestrelease[0][1]:
							c.execute('UPDATE albums SET Status = "Wanted" WHERE AlbumID="%s"' % u.extractUuid(results.id))
						else:
							pass
						for track in results.tracks:
							c.execute('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', (artistid, results.artist.name, results.title, results.asin, u.extractUuid(results.id), track.title, track.duration, u.extractUuid(track.id)))
							conn.commit()
							c.close()
					else:
						pass
			raise cherrypy.HTTPRedirect("/")
		
		
	addArtist.exposed = True
	
		#page for pausing an artist
	def pauseArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('UPDATE artists SET status = "Paused" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/")
		
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
		c.execute('UPDATE artists SET status = "Active" WHERE ArtistId="%s"' % ArtistID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/")
		
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):
		conn=sqlite3.connect(database)
		c=conn.cursor()
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
		c.execute('UPDATE albums SET status = "Skipped" WHERE AlbumID="%s"' % AlbumID)
		conn.commit()
		c.close()
		raise cherrypy.HTTPRedirect("/artistPage?ArtistID=%s" % ArtistID)
		
	unqueueAlbum.exposed = True
	
	def upcoming(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append(templates._footer)
		return page
	upcoming.exposed = True
	
	def manage(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append(templates._footer)
		return page
	manage.exposed = True
	
	def history(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append(templates._footer)
		return page
	history.exposed = True
	
	def config(self):
		page = [templates._header]
		page.append(templates._logobar)
		page.append(templates._nav)
		page.append(config.form)
		page.append(templates._footer)
		return page
					
	config.exposed = True
	
	
	def configUpdate(self, http_host='127.0.0.1', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, music_download_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, include_lossless=0, 
		flac_to_mp3=0, move_to_itunes=0, path_to_itunes=None, rename_mp3s=0, cleanup=0, add_album_art=0):
		
		configs = configobj.ConfigObj(config_file)
		SABnzbd = configs['SABnzbd']
		General = configs['General']
		NZBMatrix = configs['NZBMatrix']	
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
		sys.exit()

	shutdown.exposed = True
