from __future__ import with_statement

import os, sys, subprocess

import threading
import webbrowser
import sqlite3

from lib.apscheduler.scheduler import Scheduler
from lib.configobj import ConfigObj

import cherrypy

from headphones import versioncheck, logger, version
from headphones.common import *

FULL_PATH = None
PROG_DIR = None

ARGS = None
SIGNAL = None

SYS_ENCODING = None

VERBOSE = 1
DAEMON = False
PIDFILE= None

SCHED = Scheduler()

INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
started = False

DATA_DIR = None

CONFIG_FILE = None
CFG = None

DB_FILE = None

LOG_DIR = None
LOG_LIST = []

CACHE_DIR = None

HTTP_PORT = None
HTTP_HOST = None
HTTP_USERNAME = None
HTTP_PASSWORD = None
HTTP_ROOT = None
LAUNCH_BROWSER = False

GIT_PATH = None
INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

MUSIC_DIR = None
DESTINATION_DIR = None
FOLDER_FORMAT = None
FILE_FORMAT = None
PATH_TO_XML = None
PREFERRED_QUALITY = None
PREFERRED_BITRATE = None
DETECT_BITRATE = False
ADD_ARTISTS = False
NEW_ARTISTS = []
CORRECT_METADATA = False
MOVE_FILES = False
RENAME_FILES = False
CLEANUP_FILES = False
ADD_ALBUM_ART = False
EMBED_ALBUM_ART = False
EMBED_LYRICS = False
DOWNLOAD_DIR = None
BLACKHOLE = None
BLACKHOLE_DIR = None
USENET_RETENTION = None
INCLUDE_EXTRAS = False

SEARCH_INTERVAL = 360
LIBRARYSCAN_INTERVAL = 300
DOWNLOAD_SCAN_INTERVAL = 5

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

NEWZBIN = False
NEWZBIN_UID = None
NEWZBIN_PASSWORD = None

LASTFM_USERNAME = None

LOSSY_MEDIA_FORMATS = ["mp3", "aac", "ogg", "ape", "m4a"]
LOSSLESS_MEDIA_FORMATS = ["flac"]
MEDIA_FORMATS = LOSSY_MEDIA_FORMATS + LOSSLESS_MEDIA_FORMATS

TORRENTBLACKHOLE_DIR = None
NUMBEROFSEEDERS = 10
ISOHUNT = None
KAT = None
MININOVA = None
DOWNLOAD_TORRENT_DIR = None

INTERFACE = None
FOLDER_PERMISSIONS = None

