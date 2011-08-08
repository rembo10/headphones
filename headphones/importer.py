from lib.pyItunes import *
import time
import os
from lib.beets.mediafile import MediaFile

import headphones
from headphones import logger, helpers, db, mb, albumart, lastfm

various_artists_mbid = '89ad4ac3-39f7-470e-963a-56509c546377'

def scanMusic(dir=None):

	if not dir:
		dir = headphones.MUSIC_DIR
		
	try:
		dir = str(dir)
	except UnicodeEncodeError:
		dir = unicode(dir).encode('unicode_escape')
		
	logger.info('Starting Music Scan with directory: %s' % dir)

	results = []
	
	for r,d,f in os.walk(dir):
		for files in f:
			if any(files.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				results.append(os.path.join(r, files))
				
	logger.info(u'%i music files found. Reading metadata....' % len(results))
	
	if results:
	
		myDB = db.DBConnection()
		myDB.action('''DELETE from have''')
	
		for song in results:
			try:
				f = MediaFile(song)
				albumartist = f.albumartist
				artist = f.artist
			except:
				logger.warn('Could not read file: %s' % song)
				continue
			else:	
				if albumartist and albumartist != 'Various Artists':
					artist = albumartist
				elif artist:
					pass
				else:
					continue
				
				myDB.action('INSERT INTO have VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?)', [artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid])
				
		# Get the average bitrate if the option is selected
		if headphones.DETECT_BITRATE:
			try:
				avgbitrate = myDB.action("SELECT AVG(BitRate) FROM have").fetchone()[0]
				headphones.PREFERRED_BITRATE = int(avgbitrate)/1000
				
			except Exception, e:
				logger.error('Error detecting preferred bitrate:' + str(e))
			
		artistlist = myDB.action('SELECT DISTINCT ArtistName FROM have').fetchall()
		logger.info(u"Preparing to import %i artists" % len(artistlist))
		
		artistlist_to_mbids(artistlist)

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
	
	else:
		rawlist = os.listdir(pathtoxml)
		logger.info(u"Loading artists from directory:" +pathtoxml)
		exclude = ['.ds_store', 'various artists', 'untitled folder', 'va']
		artistlist = [f for f in rawlist if f.lower() not in exclude]
		
	logger.info('Starting directory/xml import...')
	artistlist_to_mbids(artistlist)
	
		
def is_exists(artistid):

	myDB = db.DBConnection()
	
	# See if the artist is already in the database
	artistlist = myDB.select('SELECT ArtistID, ArtistName from artists WHERE ArtistID=?', [artistid])

	if any(artistid in x for x in artistlist):
		logger.info(artistlist[0][1] + u" is already in the database. Updating 'have tracks', but not artist information")
		return True
	else:
		return False


def artistlist_to_mbids(artistlist):

	for artist in artistlist:
	
		results = mb.findArtist(artist['ArtistName'], limit=1)
		
		if not results:
			continue
		
		try:	
			artistid = results[0]['id']
		
		except IndexError:
			logger.info('MusicBrainz query turned up no matches for: %s' % artist)
			continue
		
		# Add to database if it doesn't exist
		if artistid != various_artists_mbid and not is_exists(artistid):
			addArtisttoDB(artistid)
			
		# Update track count regardless of whether it already exists
		if artistid != various_artists_mbid:
	
			myDB = db.DBConnection()
			havetracks = len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['ArtistName']]))
			
			controlValueDict = {"ArtistID": 	artistid}
			newValueDict = {"HaveTracks": 		havetracks}
			myDB.upsert("artists", newValueDict, controlValueDict)
			
	# Update the similar artist tag cloud:
	logger.info('Updating artist information from Last.fm')
	try:
		lastfm.getSimilar()
	except Exception, e:
		logger.warn('Failed to update arist information from Last.fm: %s' % e)
		

