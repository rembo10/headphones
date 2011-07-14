import os, sys, subprocess

import threading
import webbrowser
import sqlite3

from lib.apscheduler.scheduler import Scheduler
from lib.configobj import ConfigObj

import cherrypy

from headphones import updater, searcher, itunesimport, versioncheck, logger

FULL_PATH = None
PROG_DIR = None

ARGS = None
INVOKED_COMMAND = None

QUIET = False
DAEMON = False

SCHED = Scheduler()

INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
started = False

DATA_DIR = None

CONFIG_FILE = None
CFG = None

DB_FILE = None

LOG_DIR = None

HTTP_PORT = None
HTTP_HOST = None
HTTP_USERNAME = None
HTTP_PASSWORD = None
HTTP_ROOT = None
LAUNCH_BROWSER = False

GIT_PATH = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

MUSIC_DIR = None
FOLDER_FORMAT = None
FILE_FORMAT = None
PATH_TO_XML = None
PREFER_LOSSLESS = False
FLAC_TO_MP3 = False
MOVE_FILES = False
RENAME_FILES = False
CLEANUP_FILES = False
ADD_ALBUM_ART = False
DOWNLOAD_DIR = None
USENET_RETENTION = None

NZB_SEARCH_INTERVAL = 360
LIBRARYSCAN_INTERVAL = 60

SAB_HOST = None
SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None

NZBMATRIX = False
NZBMATRIX_USERNAME = None
NZBMATRIX_APIKEY = None

NEWZNAB = False
NEWZNAB_HOST = None
NEWZNAB_APIKEY = None

NZBSORG = False
NZBSORG_UID = None
NZBSORG_HASH = None

def CheckSection(sec):
    """ Check if INI section exists, if not create it """
    try:
        CFG[sec]
        return True
    except:
        CFG[sec] = {}
        return False

