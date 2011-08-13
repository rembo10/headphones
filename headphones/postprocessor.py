import os
import time

import urllib, shutil, re

import lib.beets as beets
from lib.beets import autotag
from lib.beets.mediafile import MediaFile

import headphones
from headphones import db, albumart, logger, helpers

def checkFolder():

	myDB = db.DBConnection()
	snatched = myDB.select('SELECT * from snatched WHERE Status="Snatched"')

	for album in snatched:
		
		if album['FolderName']:
		
			album_path = os.path.join(headphones.DOWNLOAD_DIR, album['FolderName'])

			if os.path.exists(album_path):
				logger.debug('Found %s. Verifying....' % album['FolderName'])
				verify(album['AlbumID'], album_path)

def verify(albumid, albumpath):

	myDB = db.DBConnection()
	release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
	tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])

	if not release or not tracks:
		#the result of a manual post-process on an album that hasn't been inserted
		#from an RSS feed or etc
		#TODO: This should be a call to a class method.. copied it out of importer with only minor changes
		#TODO: odd things can happen when there are diacritic characters in the folder name, need to translate them?
		import mb
		try:	
			release_dict = mb.getReleaseGroup(albumid)
		except Exception, e:
			logger.info('Unable to get release information for manual album with rgid: ' + albumid)

		if not release_dict:
			logger.warn('Unable to get release information for manual album with rgid: ' + albumid)
			return

		logger.info(u"Now adding/updating artist: " + release_dict['artist_name'])
		
		if release_dict['artist_name'].startswith('The '):
			sortname = release_dict['artist_name'][4:]
		else:
			sortname = release_dict['artist_name']
			
	
		controlValueDict = {"ArtistID": 	release_dict['artist_id']}
		newValueDict = {"ArtistName": 		release_dict['artist_name'],
						"ArtistSortName": 	sortname,
						"DateAdded": 		helpers.today(),
						"Status": 			"Paused"}
		logger.info("ArtistID:ArtistName: " + release_dict['artist_id'] + " : " + release_dict['artist_name'])

		if headphones.INCLUDE_EXTRAS:
			newValueDict['IncludeExtras'] = 1
		
		myDB.upsert("artists", newValueDict, controlValueDict)

		logger.info(u"Now adding album: " + release_dict['title'])
		controlValueDict = {"AlbumID": 	albumid}
		
		newValueDict = {"ArtistID":			release_dict['artist_id'],
						"ArtistName": 		release_dict['artist_name'],
						"AlbumTitle":		release_dict['title'],
						"AlbumASIN":		release_dict['asin'],
						"ReleaseDate":		release_dict['releasedate'],
						"DateAdded":		helpers.today(),
						"Type":				release_dict['type'],
						"Status":			"Snatched"
						}

		myDB.upsert("albums", newValueDict, controlValueDict)
		
		# I changed the albumid from releaseid -> rgid, so might need to delete albums that have a releaseid
		for rel in release_dict['releaselist']:
			myDB.action('DELETE from albums WHERE AlbumID=?', [rel['releaseid']])
			myDB.action('DELETE from tracks WHERE AlbumID=?', [rel['releaseid']])
		
		myDB.action('DELETE from tracks WHERE AlbumID=?', [albumid])
		for track in release_dict['tracks']:
		
			controlValueDict = {"TrackID": 	track['id'],
								"AlbumID":	albumid}
			newValueDict = {"ArtistID":		release_dict['artist_id'],
						"ArtistName": 		release_dict['artist_name'],
						"AlbumTitle":		release_dict['title'],
						"AlbumASIN":		release_dict['asin'],
						"TrackTitle":		track['title'],
						"TrackDuration":	track['duration'],
						"TrackNumber":		track['number']
						}
		
			myDB.upsert("tracks", newValueDict, controlValueDict)
			
		controlValueDict = {"ArtistID": 	release_dict['artist_id']}
		newValueDict = {"Status":			"Paused"}
		
		myDB.upsert("artists", newValueDict, controlValueDict)
		logger.info(u"Addition complete for: " + release_dict['title'] + " - " + release_dict['artist_name'])

		release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
		tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])
	
	downloaded_track_list = []
	
	for r,d,f in os.walk(albumpath):
		for files in f:
			if any(files.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				downloaded_track_list.append(os.path.join(r, files))	
	
	# test #1: metadata - usually works
	logger.debug('Verifying metadata...')

	for downloaded_track in downloaded_track_list:
		try:
			f = MediaFile(downloaded_track)
		except:
			continue
			
		metaartist = helpers.latinToAscii(f.artist.lower()).encode('UTF-8')
		dbartist = helpers.latinToAscii(release['ArtistName'].lower()).encode('UTF-8')
		metaalbum = helpers.latinToAscii(f.album.lower()).encode('UTF-8')
		dbalbum = helpers.latinToAscii(release['AlbumTitle'].lower()).encode('UTF-8')
		
		logger.debug('Matching metadata artist: %s with artist name: %s' % (metaartist, dbartist))
		logger.debug('Matching metadata album: %s with album name: %s' % (metaalbum, dbalbum))
		
		if metaartist == dbartist and metaalbum == dbalbum:
			doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
			return
			
	# test #2: filenames
	logger.debug('Metadata check failed. Verifying filenames...')
	for downloaded_track in downloaded_track_list:
		track_name = os.path.splitext(downloaded_track)[0]
		split_track_name = re.sub('[\.\-\_]', ' ', track_name).lower()
		for track in tracks:
			
			dbtrack = helpers.latinToAscii(track['TrackTitle'].lower()).encode('UTF-8')
			filetrack = helpers.latinToAscii(split_track_name).encode('UTF-8')
			logger.debug('Checking if track title: %s is in file name: %s' % (dbtrack, filetrack))
		
			if dbtrack in filetrack:
				doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
				return
			
	# test #3: number of songs and duration
	logger.debug('Filename check failed. Verifying album length...')
	db_track_duration = 0
	downloaded_track_duration = 0
	
	logger.debug('Total music files in %s: %i' % (albumpath, len(downloaded_track_list)))
	logger.debug('Total tracks for this album in the database: %i' % len(tracks))
	if len(tracks) == len(downloaded_track_list):
	
		for track in tracks:
			try:
				db_track_duration += track['TrackDuration']/1000
			except:
				downloaded_track_duration = False
				break
				
		for downloaded_track in downloaded_track_list:
			try:
				f = MediaFile(downloaded_track)
				downloaded_track_duration += f.length
			except:
				downloaded_track_duration = False
				break
		
		if downloaded_track_duration and db_track_duration:
			logger.debug('Downloaded album duration: %i' % downloaded_track_duration)
			logger.debug('Database track duration: %i' % db_track_duration)
			delta = abs(downloaded_track_duration - db_track_duration)
			if delta < 240:
				doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
				return
			
	logger.warn('Could not identify album: %s. It may not be the intended album.' % albumpath)
	myDB.action('UPDATE snatched SET status = "Unprocessed" WHERE AlbumID=?', [albumid])
	processed = re.search(r' \(Unprocessed\)(?:\[\d+\])?', albumpath)
	if not processed:
		renameUnprocessedFolder(albumpath)
	else:
		logger.info("Already marked as unprocessed: " + albumpath)
			
def doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list):

	logger.info('Starting post-processing for: %s - %s' % (release['ArtistName'], release['AlbumTitle']))

	if headphones.EMBED_ALBUM_ART or headphones.ADD_ALBUM_ART:
	
		album_art_path = albumart.getAlbumArt(albumid)
		artwork = urllib.urlopen(album_art_path).read()
	
	if headphones.EMBED_ALBUM_ART:
		embedAlbumArt(artwork, downloaded_track_list)
	
	if headphones.CLEANUP_FILES:
		cleanupFiles(albumpath)
		
	if headphones.ADD_ALBUM_ART:
		addAlbumArt(artwork, albumpath)
		
	if headphones.CORRECT_METADATA:
		correctMetadata(albumid, release, downloaded_track_list)
		
	if headphones.RENAME_FILES:
		renameFiles(albumpath, downloaded_track_list, release)
	
	if headphones.MOVE_FILES and headphones.DESTINATION_DIR:
		albumpath = moveFiles(albumpath, release, tracks)
	
	if headphones.MOVE_FILES and not headphones.DESTINATION_DIR:
		logger.error('No DESTINATION_DIR has been set. Set "Destination Directory" to the parent directory you want to move the files to')
		pass
		
	myDB = db.DBConnection()
	# There's gotta be a better way to update the have tracks - sqlite
	
	trackcount = myDB.select('SELECT HaveTracks from artists WHERE ArtistID=?', [release['ArtistID']])
	
	if not trackcount[0][0]:
		cur_track_count = 0
	else:
		cur_track_count = trackcount[0][0]
		
	new_track_count = cur_track_count + len(downloaded_track_list)
	myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [new_track_count, release['ArtistID']])
	myDB.action('UPDATE albums SET status = "Downloaded" WHERE AlbumID=?', [albumid])
	myDB.action('UPDATE snatched SET status = "Processed" WHERE AlbumID=?', [albumid])
	updateHave(albumpath)
	
	logger.info('Post-processing for %s - %s complete' % (release['ArtistName'], release['AlbumTitle']))
	
