from webServer import database
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
import sqlite3
import time

import logger

def dbUpdate():

	conn=sqlite3.connect(database)
	c=conn.cursor()
	c.execute('SELECT ArtistID, ArtistName from artists WHERE Status="Active"')
	
	activeartists = c.fetchall()
	
	i = 0
	
	while i < len(activeartists):
			
		artistid = activeartists[i][0]
		artistname = activeartists[i][1]
		logger.log(u"Updating album information for artist: " + artistname)
		
		c.execute('SELECT AlbumID from albums WHERE ArtistID="%s"' % artistid)
		albumlist = c.fetchall()
		
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=False)
		artist = ws.Query().getArtistById(artistid, inc)
		
		for release in artist.getReleases():
			
			releaseid = u.extractUuid(release.id)
			inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
			results = ws.Query().getReleaseById(releaseid, inc)
			time.sleep(2)
			
			for event in results.releaseEvents:
				
				if event.country == 'US':
					
					if any(releaseid in x for x in albumlist):
					
						logger.log(results.title + " already exists in the database. Updating ASIN, Release Date, Tracks")
						
						c.execute('UPDATE albums SET AlbumASIN="%s", ReleaseDate="%s" WHERE AlbumID="%s"' % (results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id)))
		
						for track in results.tracks:
							c.execute('UPDATE tracks SET TrackDuration="%s" WHERE AlbumID="%s" AND TrackID="%s"' % (track.duration, u.extractUuid(results.id), u.extractUuid(track.id)))
							conn.commit()
						
					else:
						
						logger.log(u"New album found! Adding "+results.title+"to the database...")
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
					logger.log(results.title + " is not a US release. Skipping it for now")
		i += 1
	
	conn.commit()
	c.close()
	conn.close()