################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val):
    try:
        my_val = int(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    logger.debug(item_name + " -> " + str(my_val))
    return my_val

################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, log=True):
    try:
        my_val = config[cfg_name][item_name]
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if log:
        logger.debug(item_name + " -> " + my_val)
    else:
        logger.debug(item_name + " -> ******")
    return my_val
	

def initialize():

	with INIT_LOCK:
	
		global __INITIALIZED__, FULL_PATH, PROG_DIR, QUIET, DAEMON, DATA_DIR, CONFIG_FILE, CFG, LOG_DIR, \
				HTTP_PORT, HTTP_HOST, HTTP_USERNAME, HTTP_PASSWORD, HTTP_ROOT, LAUNCH_BROWSER, GIT_PATH, \
				CURRENT_VERSION, \
				MUSIC_DIR, PREFER_LOSSLESS, FLAC_TO_MP3, MOVE_FILES, RENAME_FILES, FOLDER_FORMAT, \
				FILE_FORMAT, CLEANUP_FILES, ADD_ALBUM_ART, DOWNLOAD_DIR, USENET_RETENTION, \
				NZB_SEARCH_INTERVAL, LIBRARYSCAN_INTERVAL, \
				SAB_HOST, SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, \
				NZBMATRIX, NZBMATRIX_USERNAME, NZBMATRIX_APIKEY, \
				NEWZNAB, NEWZNAB_HOST, NEWZNAB_APIKEY, \
				NZBSORG, NZBSORG_UID, NZBSORG_HASH
				
		if __INITIALIZED__:
			return False
				
		# Make sure all the config sections exist
		CheckSection('General')
		CheckSection('SABnzbd')
		CheckSection('NZBMatrix')
		CheckSection('Newznab')
		CheckSection('NZBsorg')
		
		# Set global variables based on config file or use defaults
		try:
			HTTP_PORT = check_setting_int(CFG, 'General', 'http_port', 8181)
		except:
			HTTP_PORT = 8181
			
		if HTTP_PORT < 21 or HTTP_PORT > 65535:
			HTTP_PORT = 8181
			
		HTTP_HOST = check_setting_str(CFG, 'General', 'http_host', '0.0.0.0')
		HTTP_USERNAME = check_setting_str(CFG, 'General', 'http_username', '')
		HTTP_PASSWORD = check_setting_str(CFG, 'General', 'http_password', '')
		HTTP_ROOT = check_setting_str(CFG, 'General', 'http_root', '/')
		LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))
		GIT_PATH = check_setting_str(CFG, 'General', 'git_path', '')
		
		MUSIC_DIR = check_setting_str(CFG, 'General', 'music_dir', '')
		PREFER_LOSSLESS = bool(check_setting_int(CFG, 'General', 'prefer_lossless', 0))
		FLAC_TO_MP3 = bool(check_setting_int(CFG, 'General', 'flac_to_mp3', 0))
		MOVE_FILES = bool(check_setting_int(CFG, 'General', 'move_files', 0))
		RENAME_FILES = bool(check_setting_int(CFG, 'General', 'rename_files', 0))
		FOLDER_FORMAT = check_setting_str(CFG, 'General', 'folder_format', '%artist/%album/%track')
		FILE_FORMAT = check_setting_str(CFG, 'General', 'file_format', '%tracknumber %artist - %album - %title')
		CLEANUP_FILES = bool(check_setting_int(CFG, 'General', 'cleanup_files', 0))
		ADD_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'add_album_art', 0))
		DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'download_dir', '')
		USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', '')
		
		NZB_SEARCH_INTERVAL = check_setting_int(CFG, 'General', 'nzb_search_interval', 360)
		LIBRARYSCAN_INTERVAL = check_setting_int(CFG, 'General', 'libraryscan_interval', 180)
		
		SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')
		SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
		SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
		SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
		SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', '')
		
		NZBMATRIX = bool(check_setting_int(CFG, 'NZBMatrix', 'nzbmatrix', 0))
		NZBMATRIX_USERNAME = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_username', '')
		NZBMATRIX_APIKEY = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_apikey', '')
		
		NEWZNAB = bool(check_setting_int(CFG, 'Newznab', 'newznab', 0))
		NEWZNAB_HOST = check_setting_str(CFG, 'Newznab', 'newznab_host', '')
		NEWZNAB_APIKEY = check_setting_str(CFG, 'Newznab', 'newznab_apikey', '')
		
		NZBSORG = bool(check_setting_int(CFG, 'NZBsorg', 'nzbsorg', 0))
		NZBSORG_UID = check_setting_str(CFG, 'NZBsorg', 'nzbsorg_uid', '')
		NZBSORG_HASH = check_setting_str(CFG, 'NZBsorg', 'nzbsorg_hash', '')
	
		# Put the log dir in the data dir for now
		LOG_DIR = os.path.join(DATA_DIR, 'logs')
		if not os.path.exists(LOG_DIR):
			try:
				os.makedirs(LOG_DIR)
			except OSError:
				if not QUIET:
					print 'Unable to create the log directory. Logging to screen only.'
		
		# Start the logger, silence console logging if we need to
		logger.headphones_log.initLogger(quiet=QUIET)
		
		# Initialize the database
		logger.info('Checking to see if the database has all tables....')
		try:
			dbcheck()
		except Exception, e:
			logger.error("Can't connect to the database: %s" % e)
			
		# Get the currently installed version
		CURRENT_VERSION = versioncheck.getVersion()

		__INITIALIZED__ = True
		return True
	