ENCODE = False
ENCODERFOLDER = None
ENCODER = None
BITRATE = None
SAMPLINGFREQUENCY = None
ADVANCEDENCODER = None
ENCODEROUTPUTFORMAT = None
ENCODERQUALITY = None
ENCODERVBRCBR = None
ENCODERLOSSLESS = False
PROWL_ENABLED = True
PROWL_PRIORITY = 1
PROWL_KEYS = None
PROWL_ONSNATCH = True
MIRRORLIST = ["musicbrainz.org","tbueter.com","localhost"]
MIRROR = None

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
    
        global __INITIALIZED__, FULL_PATH, PROG_DIR, VERBOSE, DAEMON, DATA_DIR, CONFIG_FILE, CFG, LOG_DIR, CACHE_DIR, \
                HTTP_PORT, HTTP_HOST, HTTP_USERNAME, HTTP_PASSWORD, HTTP_ROOT, LAUNCH_BROWSER, GIT_PATH, \
                CURRENT_VERSION, LATEST_VERSION, MUSIC_DIR, DESTINATION_DIR, PREFERRED_QUALITY, PREFERRED_BITRATE, DETECT_BITRATE, \
                ADD_ARTISTS, CORRECT_METADATA, MOVE_FILES, RENAME_FILES, FOLDER_FORMAT, FILE_FORMAT, CLEANUP_FILES, INCLUDE_EXTRAS, \
                ADD_ALBUM_ART, EMBED_ALBUM_ART, EMBED_LYRICS, DOWNLOAD_DIR, BLACKHOLE, BLACKHOLE_DIR, USENET_RETENTION, SEARCH_INTERVAL, \
                TORRENTBLACKHOLE_DIR, NUMBEROFSEEDERS, ISOHUNT, KAT, MININOVA, DOWNLOAD_TORRENT_DIR, \
                LIBRARYSCAN_INTERVAL, DOWNLOAD_SCAN_INTERVAL, SAB_HOST, SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, \
                NZBMATRIX, NZBMATRIX_USERNAME, NZBMATRIX_APIKEY, NEWZNAB, NEWZNAB_HOST, NEWZNAB_APIKEY, \
                NZBSORG, NZBSORG_UID, NZBSORG_HASH, NEWZBIN, NEWZBIN_UID, NEWZBIN_PASSWORD, LASTFM_USERNAME, INTERFACE, FOLDER_PERMISSIONS, \
                ENCODERFOLDER, ENCODER, BITRATE, SAMPLINGFREQUENCY, ENCODE, ADVANCEDENCODER, ENCODEROUTPUTFORMAT, ENCODERQUALITY, ENCODERVBRCBR, \
                ENCODERLOSSLESS, PROWL_ENABLED, PROWL_PRIORITY, PROWL_KEYS, PROWL_ONSNATCH, MIRRORLIST, MIRROR
                
        if __INITIALIZED__:
            return False
                
        # Make sure all the config sections exist
        CheckSection('General')
        CheckSection('SABnzbd')
        CheckSection('NZBMatrix')
        CheckSection('Newznab')
        CheckSection('NZBsorg')
        CheckSection('Newzbin')
        CheckSection('Prowl')
        
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
        LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', '')
        
        MUSIC_DIR = check_setting_str(CFG, 'General', 'music_dir', '')
        DESTINATION_DIR = check_setting_str(CFG, 'General', 'destination_dir', '')
        PREFERRED_QUALITY = check_setting_int(CFG, 'General', 'preferred_quality', 0)
        PREFERRED_BITRATE = check_setting_int(CFG, 'General', 'preferred_bitrate', '')
        DETECT_BITRATE = bool(check_setting_int(CFG, 'General', 'detect_bitrate', 0))
        ADD_ARTISTS = bool(check_setting_int(CFG, 'General', 'auto_add_artists', 1))
        CORRECT_METADATA = bool(check_setting_int(CFG, 'General', 'correct_metadata', 0))
        MOVE_FILES = bool(check_setting_int(CFG, 'General', 'move_files', 0))
        RENAME_FILES = bool(check_setting_int(CFG, 'General', 'rename_files', 0))
        FOLDER_FORMAT = check_setting_str(CFG, 'General', 'folder_format', 'artist/album [year]')
        FILE_FORMAT = check_setting_str(CFG, 'General', 'file_format', 'tracknumber artist - album [year]- title')
        CLEANUP_FILES = bool(check_setting_int(CFG, 'General', 'cleanup_files', 0))
        ADD_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'add_album_art', 0))
        EMBED_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'embed_album_art', 0))
        EMBED_LYRICS = bool(check_setting_int(CFG, 'General', 'embed_lyrics', 0))
        DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'download_dir', '')
        BLACKHOLE = bool(check_setting_int(CFG, 'General', 'blackhole', 0))
        BLACKHOLE_DIR = check_setting_str(CFG, 'General', 'blackhole_dir', '')
        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', '')
        INCLUDE_EXTRAS = bool(check_setting_int(CFG, 'General', 'include_extras', 0))
        
        SEARCH_INTERVAL = check_setting_int(CFG, 'General', 'search_interval', 360)
        LIBRARYSCAN_INTERVAL = check_setting_int(CFG, 'General', 'libraryscan_interval', 300)
        DOWNLOAD_SCAN_INTERVAL = check_setting_int(CFG, 'General', 'download_scan_interval', 5)
        
        TORRENTBLACKHOLE_DIR = check_setting_str(CFG, 'General', 'torrentblackhole_dir', '')
        NUMBEROFSEEDERS = check_setting_str(CFG, 'General', 'numberofseeders', '10')
        ISOHUNT = bool(check_setting_int(CFG, 'General', 'isohunt', 0))
        KAT = bool(check_setting_int(CFG, 'General', 'kat', 0))
        MININOVA = bool(check_setting_int(CFG, 'General', 'mininova', 0))
        DOWNLOAD_TORRENT_DIR = check_setting_str(CFG, 'General', 'download_torrent_dir', '')
        
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

        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_UID = check_setting_str(CFG, 'Newzbin', 'newzbin_uid', '')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '')

        LASTFM_USERNAME = check_setting_str(CFG, 'General', 'lastfm_username', '')
        
        INTERFACE = check_setting_str(CFG, 'General', 'interface', 'default')
        FOLDER_PERMISSIONS = check_setting_str(CFG, 'General', 'folder_permissions', '0755')
		
        ENCODERFOLDER = check_setting_str(CFG, 'General', 'encoderfolder', '')        
        ENCODER = check_setting_str(CFG, 'General', 'encoder', 'ffmpeg')
        BITRATE = check_setting_int(CFG, 'General', 'bitrate', 192)
        SAMPLINGFREQUENCY= check_setting_int(CFG, 'General', 'samplingfrequency', 44100)
        ENCODE = bool(check_setting_int(CFG, 'General', 'encode', 0))
        ADVANCEDENCODER = check_setting_str(CFG, 'General', 'advancedencoder', '')
        ENCODEROUTPUTFORMAT = check_setting_str(CFG, 'General', 'encoderoutputformat', 'mp3')
        ENCODERQUALITY = check_setting_int(CFG, 'General', 'encoderquality', 2)
        ENCODERVBRCBR = check_setting_str(CFG, 'General', 'encodervbrcbr', 'cbr')
        ENCODERLOSSLESS = bool(check_setting_int(CFG, 'General', 'encoderlossless', 1))

        PROWL_ENABLED = bool(check_setting_int(CFG, 'Prowl', 'prowl_enabled', 0))
        PROWL_KEYS = check_setting_str(CFG, 'Prowl', 'prowl_keys', '')
        PROWL_ONSNATCH = bool(check_setting_int(CFG, 'Prowl', 'prowl_onsnatch', 0)) 
        PROWL_PRIORITY = check_setting_int(CFG, 'Prowl', 'prowl_priority', 0)
        
        MIRROR = check_setting_str(CFG, 'General', 'mirror', 'tbueter.com')
        
        if not LOG_DIR:
            LOG_DIR = os.path.join(DATA_DIR, 'logs')
        
        if not os.path.exists(LOG_DIR):
            try:
                os.makedirs(LOG_DIR)
            except OSError:
                if VERBOSE:
                    print 'Unable to create the log directory. Logging to screen only.'
        
        # Start the logger, silence console logging if we need to
        logger.headphones_log.initLogger(verbose=VERBOSE)
        
        # Update some old config code:
        if FOLDER_FORMAT == '%artist/%album/%track':
            FOLDER_FORMAT = 'artist/album [year]'
        if FILE_FORMAT == '%tracknumber %artist - %album - %title':
            FILE_FORMAT = 'tracknumber artist - album - title'
        
        # Put the cache dir in the data dir for now
        CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CACHE_DIR):
            try:
                os.makedirs(CACHE_DIR)
            except OSError:
                logger.error('Could not create cache dir. Check permissions of datadir: ' + DATA_DIR)
        
        # Initialize the database
        logger.info('Checking to see if the database has all tables....')
        try:
            dbcheck()
        except Exception, e:
            logger.error("Can't connect to the database: %s" % e)
            
        # Get the currently installed version - returns None, 'win32' or the git hash
        # Also sets INSTALL_TYPE variable to 'win', 'git' or 'source'
        CURRENT_VERSION = versioncheck.getVersion()
        
        # Check for new versions
        try:
            LATEST_VERSION = versioncheck.checkGithub()
        except:
            LATEST_VERSION = CURRENT_VERSION

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

    pid = os.getpid()
    logger.info('Daemonized to PID: %s' % pid)
    if PIDFILE:
        logger.info('Writing PID %s to %s' % (pid, PIDFILE))
        file(PIDFILE, 'w').write("%s\n" % pid)

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
    new_config['General']['log_dir'] = LOG_DIR
    new_config['General']['git_path'] = GIT_PATH

    new_config['General']['music_dir'] = MUSIC_DIR
    new_config['General']['destination_dir'] = DESTINATION_DIR
    new_config['General']['preferred_quality'] = PREFERRED_QUALITY
    new_config['General']['preferred_bitrate'] = PREFERRED_BITRATE
    new_config['General']['detect_bitrate'] = int(DETECT_BITRATE)
    new_config['General']['auto_add_artists'] = int(ADD_ARTISTS)
    new_config['General']['correct_metadata'] = int(CORRECT_METADATA)
    new_config['General']['move_files'] = int(MOVE_FILES)
    new_config['General']['rename_files'] = int(RENAME_FILES)
    new_config['General']['folder_format'] = FOLDER_FORMAT
    new_config['General']['file_format'] = FILE_FORMAT
    new_config['General']['cleanup_files'] = int(CLEANUP_FILES)
    new_config['General']['add_album_art'] = int(ADD_ALBUM_ART)
    new_config['General']['embed_album_art'] = int(EMBED_ALBUM_ART)
    new_config['General']['embed_lyrics'] = int(EMBED_LYRICS)
    new_config['General']['download_dir'] = DOWNLOAD_DIR
    new_config['General']['blackhole'] = int(BLACKHOLE)
    new_config['General']['blackhole_dir'] = BLACKHOLE_DIR
    new_config['General']['usenet_retention'] = USENET_RETENTION
    new_config['General']['include_extras'] = int(INCLUDE_EXTRAS)
    
    new_config['General']['numberofseeders'] = NUMBEROFSEEDERS
    new_config['General']['torrentblackhole_dir'] = TORRENTBLACKHOLE_DIR
    new_config['General']['isohunt'] = int(ISOHUNT)
    new_config['General']['kat'] = int(KAT)
    new_config['General']['mininova'] = int(MININOVA)
    new_config['General']['download_torrent_dir'] = DOWNLOAD_TORRENT_DIR
    
    new_config['General']['search_interval'] = SEARCH_INTERVAL
    new_config['General']['libraryscan_interval'] = LIBRARYSCAN_INTERVAL
    new_config['General']['download_scan_interval'] = DOWNLOAD_SCAN_INTERVAL

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
    
    new_config['Newzbin'] = {}
    new_config['Newzbin']['newzbin'] = int(NEWZBIN)
    new_config['Newzbin']['newzbin_uid'] = NEWZBIN_UID
    new_config['Newzbin']['newzbin_password'] = NEWZBIN_PASSWORD
    
    new_config['Prowl'] = {}
    new_config['Prowl']['prowl_enabled'] = int(PROWL_ENABLED)
    new_config['Prowl']['prowl_keys'] = PROWL_KEYS
    new_config['Prowl']['prowl_onsnatch'] = int(PROWL_ONSNATCH)
    new_config['Prowl']['prowl_priority'] = int(PROWL_PRIORITY)
    
    new_config['General']['lastfm_username'] = LASTFM_USERNAME
    new_config['General']['interface'] = INTERFACE
    new_config['General']['folder_permissions'] = FOLDER_PERMISSIONS

    new_config['General']['encode'] = int(ENCODE)
    new_config['General']['encoder'] = ENCODER
    new_config['General']['bitrate'] = int(BITRATE)
    new_config['General']['samplingfrequency'] = int(SAMPLINGFREQUENCY)
    new_config['General']['encoderfolder'] = ENCODERFOLDER
    new_config['General']['advancedencoder'] = ADVANCEDENCODER
    new_config['General']['encoderoutputformat'] = ENCODEROUTPUTFORMAT
    new_config['General']['encoderquality'] = ENCODERQUALITY
    new_config['General']['encodervbrcbr'] = ENCODERVBRCBR
    new_config['General']['encoderlossless'] = ENCODERLOSSLESS
    
    new_config['General']['mirror'] = MIRROR
    
    new_config.write()

    
