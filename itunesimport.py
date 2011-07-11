from pyItunes import *
from configobj import ConfigObj
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
import string
import time
import os
import sqlite3
from headphones import FULL_PATH
from lib.beets.mediafile import MediaFile

import logger

database = os.path.join(FULL_PATH, 'headphones.db')


def scanMusic(dir):

	results = []
	
	for r,d,f in os.walk(dir):
		for files in f:
			if any(files.endswith(x) for x in (".mp3", ".flac", ".aac", ".ogg", ".ape")):
				results.append(os.path.join(r,files))
	
	logger.log(u'%i music files found' % len(results))
	
	lst = []
	
	for song in results:
		try:
			f = MediaFile(song)
		except:
			logger.log("Could not read file: '" + song + "'", logger.ERROR)
		else:	
			if not f.artist:
				pass
			else:
				lst.append(f.artist)
	
	artistlist = {}.fromkeys(lst).keys()
	logger.log(u"Preparing to import %i artists" % len(artistlist))
	importartist(artistlist)
	
	


def itunesImport(pathtoxml):
	if os.path.splitext(pathtoxml)[1] == '.xml':
		logger.log(u"Loading xml file from"+ pathtoxml)
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
		logger.log(u"Loading artists from directory:" +pathtoxml)
		exclude = ['.ds_store', 'various artists', 'untitled folder', 'va']
		artistlist = [f for f in rawlist if f.lower() not in exclude]
		importartist(artistlist)
		


def importartist(artistlist):
	for name in artistlist:
		logger.log(u"Querying MusicBrainz for: "+name)
		time.sleep(1)
		artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&#38;', '%38'), limit=1))		
		for result in artistResults:
			if result.artist.name == 'Various Artists':
				logger.log(u"Top result is Various Artists. Skipping.", logger.WARNING)
			else:
				logger.log(u"Found best match: "+result.artist.name+". Gathering album information...")
				time.sleep(1)
				artistid = u.extractUuid(result.artist.id)
				inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=False)
				artist = ws.Query().getArtistById(artistid, inc)
				conn=sqlite3.connect(database)
				c=conn.cursor()
				c.execute('SELECT ArtistID from artists')
				artistlist = c.fetchall()
				if any(artistid in x for x in artistlist):
					logger.log(result.artist.name + u" is already in the database, skipping")
				else:
					c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
					for release in artist.getReleases():
						time.sleep(1)
						releaseid = u.extractUuid(release.id)
						inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
						results = ws.Query().getReleaseById(releaseid, inc)
						
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
	
							else:
								logger.log(results.title + u" is not a US release. Skipping for now")
			
				c.close()