def daemonize():

	if threading.activeCount() != 1:
		logger.warn('There are %r active threads. Daemonizing may cause \
						strange behavior.' % threading.enumerate())
	
	sys.stdout.flush()
	sys.stderr.flush()
	
	# Do first fork
	try:
		pid = os.fork()
		if pid == 0:
			pass
		else:
			# Exit the parent process
			logger.debug('Forking once...')
			os._exit(0)
	except OSError, e:
		sys.exit("1st fork failed: %s [%d]" % (e.strerror, e.errno))
		
	os.setsid()

	# Do second fork
	try:
		pid = os.fork()
		if pid > 0:
			logger.debug('Forking twice...')
			os._exit(0) # Exit second parent process
	except OSError, e:
		sys.exit("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

	os.chdir("/")
	os.umask(0)
	
	si = open('/dev/null', "r")
	so = open('/dev/null', "a+")
	se = open('/dev/null', "a+")
	
	os.dup2(si.fileno(), sys.stdin.fileno())
	os.dup2(so.fileno(), sys.stdout.fileno())
	os.dup2(se.fileno(), sys.stderr.fileno())
	
	logger.info('Daemonized to PID: %s' % os.getpid())
	
def launch_browser(host, port, root):

	if host == '0.0.0.0':
		host = 'localhost'
	
	try:	
		webbrowser.open('http://%s:%i%s' % (host, port, root))
	except Exception, e:
		logger.error('Could not launch browser: %s' % e)

def config_write():

	new_config = ConfigObj()
	new_config.filename = CONFIG_FILE

	new_config['General'] = {}
	new_config['General']['http_port'] = HTTP_PORT
	new_config['General']['http_host'] = HTTP_HOST
	new_config['General']['http_username'] = HTTP_USERNAME
	new_config['General']['http_password'] = HTTP_PASSWORD
	new_config['General']['http_root'] = HTTP_ROOT
	new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)
	new_config['General']['git_path'] = GIT_PATH

	new_config['General']['music_dir'] = MUSIC_DIR
	new_config['General']['prefer_lossless'] = int(PREFER_LOSSLESS)
	new_config['General']['flac_to_mp3'] = int(FLAC_TO_MP3)
	new_config['General']['move_files'] = int(MOVE_FILES)
	new_config['General']['rename_files'] = int(RENAME_FILES)
	new_config['General']['folder_format'] = FOLDER_FORMAT
	new_config['General']['file_format'] = FILE_FORMAT
	new_config['General']['cleanup_files'] = int(CLEANUP_FILES)
	new_config['General']['add_album_art'] = int(ADD_ALBUM_ART)
	new_config['General']['download_dir'] = DOWNLOAD_DIR
	new_config['General']['usenet_retention'] = USENET_RETENTION
	
	new_config['General']['nzb_search_interval'] = NZB_SEARCH_INTERVAL
	new_config['General']['libraryscan_interval'] = LIBRARYSCAN_INTERVAL

	new_config['SABnzbd'] = {}
	new_config['SABnzbd']['sab_host'] = SAB_HOST
	new_config['SABnzbd']['sab_username'] = SAB_USERNAME
	new_config['SABnzbd']['sab_password'] = SAB_PASSWORD
	new_config['SABnzbd']['sab_apikey'] = SAB_APIKEY
	new_config['SABnzbd']['sab_category'] = SAB_CATEGORY

	new_config['NZBMatrix'] = {}
	new_config['NZBMatrix']['nzbmatrix'] = int(NZBMATRIX)
	new_config['NZBMatrix']['nzbmatrix_username'] = NZBMATRIX_USERNAME
	new_config['NZBMatrix']['nzbmatrix_apikey'] = NZBMATRIX_APIKEY

	new_config['Newznab'] = {}
	new_config['Newznab']['newznab'] = int(NEWZNAB)
	new_config['Newznab']['newznab_host'] = NEWZNAB_HOST
	new_config['Newznab']['newznab_apikey'] = NEWZNAB_APIKEY

	new_config['NZBsorg'] = {}
	new_config['NZBsorg']['nzbsorg'] = int(NZBSORG)
	new_config['NZBsorg']['nzbsorg_uid'] = NZBSORG_UID
	new_config['NZBsorg']['nzbsorg_hash'] = NZBSORG_HASH
	
	new_config.write()

	
def start():
	
	global __INITIALIZED__, started
	
	if __INITIALIZED__:
	
		# Start our scheduled background tasks

		SCHED.add_cron_job(updater.dbUpdate, hour=4, minute=0, second=0)
		SCHED.add_interval_job(searcher.searchNZB, minutes=NZB_SEARCH_INTERVAL)
		SCHED.add_interval_job(itunesimport.scanMusic, minutes=LIBRARYSCAN_INTERVAL)
		SCHED.add_interval_job(versioncheck.checkGithub, minutes=300)

		SCHED.start()
		
		# Check for new versions
		versioncheck.checkGithub()
		
		
		started = True
	
def dbcheck():

	conn=sqlite3.connect(DB_FILE)
	c=conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS snatched (AlbumID TEXT, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS extras (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS have (ArtistName TEXT, AlbumTitle TEXT, TrackNumber TEXT, TrackTitle TEXT, TrackLength TEXT, BitRate TEXT, Genre TEXT, Date TEXT, TrackID TEXT)')
	conn.commit()
	c.close()

	
def shutdown(restart=False, update=False):
	
	cherrypy.engine.exit()
	SCHED.shutdown(wait=False)
	
	config_write()
	
	if update:
		try:
			versioncheck.update()
		except Exception, e:
			logger.warn('Headphones failed to update: %s. Restarting.' % e) 
			
	if restart:
	
		popen_list = [sys.executable, FULL_PATH]
		popen_list += ARGS
		if '--nolaunch' not in popen_list:
			popen_list += ['--nolaunch']
		logger.info('Restarting Headphones with ' + str(popen_list))
		subprocess.Popen(popen_list, cwd=os.getcwd())
		
	os._exit(0)