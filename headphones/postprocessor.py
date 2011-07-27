import os
import time

import urllib, shutil, re

from lib.beets.mediafile import MediaFile
import lib.musicbrainz2.webservice as ws

import headphones
from headphones import db, albumart, logger, helpers

def checkFolder():

	myDB = db.DBConnection()
	snatched = myDB.select('SELECT * from snatched WHERE Status="Snatched"')

	for album in snatched:
		
		if album['FolderName']:
		
			album_path = os.path.join(headphones.DOWNLOAD_DIR, album['FolderName'])

			if os.path.exists(album_path):
				verify(album['AlbumID'], album_path)

def verify(albumid, albumpath):

	myDB = db.DBConnection()
	release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
	tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])
	
	downloaded_track_list = []
	for r,d,f in os.walk(albumpath):
		for files in f:
			if any(files.endswith(x) for x in (".mp3", ".flac", ".aac", ".ogg", ".ape")):
				downloaded_track_list.append(os.path.join(r, files))	
	
	# test #1: metadata - usually works
	for downloaded_track in downloaded_track_list:
		try:
			f = MediaFile(downloaded_track)
		except:
			continue
		if helpers.latinToAscii(f.artist.lower()).encode('UTF-8') == helpers.latinToAscii(release['ArtistName'].lower()).encode('UTF-8') and helpers.latinToAscii(f.album.lower()).encode('UTF-8') == helpers.latinToAscii(release['AlbumTitle'].lower()).encode('UTF-8'):
			doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
			return
			
	# test #2: filenames
	for downloaded_track in downloaded_track_list:
		track_name = os.path.splitext(downloaded_track)[0]
		split_track_name = re.sub('[\.\-\_]', ' ', track_name).lower()
		for track in tracks:
			if helpers.latinToAscii(track['TrackTitle'].lower()).encode('UTF-8') in helpers.latinToAscii(split_track_name).encode('UTF-8'):
				doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
				return
			
	# test #3: number of songs and duration
	db_track_duration = 0
	downloaded_track_duration = 0
	
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
			delta = abs(downloaded_track_duration - db_track_duration)
			if delta < 240:
				doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list)
				return
			
	logger.warn('Could not identify album: %s. It may not be the intended album.' % albumpath)
	myDB.action('UPDATE snatched SET status = "Unprocessed" WHERE AlbumID=?', [albumid])
			
def doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list):

	logger.info('Starting post-processing for: %s - %s' % (release['ArtistName'], release['AlbumTitle']))

	if headphones.ADD_ALBUM_ART:
		addAlbumArt(albumid, downloaded_track_list)
	
	if headphones.CLEANUP_FILES:
		cleanupFiles(albumpath)
		
	if headphones.CORRECT_METADATA:
		correctMetadata(albumid, release, downloaded_track_list)
		
	if headphones.RENAME_FILES:
		renameFiles(albumpath, downloaded_track_list, release)
	
	if headphones.MOVE_FILES and headphones.DESTINATION_DIR:
		moveFiles(albumpath, release, tracks)
		
	myDB = db.DBConnection()
	myDB.action('UPDATE albums SET status = "Downloaded" WHERE AlbumID=?', [albumid])
	myDB.action('UPDATE snatched SET status = "Processed" WHERE AlbumID=?', [albumid])
	logger.info('Post-processing for %s - %s complete' % (release['ArtistName'], release['AlbumTitle']))
	
		
def addAlbumArt(albumid, downloaded_track_list):

	album_art_path = albumart.getAlbumArt(albumid)
	
	artwork = urllib.urlopen(album_art_path).read()
	
	for downloaded_track in downloaded_track_list:
		try:
			f = MediaFile(downloaded_track)
		except:
			continue
			
		f.art = artwork
		f.save()
	
def cleanupFiles(albumpath):

	for r,d,f in os.walk(albumpath):
		for files in f:
			if not any(files.endswith(x) for x in (".mp3", ".flac", ".aac", ".ogg", ".ape", ".m4a")):
				os.remove(os.path.join(r, files))
				
def moveFiles(albumpath, release, tracks):

	try:
		year = release['ReleaseDate'][:4]
	except TypeError:
		year = ''

	values = {	'artist':	release['ArtistName'],
				'album':	release['AlbumTitle'],
				'year':		year
			}
			
	
	folder = helpers.replace_all(headphones.FOLDER_FORMAT, values)
	
	destination_path = os.path.join(headphones.DESTINATION_DIR, folder)
	
	try:
		os.makedirs(destination_path)
	except Exception, e:
		logger.error('Could not create folder for %s. Not moving' % release['AlbumName'])
		return
		
	for r,d,f in os.walk(albumpath):
		for files in f:
			shutil.move(os.path.join(r, files), destination_path)
			
	try:
		os.rmdir(albumpath)
	except Exception, e:
		logger.error('Could not remove directory: %s. %s' % (albumpath, e))
		
def correctMetadata(albumid, release, downloaded_track_list):
	
	pass

def renameFiles(albumpath, downloaded_track_list, release):

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
			
		tracknumber = '%02d' % f.track
			
		values = {	'tracknumber':	tracknumber,
					'title':		f.title,
					'artist':		release['ArtistName'],
					'album':		release['AlbumTitle'],
					'year':			year
					}
					
		ext = os.path.splitext(downloaded_track)[1]
		
		new_file_name = helpers.replace_all(headphones.FILE_FORMAT, values).replace('/','_') + ext

		new_file = os.path.join(albumpath, new_file_name)
		
		shutil.move(downloaded_track, new_file)