def start():
    
    global __INITIALIZED__, started
    
    if __INITIALIZED__:
    
        # Start our scheduled background tasks
        from headphones import updater, searcher, librarysync, postprocessor

        SCHED.add_interval_job(updater.dbUpdate, hours=48)
        SCHED.add_interval_job(searcher.searchforalbum, minutes=SEARCH_INTERVAL)
        SCHED.add_interval_job(librarysync.libraryScan, minutes=LIBRARYSCAN_INTERVAL)
        SCHED.add_interval_job(versioncheck.checkGithub, minutes=300)
        SCHED.add_interval_job(postprocessor.checkFolder, minutes=DOWNLOAD_SCAN_INTERVAL)

        SCHED.start()
        
        started = True
    
def dbcheck():

    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT, IncludeExtras INTEGER, LatestAlbum TEXT, ReleaseDate TEXT, AlbumID TEXT, HaveTracks INTEGER, TotalTracks INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT, Type TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT, TrackNumber INTEGER, Location TEXT, BitRate INTEGER, CleanName TEXT, Format TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS snatched (AlbumID TEXT, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT, FolderName TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS have (ArtistName TEXT, AlbumTitle TEXT, TrackNumber TEXT, TrackTitle TEXT, TrackLength TEXT, BitRate TEXT, Genre TEXT, Date TEXT, TrackID TEXT, Location TEXT, CleanName TEXT, Format TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS lastfmcloud (ArtistName TEXT, ArtistID TEXT, Count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS descriptions (ReleaseGroupID TEXT, ReleaseID TEXT, Summary TEXT, Content TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS releases (ReleaseID TEXT, ReleaseGroupID TEXT, UNIQUE(ReleaseID, ReleaseGroupID))')
    c.execute('CREATE INDEX IF NOT EXISTS tracks_albumid ON tracks(AlbumID ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS album_artistid_reldate ON albums(ArtistID ASC, ReleaseDate DESC)')
    
    try:
        c.execute('SELECT IncludeExtras from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN IncludeExtras INTEGER DEFAULT 0')
        
    try:
        c.execute('SELECT LatestAlbum from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN LatestAlbum TEXT')
        
    try:
        c.execute('SELECT ReleaseDate from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN ReleaseDate TEXT')
        
    try:
        c.execute('SELECT AlbumID from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN AlbumID TEXT')
        
    try:
        c.execute('SELECT HaveTracks from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN HaveTracks INTEGER DEFAULT 0')
        
    try:
        c.execute('SELECT TotalTracks from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN TotalTracks INTEGER DEFAULT 0')
        
    try:
        c.execute('SELECT Type from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN Type TEXT DEFAULT "Album"')

    try:
        c.execute('SELECT TrackNumber from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN TrackNumber INTEGER')
        
    try:
        c.execute('SELECT FolderName from snatched')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE snatched ADD COLUMN FolderName TEXT')
    
    try:
        c.execute('SELECT Location from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN Location TEXT')
        
    try:
        c.execute('SELECT Location from have')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE have ADD COLUMN Location TEXT')
    
    try:
        c.execute('SELECT BitRate from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN BitRate INTEGER')  
        
    try:
        c.execute('SELECT CleanName from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN CleanName TEXT')  
        
    try:
        c.execute('SELECT CleanName from have')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE have ADD COLUMN CleanName TEXT')  
    
    # Add the Format column
    try:
        c.execute('SELECT Format from have')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE have ADD COLUMN Format TEXT DEFAULT NULL')  
    
    try:
        c.execute('SELECT Format from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN Format TEXT DEFAULT NULL')  

    # Update the Format of files in library, this won't do anything if all files have a known format
    threading.Thread(target=importer.updateFormat).start()
    
    conn.commit()
    c.close()

    
def shutdown(restart=False, update=False):

    cherrypy.engine.exit()
    SCHED.shutdown(wait=False)
    
    config_write()
    
    if not restart and not update:
    	logger.info('Headphones is shutting down...')
    if update:
    	logger.info('Headphones is updating...')
        try:
            versioncheck.update()
        except Exception, e:
            logger.warn('Headphones failed to update: %s. Restarting.' % e) 

    if PIDFILE :
        logger.info ('Removing pidfile %s' % PIDFILE)
        os.remove(PIDFILE)
        
    if restart:
    	logger.info('Headphones is restarting...')
        popen_list = [sys.executable, FULL_PATH]
        popen_list += ARGS
        if '--nolaunch' not in popen_list:
            popen_list += ['--nolaunch']
        logger.info('Restarting Headphones with ' + str(popen_list))
        subprocess.Popen(popen_list, cwd=os.getcwd())
        
    os._exit(0)
