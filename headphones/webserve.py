import os

import cherrypy
from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import time
import threading

import headphones

from headphones.mb import getReleaseGroup
from headphones import templates, logger, searcher, db, importer, helpers, mb, lastfm
from headphones.helpers import checked, radio

_hplookup = TemplateLookup(directories=[os.path.join(str(headphones.PROG_DIR), 'data/interfaces/default/')], output_encoding='utf-8')

def serve_template(templatename, **kwargs):
	try:
		template = _hplookup.get_template(templatename)
		kwargs['hpRoot'] = headphones.HTTP_ROOT
		return template.render(**kwargs)
	except:
		return exceptions.html_error_template().render()
	
class WebInterface(object):
	
	def index(self):
		raise cherrypy.HTTPRedirect("home")
	index.exposed=True

	def home(self):
		myDB = db.DBConnection()
		results = myDB.select('SELECT ArtistName, ArtistID, Status, LatestAlbum, ReleaseDate, AlbumID, TotalTracks, HaveTracks from artists order by ArtistSortName COLLATE NOCASE')
		return serve_template(templatename="index.html", title='Home', artists=results)
	home.exposed = True
	

	def artistPage(self, ArtistID):
		myDB = db.DBConnection()
		
		artist = myDB.action('SELECT ArtistName, IncludeExtras FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
		albums = myDB.select('SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])

		return serve_template(templatename="artist.html", title=artist['ArtistName'], artist=artist, albums=albums, artistID=ArtistID)
	artistPage.exposed = True
	
	
	def albumPage(self, AlbumID):

		myDB = db.DBConnection()
		
		album = myDB.action('SELECT * FROM albums WHERE AlbumID=?', [AlbumID]).fetchone()
		tracks = myDB.select('SELECT ArtistID, ArtistName, AlbumTitle, TrackTitle, TrackDuration, TrackID, AlbumASIN FROM tracks WHERE AlbumID=?', [AlbumID])
		
		return serve_template(templatename="album.html", title=album['AlbumTitle'],tracks=tracks, album=album)

	albumPage.exposed = True
	
	
	def findArtist(self, name):

		if len(name) == 0 or name == 'Add an artist':
			raise cherrypy.HTTPRedirect("home")
		else:
			artistResults = mb.findArtist(name, limit=10)
			if len(artistResults) == 1:
				logger.info(u"Found one artist matching your search term: " + artistResults[0]['name'] +" ("+ artistResults[0]['id']+")")			
				raise cherrypy.HTTPRedirect("addArtist?artistid=%s" % artistResults[0]['id'])
		return serve_template(templatename="artistsearch.html", title="Search", results=artistResults)
	findArtist.exposed = True

	def artistInfo(self, artistid):
		artist = mb.getArtist(artistid)
		if artist['artist_begindate']:
			begindate = artist['artist_begindate']
		else:
			begindate = ''
		if artist['artist_enddate']:
			enddate = artist['artist_enddate']
		else:
			enddate = ''
		return serve_template(templatename="artistinfo.html", artist=artist, begindate=begindate, enddate=enddate)
	artistInfo.exposed = True

	def addArtist(self, artistid, redirect='home'):
		
		threading.Thread(target=importer.addArtisttoDB, args=[artistid]).start()
		time.sleep(5)
		threading.Thread(target=lastfm.getSimilar).start()
		raise cherrypy.HTTPRedirect(redirect)
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
	
	def pauseArtist(self, ArtistID):
	
		logger.info(u"Pausing artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Paused'}
		myDB.upsert("artists", newValueDict, controlValueDict)
		
		raise cherrypy.HTTPRedirect("home")
	pauseArtist.exposed = True
	
	def resumeArtist(self, ArtistID):

		logger.info(u"Resuming artist: " + ArtistID)
		myDB = db.DBConnection()
		controlValueDict = {'ArtistID': ArtistID}
		newValueDict = {'Status': 'Active'}
		myDB.upsert("artists", newValueDict, controlValueDict)

		raise cherrypy.HTTPRedirect("home")
	resumeArtist.exposed = True
	
	def deleteArtist(self, ArtistID):

		logger.info(u"Deleting all traces of artist: " + ArtistID)
		myDB = db.DBConnection()
		myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
		myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

		raise cherrypy.HTTPRedirect("home")
	deleteArtist.exposed = True
	
	def queueAlbum(self, AlbumID, ArtistID, new=False):

		logger.info(u"Marking album: " + AlbumID + "as wanted...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Wanted'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		import searcher
		searcher.searchNZB(AlbumID, new)
		
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	queueAlbum.exposed = True

	def unqueueAlbum(self, AlbumID, ArtistID):

		logger.info(u"Marking album: " + AlbumID + "as skipped...")
		myDB = db.DBConnection()
		controlValueDict = {'AlbumID': AlbumID}
		newValueDict = {'Status': 'Skipped'}
		myDB.upsert("albums", newValueDict, controlValueDict)
		
		raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
	unqueueAlbum.exposed = True
	
	def upcoming(self):
		myDB = db.DBConnection()

		upcoming = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE ReleaseDate > date('now') order by ReleaseDate DESC")
		wanted = myDB.select("SELECT AlbumTitle, ReleaseDate, DateAdded, AlbumASIN, AlbumID, ArtistName, ArtistID from albums WHERE Status='Wanted'")
		
		return serve_template(templatename="upcoming.html", title="Upcoming Albums", upcoming=upcoming, wanted=wanted)
	upcoming.exposed = True
	
	def manage(self):
		return serve_template(templatename="manage.html", title="Manage")
	manage.exposed = True
	
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
	
	def musicScan(self, path):
		headphones.MUSIC_DIR = path
		headphones.config_write()
		try:	
			threading.Thread(target=importer.scanMusic, args=[path]).start()
		except Exception, e:
			logger.error('Unable to complete the scan: %s' % e)
		time.sleep(10)
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
		snatched = myDB.select('''SELECT AlbumID, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT from snatched order by DateAdded DESC''')
		return serve_template(templatename="history.html", title="History", snatched=snatched)
	history.exposed = True
	
	def logs(self):
		if os.path.isfile(os.path.join(headphones.LOG_DIR, 'headphones.log')):
			fileHandle = open(os.path.join(headphones.LOG_DIR, 'headphones.log'))
			lineList = fileHandle.readlines()
			fileHandle.close()
			lineList.reverse()
			
		return serve_template(templatename="logs.html",title="Logs", log=lineList)
	logs.exposed = True
	
	def clearhistory(self):

		logger.info(u"Clearing history")
		myDB = db.DBConnection()
		myDB.action('''DELETE from snatched''')

		raise cherrypy.HTTPRedirect("history")
	clearhistory.exposed = True
	
	def config(self):
		# FIXME: this is all temporary until the way the config is handled is rewritten. 
		# should be able to just add
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
					"pref_qual_0" : radio(headphones.PREFERRED_QUALITY, 0),
					"pref_qual_1" : radio(headphones.PREFERRED_QUALITY, 1),
					"pref_qual_2" : radio(headphones.PREFERRED_QUALITY, 3),
					"pref_qual_3" : radio(headphones.PREFERRED_QUALITY, 2),
					"pref_bitrate" : headphones.PREFERRED_BITRATE,
					"detect_bitrate" : checked(headphones.DETECT_BITRATE),
					"move_files" : checked(headphones.MOVE_FILES),
					"rename_files" : checked(headphones.RENAME_FILES),
					"correct_metadata" : checked(headphones.CORRECT_METADATA),
					"cleanup_files" : checked(headphones.CLEANUP_FILES),
					"add_album_art" : checked(headphones.ADD_ALBUM_ART),
					"embed_album_art" : checked(headphones.EMBED_ALBUM_ART),
					"dest_dir" : headphones.DESTINATION_DIR,
					"folder_format" : headphones.FOLDER_FORMAT,
					"file_format" : headphones.FILE_FORMAT,
					"include_extras" : checked(headphones.INCLUDE_EXTRAS),
					"log_dir" : headphones.LOG_DIR
				}

		return serve_template(templatename="config.html", title="Config", config=config)
	config.exposed = True
	
	
	def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0,
		sab_host=None, sab_username=None, sab_apikey=None, sab_password=None, sab_category=None, download_dir=None, blackhole=0, blackhole_dir=None,
		usenet_retention=None, nzbmatrix=0, nzbmatrix_username=None, nzbmatrix_apikey=None, newznab=0, newznab_host=None, newznab_apikey=None,
		nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, preferred_quality=0, preferred_bitrate=None, detect_bitrate=0, move_files=0, 
		rename_files=0, correct_metadata=0, cleanup_files=0, add_album_art=0, embed_album_art=0, destination_dir=None, folder_format=None, file_format=None, include_extras=0, log_dir=None):
		
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
		headphones.PREFERRED_QUALITY = int(preferred_quality)
		headphones.PREFERRED_BITRATE = preferred_bitrate
		headphones.DETECT_BITRATE = detect_bitrate
		headphones.MOVE_FILES = move_files
		headphones.CORRECT_METADATA = correct_metadata
		headphones.RENAME_FILES = rename_files
		headphones.CLEANUP_FILES = cleanup_files
		headphones.ADD_ALBUM_ART = add_album_art
		headphones.EMBED_ALBUM_ART = embed_album_art
		headphones.DESTINATION_DIR = destination_dir
		headphones.FOLDER_FORMAT = folder_format
		headphones.FILE_FORMAT = file_format
		headphones.INCLUDE_EXTRAS = include_extras
		headphones.LOG_DIR = log_dir
		
		headphones.config_write()

		raise cherrypy.HTTPRedirect("config")
	configUpdate.exposed = True

	def shutdown(self):
		logger.info(u"Headphones is shutting down...")
		threading.Timer(2, headphones.shutdown).start()
		return serve_template(templatename="shutdown.html", title="Shutdown", messageText="Shutting down Headphones...")
	shutdown.exposed = True

	def restart(self):
		logger.info(u"Headphones is restarting...")
		threading.Timer(2, headphones.shutdown, [True]).start()
		return serve_template(templatename="shutdown.html", title="Restart", messageText="Restarting Headphones...")
	restart.exposed = True
	
	def update(self):
		logger.info('Headphones is updating...')
		threading.Timer(2, headphones.shutdown, [True, True]).start()
		return serve_template(templatename="shutdown.html", title="Update", messageText="Updating Headphones...")
	update.exposed = True
		
	def extras(self):
		myDB = db.DBConnection()
		cloudlist = myDB.select('SELECT * from lastfmcloud')
		return serve_template(templatename="extras.html", title="Extras", cloudList=cloudlist)
	extras.exposed = True
	
	def updateCloud(self):
		
		lastfm.getSimilar()
		raise cherrypy.HTTPRedirect("extras")
	updateCloud.exposed = True
