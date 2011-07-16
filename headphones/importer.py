from lib.pyItunes import *
from lib.configobj import ConfigObj
import time
import os
from lib.beets.mediafile import MediaFile

import headphones
from headphones import logger, helpers, db, mb

various_artists_mbid = '89ad4ac3-39f7-470e-963a-56509c546377'

def scanMusic(dir=None):

	if not dir:
		dir = headphones.MUSIC_DIR

	results = []
	
	for r,d,f in os.walk(unicode(dir)):
		for files in f:
			if any(files.endswith(x) for x in (".mp3", ".flac", ".aac", ".ogg", ".ape")):
				results.append(os.path.join(r,files))
	
	logger.info(u'%i music files found' % len(results))
	
	if results:
	
		lst = []
	
		myDB = db.DBConnection()
		myDB.action('''DELETE from have''')
	
		for song in results:
			try:
				f = MediaFile(song)
			except:
				logger.info("Could not read file: '" + song + "'")
			else:	
				if f.albumartist:
					artist = f.albumartist
				elif f.artist:
					artist = f.artist
				else:
					continue
				
				myDB.action('INSERT INTO have VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?)', [artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid])
				lst.append(artist)
	
		artistlist = {}.fromkeys(lst).keys()
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
		
	artistlist_to_mbids(artistlist)
	
	
def artistlist_to_mbids(artistlist):

	for artist in artistlist:
	
		results = mb.findArtist(artist, limit=1)
		artistid = results[0]['id']
		if artistid != various_artists_mbid:
			addArtisttoDB(artistid)


def addArtisttoDB(artistid):

	if artistid == various_artists_mbid:
		logger.warn('Cannot import Various Artists.')
		return
		
	myDB = db.DBConnection()
	
	artistlist = myDB.select('SELECT ArtistID, ArtistName from artists WHERE ArtistID=?', [artistid])
	
	if any(artistid in x for x in artistlist):
		logger.info(artistlist[0][1] + u" is already in the database, skipping")
		return
	
	artist = mb.getArtist(artistid)
	
	if artist['artist_name'].startswith('The '):
		sortname = artist['artist_name'][4:]
	else:
		sortname = artist['artist_name']
		

	
	controlValueDict = {"ArtistID": 	artistid}
	newValueDict = {"ArtistName": 		artist['artist_name'],
					"ArtistSortName": 	sortname,
					"DateAdded": 		helpers.today(),
					"Status": 			"Loading"}
	
	myDB.upsert("artists", newValueDict, controlValueDict)

	for rg in artist['releasegroups']:
		
		rgid = rg['id']
					
		try:	
			releaseid = mb.getReleaseGroup(rgid)
		except Exception, e:
			logger.info('Unable to get release information for %s - it may not be a valid release group' % rg['title'])
			continue
			
		release = mb.getRelease(releaseid)
	
		logger.info(u"Now adding album: " + release['title']+ " to the database")
		controlValueDict = {"AlbumID": 	release['id']}
		newValueDict = {"ArtistID":			artistid,
						"ArtistName": 		artist['artist_name'],
						"AlbumTitle":		rg['title'],
						"AlbumASIN":		release['asin'],
						"ReleaseDate":		release['date'],
						"DateAdded":		helpers.today(),
						"Status":			"Skipped"
						}
		
		myDB.upsert("albums", newValueDict, controlValueDict)

		latestrelease = myDB.select("SELECT ReleaseDate, DateAdded from albums WHERE AlbumID=?", [release['id']])		
		
		if latestrelease[0][0] > latestrelease[0][1]:
			logger.info(release['title'] + u" is an upcoming album. Setting its status to 'Wanted'...")
			controlValueDict = {"AlbumID": 	release['id']}
			newValueDict = {"Status":	"Wanted"}
			myDB.upsert("albums", newValueDict, controlValueDict)
						
		for track in release['tracks']:
		
			myDB.action('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', [artistid, artist['artist_name'], rg['title'], release['asin'], release['id'], track['title'], track['duration'], track['id']])
			
	controlValueDict = {"ArtistID": 	artistid}
	newValueDict = {"Status": 			"Active"}
	
	myDB.upsert("artists", newValueDict, controlValueDict)