def addArtisttoDB(artistid, extrasonly=False):
	
	# Can't add various artists - throws an error from MB
	if artistid == various_artists_mbid:
		logger.warn('Cannot import Various Artists.')
		return
		
	myDB = db.DBConnection()
		
	artist = mb.getArtist(artistid, extrasonly)
	
	if not artist:
		return
	
	if artist['artist_name'].startswith('The '):
		sortname = artist['artist_name'][4:]
	else:
		sortname = artist['artist_name']
		

	logger.info(u"Now adding/updating: " + artist['artist_name'])
	controlValueDict = {"ArtistID": 	artistid}
	newValueDict = {"ArtistName": 		artist['artist_name'],
					"ArtistSortName": 	sortname,
					"DateAdded": 		helpers.today(),
					"Status": 			"Loading"}
	
	if headphones.INCLUDE_EXTRAS:
		newValueDict['IncludeExtras'] = 1
	
	myDB.upsert("artists", newValueDict, controlValueDict)

	for rg in artist['releasegroups']:
		
		rgid = rg['id']
		
		# check if the album already exists
		rg_exists = myDB.select("SELECT * from albums WHERE AlbumID=?", [rg['id']])
					
		try:	
			release_dict = mb.getReleaseGroup(rgid)
		except Exception, e:
			logger.info('Unable to get release information for %s - there may not be any official releases in this release group' % rg['title'])
			continue
			
		if not release_dict:
			continue
	
		logger.info(u"Now adding/updating album: " + rg['title'])
		controlValueDict = {"AlbumID": 	rg['id']}
		
		if len(rg_exists):
		
			newValueDict = {"AlbumASIN":		release_dict['asin'],
							"ReleaseDate":		release_dict['releasedate'],
							}
		
		else:
		
			newValueDict = {"ArtistID":			artistid,
							"ArtistName": 		artist['artist_name'],
							"AlbumTitle":		rg['title'],
							"AlbumASIN":		release_dict['asin'],
							"ReleaseDate":		release_dict['releasedate'],
							"DateAdded":		helpers.today(),
							"Type":				rg['type']
							}
							
			if release_dict['releasedate'] > helpers.today():
				newValueDict['Status'] = "Wanted"
			else:
				newValueDict['Status'] = "Skipped"
		
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		lastfm.getAlbumDescription(rg['id'], release_dict['releaselist'])
		
		# I changed the albumid from releaseid -> rgid, so might need to delete albums that have a releaseid
		for release in release_dict['releaselist']:
			myDB.action('DELETE from albums WHERE AlbumID=?', [release['releaseid']])
			myDB.action('DELETE from tracks WHERE AlbumID=?', [release['releaseid']])
		
		myDB.action('DELETE from tracks WHERE AlbumID=?', [rg['id']])
		for track in release_dict['tracks']:
		
			controlValueDict = {"TrackID": 	track['id'],
								"AlbumID":	rg['id']}
			newValueDict = {"ArtistID":		artistid,
						"ArtistName": 		artist['artist_name'],
						"AlbumTitle":		rg['title'],
						"AlbumASIN":		release_dict['asin'],
						"TrackTitle":		track['title'],
						"TrackDuration":	track['duration'],
						"TrackNumber":		track['number']
						}
		
			myDB.upsert("tracks", newValueDict, controlValueDict)
			
	latestalbum = myDB.action('SELECT AlbumTitle, ReleaseDate, AlbumID from albums WHERE ArtistID=? order by ReleaseDate DESC', [artistid]).fetchone()
	totaltracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=?', [artistid]))
	
	controlValueDict = {"ArtistID": 	artistid}
	
	if latestalbum:
		newValueDict = {"Status": 			"Active",
						"LatestAlbum":		latestalbum['AlbumTitle'],
						"ReleaseDate":		latestalbum['ReleaseDate'],
						"AlbumID":			latestalbum['AlbumID'],
						"TotalTracks":		totaltracks}
	else:
		newValueDict = {"Status":			"Active"}
	
	myDB.upsert("artists", newValueDict, controlValueDict)
	logger.info(u"Updating complete for: " + artist['artist_name'])
	
def addReleaseById(rid):

	myDB = db.DBConnection()
	
	#we have to make a call to get the release no matter what so we can get the RGID
	#need a way around this - a local cache maybe in the future maybe? 
	try:
		release_dict = mb.getRelease(rid)
	except Exception, e:
		logger.info('Unable to get release information for Release: ' + str(rid) + " " + str(e))
		return
	if not release_dict:
		logger.info('Unable to get release information for Release: ' + str(rid) + " no dict")
		return
	
	rgid = release_dict['rgid']
	
	#we don't want to make more calls to MB here unless we have to, could be happening quite a lot
	#TODO: why do I have to str() this here? I don't get it.
	rg_exists = myDB.select("SELECT * from albums WHERE AlbumID=?", [rgid])
	
	#make sure the artist exists since I don't know what happens later if it doesn't
	artist_exists = myDB.select("SELECT * from artists WHERE ArtistID=?", [release_dict['artist_id']])
	if not artist_exists:
		if release_dict['artist_name'].startswith('The '):
			sortname = release_dict['artist_name'][4:]
		else:
			sortname = release_dict['artist_name']
			
	
		logger.info(u"Now manually adding: " + release_dict['artist_name'] + " - with status Paused")
		controlValueDict = {"ArtistID": 	release_dict['artist_id']}
		newValueDict = {"ArtistName": 		release_dict['artist_name'],
						"ArtistSortName": 	sortname,
						"DateAdded": 		helpers.today(),
						"Status": 			"Paused"}
		
		if headphones.INCLUDE_EXTRAS:
			newValueDict['IncludeExtras'] = 1
		
		myDB.upsert("artists", newValueDict, controlValueDict)

	if not rg_exists:	
		logger.info(u"Now adding-by-id album (" + release_dict['title'] + ") from id: " + rgid)
		controlValueDict = {"AlbumID": 	rgid}

		newValueDict = {"ArtistID":			release_dict['artist_id'],
						"ArtistName": 		release_dict['artist_name'],
						"AlbumTitle":		release_dict['rg_title'],
						"AlbumASIN":		release_dict['asin'],
						"ReleaseDate":		release_dict['date'],
						"DateAdded":		helpers.today(),
						"Status":			'Wanted',
						"Type":				release_dict['rg_type']
						}
		
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		for track in release_dict['tracks']:
		
			controlValueDict = {"TrackID": 	track['id'],
								"AlbumID":	release_dict['rgid']}
			newValueDict = {"ArtistID":		release_dict['artist_id'],
						"ArtistName": 		release_dict['artist_name'],
						"AlbumTitle":		release_dict['rg_title'],
						"AlbumASIN":		release_dict['asin'],
						"TrackTitle":		track['title'],
						"TrackDuration":	track['duration'],
						"TrackNumber":		track['number']
						}
		
			myDB.upsert("tracks", newValueDict, controlValueDict)

		
		#start a search for the album
		import searcher
		searcher.searchNZB(rgid, False)
	else:
		logger.info('Release ' + str(rid) + " already exists in the database!")