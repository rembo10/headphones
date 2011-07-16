import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u
from headphones.mb import getReleaseGroup
import time
import os

import headphones
from headphones import logger, db, mb

def dbUpdate():

	myDB = db.DBConnection()

	activeartists = myDB.select('SELECT ArtistID, ArtistName from artists WHERE Status="Active"')
	
	i = 0
	
	while i < len(activeartists):
			
		artistid = activeartists[i][0]
		artistname = activeartists[i][1]
		logger.info(u"Updating album information for artist: " + artistname)
		
		artist = mb.getArtist(artistid)
		
		for rg in artist['releasegroups']:
			
			rgid = rg['id']
			
			releaseid = mb.getReleaseGroup(rgid)
			
			results = mb.getRelease(releaseid)
			
			albumlist = myDB.select('SELECT AlbumID from albums WHERE ArtistID=?', [artistid])
			
			if any(releaseid in x for x in albumlist):
					
				logger.info(results['title'] + " already exists in the database. Updating ASIN, Release Date, Tracks")
						
				myDB.action('UPDATE albums SET AlbumASIN=?, ReleaseDate=? WHERE AlbumID=?', [results['asin'], results['date'], results['id']])
		
				for track in results['tracks']:
					
					myDB.action('UPDATE tracks SET TrackDuration=? WHERE AlbumID=? AND TrackID=?', [track['duration'], results['id'], track['id']])

						
			else:
				
				logger.info(u"New album found! Adding "+results['title']+"to the database...")
				
				myDB.action('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', [artistid, artist['artist_name'], rg['title'], results['asin'], results['date'], results['id'], 'Skipped'])
				
				latestrelease = myDB.select('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID=?', [results['id']])
						
				if latestrelease[0][0] > latestrelease[0][1]:
							
					myDB.action('UPDATE albums SET Status = "Wanted" WHERE AlbumID=?', results['id'])
						
				else:
					pass
						
				for track in results['tracks']:
							
					myDB.action('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', [artistid, artist['artist_name'], rg['title'], results['asin'], results['id'], track['title'], track['duration'], track['id']])
		i += 1

