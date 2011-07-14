from pyItunes import *
from configobj import ConfigObj
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
from headphones.mb import getReleaseGroup
import string
import time
import os
import sqlite3
from beets.mediafile import MediaFile

import headphones
from headphones import logger

def scanMusic(dir=None):

	if not dir:
		dir = headphones.MUSIC_DIR

	results = []
	
	for r,d,f in os.walk(dir):
		for files in f:
			if any(files.endswith(x) for x in (".mp3", ".flac", ".aac", ".ogg", ".ape")):
				results.append(os.path.join(r,files))
	
	logger.info(u'%i music files found' % len(results))
	
	if results:
	
		lst = []
	
		# open db connection to write songs you have
		conn=sqlite3.connect(headphones.DB_FILE)
		c=conn.cursor()
		c.execute('''DELETE from have''')
	
		for song in results:
			try:
				f = MediaFile(song)
			except:
				logger.info("Could not read file: '" + song + "'")
			else:	
				if not f.artist:
					pass
				else:
					c.execute('INSERT INTO have VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?)', (f.artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid))
					lst.append(f.artist)
	
		conn.commit()
		c.close()
	
		artistlist = {}.fromkeys(lst).keys()
		logger.info(u"Preparing to import %i artists" % len(artistlist))
		importartist(artistlist)
	
	


def itunesImport(pathtoxml):
	if os.path.splitext(pathtoxml)[1] == '.xml':
		logger.info(u"Loading xml file from"+ pathtoxml)
		pl = XMLLibraryParser(pathtoxml)
		l = Library(pl.dictionary)
		lst = []
		for song in l.songs:
			lst.append(song.artist)
		rawlist = {}.fromkeys(lst).keys()
		artistlist = [f for f in rawlist if f != None]
		importartist(artistlist)
	else:
		rawlist = os.listdir(pathtoxml)
		logger.info(u"Loading artists from directory:" +pathtoxml)
		exclude = ['.ds_store', 'various artists', 'untitled folder', 'va']
		artistlist = [f for f in rawlist if f.lower() not in exclude]
		importartist(artistlist)
		


def importartist(artistlist):
	for name in artistlist:
		logger.info(u"Querying MusicBrainz for: "+name)
		artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&#38;', '%38'), limit=1))		
		for result in artistResults:
			if result.artist.name == 'Various Artists':
				logger.info(u"Top result is Various Artists. Skipping.")
			else:
				logger.info(u"Found best match: "+result.artist.name+". Gathering album information...")
				artistid = u.extractUuid(result.artist.id)
				inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
				artist = ws.Query().getArtistById(artistid, inc)
				conn=sqlite3.connect(headphones.DB_FILE)
				c=conn.cursor()
				c.execute('SELECT ArtistID from artists')
				artistlist = c.fetchall()
				if any(artistid in x for x in artistlist):
					logger.info(result.artist.name + u" is already in the database, skipping")
				else:
					c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
					for rg in artist.getReleaseGroups():
						rgid = u.extractUuid(rg.id)
						
						releaseid = getReleaseGroup(rgid)
						
						inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
						results = ws.Query().getReleaseById(releaseid, inc)

						logger.info(u"Now adding album: " + results.title+ " to the database")
						c.execute('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', (artistid, results.artist.name, results.title, results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id), 'Skipped'))
						conn.commit()
						c.execute('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID="%s"' % u.extractUuid(results.id))
								
						latestrelease = c.fetchall()
						
						if latestrelease[0][0] > latestrelease[0][1]:
							logger.info(results.title + u" is an upcoming album. Setting its status to 'Wanted'...")
							c.execute('UPDATE albums SET Status = "Wanted" WHERE AlbumID="%s"' % u.extractUuid(results.id))
						else:
							pass
							
						for track in results.tracks:
							c.execute('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', (artistid, results.artist.name, results.title, results.asin, u.extractUuid(results.id), track.title, track.duration, u.extractUuid(track.id)))
						time.sleep(1)
				time.sleep(1)

				conn.commit()		
				c.close()