def embedAlbumArt(artwork, downloaded_track_list):
	logger.info('Embedding album art')
	
	for downloaded_track in downloaded_track_list:
		try:
			f = MediaFile(downloaded_track)
		except:
			logger.error('Could not read %s. Not adding album art' % downloaded_track)
		
		logger.debug('Adding album art to: %s' % downloaded_track)
		f.art = artwork
		f.save()
		
def addAlbumArt(artwork, albumpath):
	logger.info('Adding album art to folder')
	
	artwork_file_name = os.path.join(albumpath, 'folder.jpg')
	file = open(artwork_file_name, 'wb')
	file.write(artwork)
	file.close()
	
def cleanupFiles(albumpath):
	logger.info('Cleaning up files')
	for r,d,f in os.walk(albumpath):
		for files in f:
			if not any(files.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				logger.debug('Removing: %s' % files)
				try:
					os.remove(os.path.join(r, files))
				except Exception, e:
					logger.error('Could not remove file: %s. Error: %s' % (files, e))
					
def moveFiles(albumpath, release, tracks):

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
	

	values = {	'artist':	artist,
				'album':	album,
				'year':		year,
				'first':	firstchar,
			}
			
	
	folder = helpers.replace_all(headphones.FOLDER_FORMAT, values)
	folder = folder.replace('./', '_/').replace(':','_').replace('?','_')
	
	if folder.endswith('.'):
		folder = folder.replace(folder[len(folder)-1], '_')
	
	destination_path = os.path.normpath(os.path.join(headphones.DESTINATION_DIR, folder))
	
	if os.path.exists(destination_path):
		i = 1
		while True:
			newfolder = folder + '[%i]' % i
			destination_path = os.path.normpath(os.path.join(headphones.DESTINATION_DIR, newfolder))
			if os.path.exists(destination_path):
				i += 1
			else:
				folder = newfolder
				break
	
	logger.info('Moving files from %s to %s' % (albumpath, destination_path))
	
	try:
		os.makedirs(destination_path)
	
	except Exception, e:
		logger.error('Could not create folder for %s. Not moving: %s' % (release['AlbumTitle'], e))
		return albumpath
		
	for r,d,f in os.walk(albumpath):
		for files in f:
			shutil.move(os.path.join(r, files), destination_path)
			
	# Chmod the directories using the folder_format (script courtesy of premiso!)
	folder_list = folder.split('/')
	
	temp_f = headphones.DESTINATION_DIR
	for f in folder_list:
		temp_f = os.path.join(temp_f, f)
		os.chmod(temp_f, int(headphones.FOLDER_PERMISSIONS, 8))
	
	try:
		shutil.rmtree(albumpath)
	except Exception, e:
		logger.error('Could not remove directory: %s. %s' % (albumpath, e))
	
	return destination_path
		
def correctMetadata(albumid, release, downloaded_track_list):
	
	logger.info('Writing metadata')
	items = []
	for downloaded_track in downloaded_track_list:
		items.append(beets.library.Item.from_path(downloaded_track))
	
	cur_artist, cur_album, out_tuples, rec = autotag.tag_album(items, search_artist=release['ArtistName'], search_album=release['AlbumTitle'])
	
	if rec == 'RECOMMEND_NONE':
		logger.warn('No accurate album match found for %s, %s -  not writing metadata' % (release['ArtistName'], release['AlbumTitle']))
		return
	
	distance, items, info = out_tuples[0]
	logger.debug('Beets recommendation: %s' % rec)
	autotag.apply_metadata(items, info)
	
	for item in items:
		item.write()

def renameFiles(albumpath, downloaded_track_list, release):
	logger.info('Renaming files')
	try:
		year = release['ReleaseDate'][:4]
	except TypeError:
		year = ''
	# Until tagging works better I'm going to rely on the already provided metadata

	for downloaded_track in downloaded_track_list:
		try:
			f = MediaFile(downloaded_track)
		except:
			continue
			
		if not f.track:
			tracknumber = ''
		else:
			tracknumber = '%02d' % f.track
		
		if not f.title:
			basename = os.path.basename(downloaded_track)
			title = os.path.splitext(basename)[0]
		else:
			title = f.title
			
		values = {	'tracknumber':	tracknumber,
					'title':		title,
					'artist':		release['ArtistName'],
					'album':		release['AlbumTitle'],
					'year':			year
					}
					
		ext = os.path.splitext(downloaded_track)[1]
		
		new_file_name = helpers.replace_all(headphones.FILE_FORMAT, values).replace('/','_') + ext
		
		new_file_name = new_file_name.replace('?','_').replace(':', '_')

		new_file = os.path.join(albumpath, new_file_name)
		
		logger.debug('Renaming %s ---> %s' % (downloaded_track, new_file_name))
		try:
			os.rename(downloaded_track, new_file)
		except Exception, e:
			logger.error('Error renaming file: %s. Error: %s' % (downloaded_track, e))
			continue
		
def updateHave(albumpath):

	results = []
	
	for r,d,f in os.walk(albumpath):
		for files in f:
			if any(files.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				results.append(os.path.join(r, files))
	
	if results:
	
		myDB = db.DBConnection()
	
		for song in results:
			try:
				f = MediaFile(song)
				#logger.debug('Reading: %s' % song.decode('UTF-8'))
			except:
				logger.warn('Could not read file: %s' % song)
				continue
			else:	
				if f.albumartist:
					artist = f.albumartist
				elif f.artist:
					artist = f.artist
				else:
					continue
				
				myDB.action('INSERT INTO have VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?)', [artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid])
				
def renameUnprocessedFolder(albumpath):
	
	i = 0
	while True:
		if i == 0:
			new_folder_name = albumpath + ' (Unprocessed)'
		else:
			new_folder_name = albumpath + ' (Unprocessed)[%i]' % i
		
		if os.path.exists(new_folder_name):
			i += 1
			
		else:
			os.rename(albumpath, new_folder_name)
			return
			
def forcePostProcess():
	
	if not headphones.DOWNLOAD_DIR:
		logger.error('No DOWNLOAD_DIR has been set. Set "Music Download Directory:" to your SAB download directory on the settings page.')
		return
	else:
		download_dir = headphones.DOWNLOAD_DIR
		
	logger.info('Checking to see if there are any folders to process in download_dir: %s' % download_dir)
	# Get a list of folders in the download_dir
	folders = [d for d in os.listdir(download_dir) if os.path.isdir(os.path.join(download_dir, d))]
	
	if len(folders):
		logger.info('Found %i folders: %s' % (len(folders), str(folders)))
		pass
	else:
		logger.info('Found no folders to process in: %s' % download_dir)
		return
	
	# Parse the folder names to get artist album info
	for folder in folders:

		folder = unicode(folder)
	
		albumpath = os.path.join(download_dir, folder)
		
		try:
			name, album, year = helpers.extract_data(folder)
		except:
			logger.info("Couldn't parse " + folder + " into any valid format.")
			continue
		if name and album and year:
			
			myDB = db.DBConnection()
			release = myDB.action('SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE ArtistName=? and AlbumTitle=?', [name, album]).fetchone()
			if release:
				logger.info('Found a match in the database: %s - %s. Verifying to make sure it is the correct album' % (release['ArtistName'], release['AlbumTitle']))
				verify(release['AlbumID'], albumpath)
			else:
				logger.info('Querying MusicBrainz for the release group id for: %s - %s' % (name, album))
				from headphones import mb
				try:
					rgid = mb.findAlbumID(name, album)
				except:
					logger.error('Can not get release information for this album')
					continue
				if rgid:
					verify(rgid, albumpath)
			
	