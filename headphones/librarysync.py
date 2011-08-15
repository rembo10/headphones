import os
import glob

from lib.beets.mediafile import MediaFile

import headphones
from headphones import db, logger

def LibraryScan():

	if not headphones.MUSIC_DIR:
		return

	unmatched_files = []
	new_artists = []
	
	myDB = db.DBConnection()
	
	for r,d,f in os.walk(headphones.MUSIC_DIR):
		for files in f:
			# MEDIA_FORMATS = music file extensions, e.g. mp3, flac, etc
			if any(files.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				
				file = unicode(os.path.join(r, files), "utf-8")
				print repr(file)
				# Try to read the metadata
				try:
					f = MediaFile(file)
				except:
					logger.error('Cannot read file: ' + file)
					continue				
				
				# Try to match on metadata first, 
				if f.mb_trackid:
					print 'has track id:' + repr(f.mb_trackid)
					# Wondering if theres a better way to do this -> do one thing if the row exists,
					# do something else if it doesn't
					track = myDB.action('SELECT TrackID from tracks WHERE TrackID=?', [f.mb_trackid]).fetchone()
		
					if not track:
						if f.albumartist:
							new_artists.append(f.albumartist)
						elif f.artist:
							new_artists.append(f.artist)
						else:
							unmatched_files.append(file)
					
					else:
						myDB.action('UPDATE tracks SET Location=?, BitRate=? WHERE TrackID=?', [file, f.bitrate, track['TrackID']])
						continue
				
				elif f.albumartist and f.album and f.title:

					track = myDB.action('SELECT TrackID from tracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [f.albumartist, f.album, f.title]).fetchone()
					
					if not track:
						new_artists.append(f.albumartist)
						
					else:
						myDB.action('UPDATE tracks SET Location=?, BitRate=? WHERE TrackID=?', [file, f.bitrate, track['TrackID']])
						
				elif f.artist and f.album and f.title:

					track = myDB.action('SELECT TrackID from tracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [f.artist, f.album, f.title]).fetchone()
					
					if not track:
						new_artists.append(file)
					else:
						myDB.action('UPDATE tracks SET Location=?, BitRate=? WHERE TrackID=?', [file, f.bitrate, track['TrackID']])
						
				else:
					continue
					
	# Try to parse the unmatched files based on the folder & file formats in the config
	for file in unmatched_files:
		# Will do later
		pass
	
	# Now check empty file paths to see if we can find a match based on their folder format
	tracks = myDB.select('SELECT * from tracks WHERE Location=NULL')
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
		
	
		albumvalues = {	'artist':	artist,
						'album':	album,
						'year':		year,
						'first':	firstchar,
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
		
		full_path_to_file = os.path.join(headphones.MUSIC_DIR, folder, new_file_name)
		
		print 'Full path to file is: ' + repr(full_path_to_file)
		
		if glob.glob(full_path_to_file):
			myDB.action('UPDATE tracks SET Location=? WHERE TrackID=?', [full_path_to_file, track['TrackID']])
			
			# Try to insert the appropriate track id so we don't have to keep doing this
			try:
				f = MediaFile(full_path_to_file)
				f.mb_trackid = track['TrackID']
				myDB.action('UPDATE tracks SET BitRate=? WHERE TrackID=?', [f.bitrate, track['TrackID']])
				f.save()
			except:
				logger.error('Error embedding track id into: %s' % full_path_to_file)
				
	# Lastly, clean up any old paths that don't exist
	tracks = myDB.select('SELECT Location, TrackID from tracks WHERE Location IS NOT NULL')
	for track in tracks:
		if not os.path.isfile(track['Location']):
			myDB.action('UPDATE tracks SET Location=? WHERE TrackID=?', [None, track['TrackID']])
	
	# Clean up the new artist list
	unique_artists = {}.fromkeys(new_artists).keys()
	current_artists = myDB.action('SELECT ArtistName from artists').fetchall()
	
	artist_list = [f for f in unique_artists if f not in current_artists]
	
	logger.info('Found %i artists to import: ' % len(artist_list))