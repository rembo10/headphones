import os
import glob

from lib.beets.mediafile import MediaFile

import headphones
from headphones import db, logger, helpers, importer

def libraryScan(dir=None):

	if not dir:
		dir = headphones.MUSIC_DIR
		
	try:
		dir = str(dir)
	except UnicodeEncodeError:
		dir = unicode(dir).encode('unicode_escape')
		
	if not os.path.isdir(dir):
		logger.warn('Cannot find directory: %s. Not scanning' % dir)
		return

	myDB = db.DBConnection()
	
	# Clean up bad filepaths
	tracks = myDB.select('SELECT Location, TrackID from tracks WHERE Location IS NOT NULL')
	
	for track in tracks:
		if not os.path.isfile(track['Location'].encode(headphones.SYS_ENCODING)):
			myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [None, None, None, track['TrackID']])

	logger.info('Scanning music directory: %s' % dir)

	new_artists = []
	bitrates = []

	myDB.action('DELETE from have')
	
	for r,d,f in os.walk(dir):
		for files in f:
			# MEDIA_FORMATS = music file extensions, e.g. mp3, flac, etc
			if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):

				song = os.path.join(r, files)
				file = unicode(os.path.join(r, files), headphones.SYS_ENCODING, errors='replace')

				# Try to read the metadata
				try:
					f = MediaFile(song)

				except:
					logger.error('Cannot read file: ' + file)
					continue
					
				# Grab the bitrates for the auto detect bit rate option
				if f.bitrate:
					bitrates.append(f.bitrate)
				
				# Try to find a match based on artist/album/tracktitle
				if f.albumartist:
					f_artist = f.albumartist
				elif f.artist:
					f_artist = f.artist
				else:
					continue
				
				if f_artist and f.album and f.title:

					track = myDB.action('SELECT TrackID from tracks WHERE CleanName LIKE ?', [helpers.cleanName(f_artist +' '+f.album+' '+f.title)]).fetchone()
						
					if not track:
						track = myDB.action('SELECT TrackID from tracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [f_artist, f.album, f.title]).fetchone()
					
					if track:
						myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [file, f.bitrate, f.format, track['TrackID']])
						continue		
				
				# Try to match on mbid if available and we couldn't find a match based on metadata
				if f.mb_trackid:

					# Wondering if theres a better way to do this -> do one thing if the row exists,
					# do something else if it doesn't
					track = myDB.action('SELECT TrackID from tracks WHERE TrackID=?', [f.mb_trackid]).fetchone()
		
					if track:
						myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [file, f.bitrate, f.format, track['TrackID']])
						continue				
				
				# if we can't find a match in the database on a track level, it might be a new artist or it might be on a non-mb release
				new_artists.append(f_artist)
				
				# The have table will become the new database for unmatched tracks (i.e. tracks with no associated links in the database				
				myDB.action('INSERT INTO have (ArtistName, AlbumTitle, TrackNumber, TrackTitle, TrackLength, BitRate, Genre, Date, TrackID, Location, CleanName, Format) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [f_artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid, file, helpers.cleanName(f_artist+' '+f.album+' '+f.title), f.format])

	logger.info('Completed scanning of directory: %s' % dir)
	logger.info('Checking filepaths to see if we can find any matches')

	# Now check empty file paths to see if we can find a match based on their folder format
	tracks = myDB.select('SELECT * from tracks WHERE Location IS NULL')
	for track in tracks:
	
		release = myDB.action('SELECT * from albums WHERE AlbumID=?', [track['AlbumID']]).fetchone()

		try:
			year = release['ReleaseDate'][:4]
		except TypeError:
			year = ''
			
		artist = release['ArtistName'].replace('/', '_')
		album = release['AlbumTitle'].replace('/', '_')
	
		if release['ArtistName'].startswith('The '):
			sortname = release['ArtistName'][4:]
		else:
			sortname = release['ArtistName']
		
		if sortname.isdigit():
			firstchar = '0-9'
		else:
			firstchar = sortname[0]
			
		lowerfirst = firstchar.lower()
		
		albumvalues = {	'artist':	artist,
						'album':	album,
						'year':		year,
						'first':	firstchar,
						'lowerfirst':	lowerfirst
					}
				
		
		folder = helpers.replace_all(headphones.FOLDER_FORMAT, albumvalues)
		folder = folder.replace('./', '_/').replace(':','_').replace('?','_')
		
		if folder.endswith('.'):
			folder = folder.replace(folder[len(folder)-1], '_')

		if not track['TrackNumber']:
			tracknumber = ''
		else:
			tracknumber = '%02d' % track['TrackNumber']
			
		trackvalues = {	'tracknumber':	tracknumber,
						'title':		track['TrackTitle'],
						'artist':		release['ArtistName'],
						'album':		release['AlbumTitle'],
						'year':			year
						}
		
		new_file_name = helpers.replace_all(headphones.FILE_FORMAT, trackvalues).replace('/','_') + '.*'
		
		new_file_name = new_file_name.replace('?','_').replace(':', '_')
		
		full_path_to_file = os.path.normpath(os.path.join(headphones.MUSIC_DIR, folder, new_file_name)).encode(headphones.SYS_ENCODING, 'replace')

		match = glob.glob(full_path_to_file)
		
		if match:

			logger.info('Found a match: %s. Writing MBID to metadata' % match[0])
			
			unipath = unicode(match[0], headphones.SYS_ENCODING, errors='replace')

			myDB.action('UPDATE tracks SET Location=? WHERE TrackID=?', [unipath, track['TrackID']])
			myDB.action('DELETE from have WHERE Location=?', [unipath])
			
			# Try to insert the appropriate track id so we don't have to keep doing this
			try:
				f = MediaFile(match[0])
				f.mb_trackid = track['TrackID']
				f.save()
				myDB.action('UPDATE tracks SET BitRate=?, Format=? WHERE TrackID=?', [f.bitrate, f.format, track['TrackID']])

				logger.debug('Wrote mbid to track: %s' % match[0])

			except:
				logger.error('Error embedding track id into: %s' % match[0])
				continue

	logger.info('Done checking empty filepaths')
	logger.info('Done syncing library with directory: %s' % dir)
	
	# Clean up the new artist list
	unique_artists = {}.fromkeys(new_artists).keys()
	current_artists = myDB.select('SELECT ArtistName, ArtistID from artists')
	
	artist_list = [f for f in unique_artists if f.lower() not in [x[0].lower() for x in current_artists]]
	
	# Update track counts
	logger.info('Updating track counts')

	for artist in current_artists:
		havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID like ? AND Location IS NOT NULL', [artist['ArtistID']])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['ArtistName']]))
		myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, artist['ArtistID']])
		
	logger.info('Found %i new artists' % len(artist_list))

	if len(artist_list):
		if headphones.ADD_ARTISTS:
			logger.info('Importing %i new artists' % len(artist_list))
			importer.artistlist_to_mbids(artist_list)
		else:
			logger.info('To add these artists, go to Manage->Manage New Artists')
			headphones.NEW_ARTISTS = artist_list
	
	if headphones.DETECT_BITRATE:
		headphones.PREFERRED_BITRATE = sum(bitrates)/len(bitrates)/1000
