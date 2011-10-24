import os
import cherrypy

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import time
import threading

import headphones

from headphones import logger, searcher, db, importer, mb, lastfm, librarysync
from headphones.helpers import checked, radio



def serve_template(templatename, **kwargs):

	interface_dir = os.path.join(str(headphones.PROG_DIR), 'data/interfaces/')
	template_dir = os.path.join(str(interface_dir), headphones.INTERFACE)
	
	_hplookup = TemplateLookup(directories=[template_dir])
	
	try:
		template = _hplookup.get_template(templatename)
		return template.render(**kwargs)
	except:
		return exceptions.html_error_template().render()
	
class WebInterface(object):
	
	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		myDB = db.DBConnection()
		artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
		return serve_template(templatename="index.html", title="Home", artists=artists)
	home.exposed = True

	def artistPage(self, ArtistID):
		myDB = db.DBConnection()
		artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
		albums = myDB.select('SELECT * from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])
		return serve_template(templatename="artist.html", title=artist['ArtistName'], artist=artist, albums=albums)
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):
		myDB = db.DBConnection()
		album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
		tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [AlbumID])
		description = myDB.action('SELECT * from descriptions WHERE ReleaseGroupID=?', [AlbumID]).fetchone()
		title = album['ArtistName'] + ' - ' + album['AlbumTitle']
		return serve_template(templatename="album.html", title=title, album=album, tracks=tracks, description=description)
	albumPage.exposed = True
	
	
	def search(self, name, type):
		if len(name) == 0:
			raise cherrypy.HTTPRedirect("home")
		if type == 'artist':
			searchresults = mb.findArtist(name, limit=100)
		else:
			searchresults = mb.findRelease(name, limit=100)
		return serve_template(templatename="searchresults.html", title='Search Results for: "' + name + '"', searchresults=searchresults, type=type)
	search.exposed = True

	def addArtist(self, artistid):
		threading.Thread(target=importer.addArtisttoDB, args=[artistid]).start()
		time.sleep(5)
		threading.Thread(target=lastfm.getSimilar).start()
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % artistid)
	addArtist.exposed = True
	
	def getExtras(self, ArtistID):
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'IncludeExtras': 1}
		myDB.upsert("artists", newValueDict, controlValueDict)
		threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, True]).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	getExtras.exposed = True
	
	def removeExtras(self, ArtistID):
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'IncludeExtras': 0}
		myDB.upsert("artists", newValueDict, controlValueDict)
		extraalbums = myDB.select('SELECT AlbumID from albums WHERE ArtistID=? AND Status="Skipped" AND Type!="Album"', [ArtistID])
		for album in extraalbums:
			myDB.action('DELETE from tracks WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
			myDB.action('DELETE from albums WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	removeExtras.exposed = True
	
	def pauseArtist(self, ArtistID):
		logger.info(u"Pausing artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Paused'}
		myDB.upsert("artists", newValueDict, controlValueDict)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):
		logger.info(u"Resuming artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Active'}
		myDB.upsert("artists", newValueDict, controlValueDict)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):
		logger.info(u"Deleting all traces of artist: " + ArtistID)
		myDB = db.DBConnection()
		myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])
		raise cherrypy.HTTPRedirect("home")
	deleteArtist.exposed = True
	
	def refreshArtist(self, ArtistID):
		importer.addArtisttoDB(ArtistID)	
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	refreshArtist.exposed=True	
	
	def markAlbums(self, ArtistID=None, action=None, **args):
		myDB = db.DBConnection()
		if action == 'WantedNew':
			newaction = 'Wanted'
		else:
			newaction = action
		for mbid in args:
			controlValueDict = {'AlbumID': mbid}
			newValueDict = {'Status': newaction}
			myDB.upsert("albums", newValueDict, controlValueDict)
			if action == 'Wanted':
				searcher.searchNZB(mbid, new=False)
			if action == 'WantedNew':
				searcher.searchNZB(mbid, new=True)
		if ArtistID:
			raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		else:
			raise cherrypy.HTTPRedirect("upcoming")
	markAlbums.exposed = True
	
	def addArtists(self, **args):
		threading.Thread(target=importer.artistlist_to_mbids, args=[args, True]).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	addArtists.exposed = True
	
	def queueAlbum(self, AlbumID, ArtistID=None, new=False, redirect=None):
		logger.info(u"Marking album: " + AlbumID + "as wanted...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Wanted'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		searcher.searchNZB(AlbumID, new)
		if ArtistID:
			raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		else:
			raise cherrypy.HTTPRedirect(redirect)
	queueAlbum.exposed = True

	def unqueueAlbum(self, AlbumID, ArtistID):
		logger.info(u"Marking album: " + AlbumID + "as skipped...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Skipped'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	unqueueAlbum.exposed = True
	
	def deleteAlbum(self, AlbumID, ArtistID=None):
		logger.info(u"Deleting all traces of album: " + AlbumID)
		myDB = db.DBConnection()
		myDB.action('DELETE from albums WHERE AlbumID=?', [AlbumID])
		myDB.action('DELETE from tracks WHERE AlbumID=?', [AlbumID])
		if ArtistID:
			raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
		else:
			raise cherrypy.HTTPRedirect("home")
	deleteAlbum.exposed = True

	def upcoming(self):
		myDB = db.DBConnection()
		upcoming = myDB.select("SELECT * from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")
		wanted = myDB.select("SELECT * from albums WHERE Status='Wanted'")
		return serve_template(templatename="upcoming.html", title="Upcoming", upcoming=upcoming, wanted=wanted)
	upcoming.exposed = True
	
	def manage(self):
		return serve_template(templatename="manage.html", title="Manage")
	manage.exposed = True
	
	def manageArtists(self):
		myDB = db.DBConnection()
		artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
		return serve_template(templatename="manageartists.html", title="Manage Artists", artists=artists)
	manageArtists.exposed = True	
	
	def manageNew(self):
		return serve_template(templatename="managenew.html", title="Manage New Artists")
	manageNew.exposed = True	
	
	def markArtists(self, action=None, **args):
		myDB = db.DBConnection()
		for ArtistID in args:
			if action == 'delete':
				myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])
				myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
				myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])
			elif action == 'pause':
				controlValueDict = {'ArtistID': ArtistID}
				newValueDict = {'Status': 'Paused'}
				myDB.upsert("artists", newValueDict, controlValueDict)
			elif action == 'resume':
				controlValueDict = {'ArtistID': ArtistID}
				newValueDict = {'Status': 'Active'}
				myDB.upsert("artists", newValueDict, controlValueDict)				
			else:
				# These may and probably will collide - need to make a better way to queue musicbrainz queries
				threading.Thread(target=importer.addArtisttoDB, args=[ArtistID]).start()
				time.sleep(30)
		raise cherrypy.HTTPRedirect("home")
	markArtists.exposed = True
	
	def importLastFM(self, username):
		headphones.LASTFM_USERNAME = username
		headphones.config_write()
		threading.Thread(target=lastfm.getArtists).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("home")
	importLastFM.exposed = True
	
	def importItunes(self, path):
		headphones.PATH_TO_XML = path
		headphones.config_write()
		threading.Thread(target=importer.itunesImport, args=[path]).start()
		time.sleep(10)
		raise cherrypy.HTTPRedirect("home")
	importItunes.exposed = True
	
	def musicScan(self, path, redirect=None, autoadd=0):
		headphones.ADD_ARTISTS = autoadd
		headphones.MUSIC_DIR = path
		headphones.config_write()
		try:	
			threading.Thread(target=librarysync.libraryScan).start()
		except Exception, e:
			logger.error('Unable to complete the scan: %s' % e)
		time.sleep(10)
		if redirect:
			raise cherrypy.HTTPRedirect(redirect)
		else:
			raise cherrypy.HTTPRedirect("home")
	musicScan.exposed = True
	
	def forceUpdate(self):
		from headphones import updater
		threading.Thread(target=updater.dbUpdate).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forceUpdate.exposed = True
	
	def forceSearch(self):
		from headphones import searcher
		threading.Thread(target=searcher.searchNZB).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forceSearch.exposed = True
	
	def forcePostProcess(self):
		from headphones import postprocessor
		threading.Thread(target=postprocessor.forcePostProcess).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	forcePostProcess.exposed = True
	
	def checkGithub(self):
		from headphones import versioncheck
		versioncheck.checkGithub()
		raise cherrypy.HTTPRedirect("home")
	checkGithub.exposed = True
	
	def history(self):
		myDB = db.DBConnection()
		history = myDB.select('''SELECT * from snatched order by DateAdded DESC''')
		return serve_template(templatename="history.html", title="History", history=history)
		return page
	history.exposed = True
	
	def logs(self):
		return serve_template(templatename="logs.html", title="Log", lineList=headphones.LOG_LIST)
	logs.exposed = True
	
	def clearhistory(self, type=None):
		myDB = db.DBConnection()
		if type == 'all':
			logger.info(u"Clearing all history")
			myDB.action('DELETE from snatched')
		else:
			logger.info(u"Clearing history where status is %s" % type)
			myDB.action('DELETE from snatched WHERE Status=?', [type])
		raise cherrypy.HTTPRedirect("history")
	clearhistory.exposed = True
	
	def config(self):
	
		interface_dir = os.path.join(headphones.PROG_DIR, 'data/interfaces/')
		interface_list = [ name for name in os.listdir(interface_dir) if os.path.isdir(os.path.join(interface_dir, name)) ]

		config = { 
					"http_host" : headphones.HTTP_HOST,
					"http_user" : headphones.HTTP_USERNAME,
		 			"http_port" : headphones.HTTP_PORT,
				 	"http_pass" : headphones.HTTP_PASSWORD,
					"launch_browser" : checked(headphones.LAUNCH_BROWSER),
					"sab_host" : headphones.SAB_HOST,
					"sab_user" : headphones.SAB_USERNAME,
					"sab_api" : headphones.SAB_APIKEY,
					"sab_pass" : headphones.SAB_PASSWORD,
					"sab_cat" : headphones.SAB_CATEGORY,
					"download_dir" : headphones.DOWNLOAD_DIR,
					"use_blackhole" : checked(headphones.BLACKHOLE),
					"blackhole_dir" : headphones.BLACKHOLE_DIR,
					"usenet_retention" : headphones.USENET_RETENTION,
					"use_nzbmatrix" : checked(headphones.NZBMATRIX),
					"nzbmatrix_user" : headphones.NZBMATRIX_USERNAME,
					"nzbmatrix_api" : headphones.NZBMATRIX_APIKEY,
					"use_newznab" : checked(headphones.NEWZNAB),
					"newznab_host" : headphones.NEWZNAB_HOST,
					"newznab_api" : headphones.NEWZNAB_APIKEY,
					"use_nzbsorg" : checked(headphones.NZBSORG),
					"nzbsorg_uid" : headphones.NZBSORG_UID,
					"nzbsorg_hash" : headphones.NZBSORG_HASH,
					"use_newzbin" : checked(headphones.NEWZBIN),
					"newzbin_uid" : headphones.NEWZBIN_UID,
					"newzbin_pass" : headphones.NEWZBIN_PASSWORD,
					"pref_qual_0" : radio(headphones.PREFERRED_QUALITY, 0),
					"pref_qual_1" : radio(headphones.PREFERRED_QUALITY, 1),
					"pref_qual_3" : radio(headphones.PREFERRED_QUALITY, 3),
					"pref_qual_2" : radio(headphones.PREFERRED_QUALITY, 2),
					"pref_bitrate" : headphones.PREFERRED_BITRATE,
					"detect_bitrate" : checked(headphones.DETECT_BITRATE),
					"move_files" : checked(headphones.MOVE_FILES),
					"rename_files" : checked(headphones.RENAME_FILES),
					"correct_metadata" : checked(headphones.CORRECT_METADATA),
					"cleanup_files" : checked(headphones.CLEANUP_FILES),
					"add_album_art" : checked(headphones.ADD_ALBUM_ART),
					"embed_album_art" : checked(headphones.EMBED_ALBUM_ART),
					"embed_lyrics" : checked(headphones.EMBED_LYRICS),
					"dest_dir" : headphones.DESTINATION_DIR,
					"folder_format" : headphones.FOLDER_FORMAT,
					"file_format" : headphones.FILE_FORMAT,
					"include_extras" : checked(headphones.INCLUDE_EXTRAS),
					"log_dir" : headphones.LOG_DIR,
					"interface_list" : interface_list,
					"encode":		checked(headphones.ENCODE),
					"encoder":		headphones.ENCODER,
					"bitrate":		int(headphones.BITRATE),
					"encoderfolder":	headphones.ENCODERFOLDER,
					"advancedencoder":	headphones.ADVANCEDENCODER,
					"encoderoutputformat": headphones.ENCODEROUTPUTFORMAT,
					"samplingfrequency": headphones.SAMPLINGFREQUENCY,
					"encodervbrcbr": headphones.ENCODERVBRCBR,
					"encoderquality": headphones.ENCODERQUALITY,
					"encoderlossless": checked(headphones.ENCODERLOSSLESS)
				}
		return serve_template(templatename="config.html", title="Settings", config=config)	
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None, blackhole=0, blackhole_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, newzbin=0, newzbin_uid=None, newzbin_password=None, preferred_quality=0, preferred_bitrate=None, detect_bitrate=0, move_files=0, 
		rename_files=0, correct_metadata=0, cleanup_files=0, add_album_art=0, embed_album_art=0, embed_lyrics=0, destination_dir=None, folder_format=None, file_format=None, include_extras=0, interface=None, log_dir=None,
		encode=0, encoder=None, bitrate=None, samplingfrequency=None, encoderfolder=None, advancedencoder=None, encoderoutputformat=None, encodervbrcbr=None, encoderquality=None, encoderlossless=0):

		headphones.HTTP_HOST = http_host
		headphones.HTTP_PORT = http_port
		headphones.HTTP_USERNAME = http_username
		headphones.HTTP_PASSWORD = http_password
		headphones.LAUNCH_BROWSER = launch_browser
		headphones.SAB_HOST = sab_host
		headphones.SAB_USERNAME = sab_username
		headphones.SAB_PASSWORD = sab_password		
		headphones.SAB_APIKEY = sab_apikey
		headphones.SAB_CATEGORY = sab_category
		headphones.DOWNLOAD_DIR = download_dir
		headphones.BLACKHOLE = blackhole
		headphones.BLACKHOLE_DIR = blackhole_dir
		headphones.USENET_RETENTION = usenet_retention
		headphones.NZBMATRIX = nzbmatrix
		headphones.NZBMATRIX_USERNAME = nzbmatrix_username
		headphones.NZBMATRIX_APIKEY = nzbmatrix_apikey
		headphones.NEWZNAB = newznab
		headphones.NEWZNAB_HOST = newznab_host
		headphones.NEWZNAB_APIKEY = newznab_apikey
		headphones.NZBSORG = nzbsorg
		headphones.NZBSORG_UID = nzbsorg_uid
		headphones.NZBSORG_HASH = nzbsorg_hash
		headphones.NEWZBIN = newzbin
		headphones.NEWZBIN_UID = newzbin_uid
		headphones.NEWZBIN_PASSWORD = newzbin_password
		headphones.PREFERRED_QUALITY = int(preferred_quality)
		headphones.PREFERRED_BITRATE = preferred_bitrate
		headphones.DETECT_BITRATE = detect_bitrate
		headphones.MOVE_FILES = move_files
		headphones.CORRECT_METADATA = correct_metadata
		headphones.RENAME_FILES = rename_files
		headphones.CLEANUP_FILES = cleanup_files
		headphones.ADD_ALBUM_ART = add_album_art
		headphones.EMBED_ALBUM_ART = embed_album_art
		headphones.EMBED_LYRICS = embed_lyrics
		headphones.DESTINATION_DIR = destination_dir
		headphones.FOLDER_FORMAT = folder_format
		headphones.FILE_FORMAT = file_format
		headphones.INCLUDE_EXTRAS = include_extras
		headphones.INTERFACE = interface
		headphones.LOG_DIR = log_dir
		headphones.ENCODE = encode
		headphones.ENCODER = encoder
		headphones.BITRATE = int(bitrate)
		headphones.SAMPLINGFREQUENCY = int(samplingfrequency)
		headphones.ENCODERFOLDER = encoderfolder
		headphones.ADVANCEDENCODER = advancedencoder
		headphones.ENCODEROUTPUTFORMAT = encoderoutputformat
		headphones.ENCODERVBRCBR = encodervbrcbr
		headphones.ENCODERQUALITY = int(encoderquality)
		headphones.ENCODERLOSSLESS = encoderlossless
		
		headphones.config_write()

		raise cherrypy.HTTPRedirect("config")
		
	configUpdate.exposed = True

	def shutdown(self):
		headphones.SIGNAL = 'shutdown'
		message = 'Shutting Down...'
		return serve_template(templatename="shutdown.html", title="Shutting Down", message=message, timer=15)
		return page

	shutdown.exposed = True

	def restart(self):
		headphones.SIGNAL = 'restart'
		message = 'Restarting...'
		return serve_template(templatename="shutdown.html", title="Restarting", message=message, timer=30)
	restart.exposed = True
	
	def update(self):
		headphones.SIGNAL = 'update'
		message = 'Updating...'
		return serve_template(templatename="shutdown.html", title="Updating", message=message, timer=120)
		return page
	update.exposed = True
		
	def extras(self):
		myDB = db.DBConnection()
		cloudlist = myDB.select('SELECT * from lastfmcloud')
		return serve_template(templatename="extras.html", title="Extras", cloudlist=cloudlist)
		return page
	extras.exposed = True

	def addReleaseById(self, rid):
		threading.Thread(target=importer.addReleaseById, args=[rid]).start()
		time.sleep(5)
		raise cherrypy.HTTPRedirect("home")
	addReleaseById.exposed = True
	
	def updateCloud(self):
		
		lastfm.getSimilar()
		raise cherrypy.HTTPRedirect("extras")
		
	updateCloud.exposed = True