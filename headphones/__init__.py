#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

# NZBGet support added by CurlyMo <curlymoo1@gmail.com> as a part of XBian - XBMC on the Raspberry Pi

import os
import sys
import subprocess
import threading
import webbrowser
import sqlite3
import itertools
import cherrypy

from apscheduler.scheduler import Scheduler
from configobj import ConfigObj

from headphones import versioncheck, logger, version
from headphones.common import *

FULL_PATH = None
PROG_DIR = None

ARGS = None
SIGNAL = None

SYS_PLATFORM = None
SYS_ENCODING = None

QUIET = False
VERBOSE = False
DAEMON = False
CREATEPID = False
PIDFILE= None

SCHED = Scheduler()

INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
started = False

DATA_DIR = None

CONFIG_FILE = None
CFG = None
CONFIG_VERSION = None

DB_FILE = None

LOG_DIR = None
LOG_LIST = []

CACHE_DIR = None

HTTP_PORT = None
HTTP_HOST = None
HTTP_USERNAME = None
HTTP_PASSWORD = None
HTTP_ROOT = None
HTTP_PROXY = False
LAUNCH_BROWSER = False

ENABLE_HTTPS = False
HTTPS_CERT = None
HTTPS_KEY = None

API_ENABLED = False
API_KEY = None

GIT_PATH = None
GIT_USER = None
GIT_BRANCH = None
DO_NOT_OVERRIDE_GIT_BRANCH = False
INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

CHECK_GITHUB = False
CHECK_GITHUB_ON_STARTUP = False
CHECK_GITHUB_INTERVAL = None

MUSIC_DIR = None
DESTINATION_DIR = None
LOSSLESS_DESTINATION_DIR = None
FOLDER_FORMAT = None
FILE_FORMAT = None
FILE_UNDERSCORES = False
PATH_TO_XML = None
PREFERRED_QUALITY = None
PREFERRED_BITRATE = None
PREFERRED_BITRATE_HIGH_BUFFER = None
PREFERRED_BITRATE_LOW_BUFFER = None
PREFERRED_BITRATE_ALLOW_LOSSLESS = False
DETECT_BITRATE = False
LOSSLESS_BITRATE_FROM = None
LOSSLESS_BITRATE_TO = None
ADD_ARTISTS = False
CORRECT_METADATA = False
FREEZE_DB = False
MOVE_FILES = False
RENAME_FILES = False
CLEANUP_FILES = False
KEEP_NFO = False
ADD_ALBUM_ART = False
ALBUM_ART_FORMAT = None
EMBED_ALBUM_ART = False
EMBED_LYRICS = False
REPLACE_EXISTING_FOLDERS = False
NZB_DOWNLOADER = None    # 0: sabnzbd, 1: nzbget, 2: blackhole
TORRENT_DOWNLOADER = None # 0: blackhole, 1: transmission, 2: utorrent
DOWNLOAD_DIR = None
BLACKHOLE = None
BLACKHOLE_DIR = None
USENET_RETENTION = None
INCLUDE_EXTRAS = False
EXTRAS = None
AUTOWANT_UPCOMING = False
AUTOWANT_ALL = False
AUTOWANT_MANUALLY_ADDED = True
KEEP_TORRENT_FILES = False
PREFER_TORRENTS = None # 0: nzbs, 1: torrents, 2: no preference
OPEN_MAGNET_LINKS = False

SEARCH_INTERVAL = 360
LIBRARYSCAN = False
LIBRARYSCAN_INTERVAL = 300
DOWNLOAD_SCAN_INTERVAL = 5
UPDATE_DB_INTERVAL = 24
MB_IGNORE_AGE = 365
TORRENT_REMOVAL_INTERVAL = 720

SAB_HOST = None
SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None

NZBGET_USERNAME = None
NZBGET_PASSWORD = None
NZBGET_CATEGORY = None
NZBGET_HOST = None
NZBGET_PRIORITY = 0

HEADPHONES_INDEXER = False

TRANSMISSION_HOST = None
TRANSMISSION_USERNAME = None
TRANSMISSION_PASSWORD = None

UTORRENT_HOST = None
UTORRENT_USERNAME = None
UTORRENT_PASSWORD = None
UTORRENT_LABEL = None

NEWZNAB = False
NEWZNAB_HOST = None
NEWZNAB_APIKEY = None
NEWZNAB_ENABLED = False
EXTRA_NEWZNABS = []

NZBSORG = False
NZBSORG_UID = None
NZBSORG_HASH = None

OMGWTFNZBS = False
OMGWTFNZBS_UID = None
OMGWTFNZBS_APIKEY = None

PREFERRED_WORDS = None
IGNORED_WORDS = None
REQUIRED_WORDS = None

LASTFM_USERNAME = None

LOSSY_MEDIA_FORMATS = ["mp3", "aac", "ogg", "ape", "m4a", "asf", "wma"]
LOSSLESS_MEDIA_FORMATS = ["flac"]
MEDIA_FORMATS = LOSSY_MEDIA_FORMATS + LOSSLESS_MEDIA_FORMATS

ALBUM_COMPLETION_PCT = None    # This is used in importer.py to determine how complete an album needs to be - to be considered "downloaded". Percentage from 0-100

TORRENTBLACKHOLE_DIR = None
NUMBEROFSEEDERS = 10
KAT = None
KAT_PROXY_URL = None
KAT_RATIO = None
MININOVA = None
MININOVA_RATIO = None
PIRATEBAY = None
PIRATEBAY_PROXY_URL = None
PIRATEBAY_RATIO = None
WAFFLES = None
WAFFLES_UID = None
WAFFLES_PASSKEY = None
WAFFLES_RATIO = None
RUTRACKER = None
RUTRACKER_USER = None
RUTRACKER_PASSWORD = None
RUTRACKER_RATIO = None
WHATCD = None
WHATCD_USERNAME = None
WHATCD_PASSWORD = None
WHATCD_RATIO = None
DOWNLOAD_TORRENT_DIR = None

INTERFACE = None
FOLDER_PERMISSIONS = None
FILE_PERMISSIONS = None

MUSIC_ENCODER = False
ENCODERFOLDER = None
ENCODER_PATH = None
ENCODER = None
XLDPROFILE = None
BITRATE = None
SAMPLINGFREQUENCY = None
ADVANCEDENCODER = None
ENCODEROUTPUTFORMAT = None
ENCODERQUALITY = None
ENCODERVBRCBR = None
ENCODERLOSSLESS = False
ENCODER_MULTICORE = False
ENCODER_MULTICORE_COUNT = 0
DELETE_LOSSLESS_FILES = False
GROWL_ENABLED = True
GROWL_HOST = None
GROWL_PASSWORD = None
GROWL_ONSNATCH = True
PROWL_ENABLED = True
PROWL_PRIORITY = 1
PROWL_KEYS = None
PROWL_ONSNATCH = True
XBMC_ENABLED = False
XBMC_HOST = None
XBMC_USERNAME = None
XBMC_PASSWORD = None
XBMC_UPDATE = False
XBMC_NOTIFY = False
LMS_ENABLED = False
LMS_HOST = None
PLEX_ENABLED = False
PLEX_SERVER_HOST = None
PLEX_CLIENT_HOST = None
PLEX_USERNAME = None
PLEX_PASSWORD = None
PLEX_UPDATE = False
PLEX_NOTIFY = False
NMA_ENABLED = False
NMA_APIKEY = None
NMA_PRIORITY = 0
NMA_ONSNATCH = None
PUSHALOT_ENABLED = False
PUSHALOT_APIKEY = None
PUSHALOT_ONSNATCH = None
SYNOINDEX_ENABLED = False
PUSHOVER_ENABLED = True
PUSHOVER_PRIORITY = 1
PUSHOVER_KEYS = None
PUSHOVER_ONSNATCH = True
PUSHOVER_APITOKEN = None
PUSHBULLET_ENABLED = True
PUSHBULLET_APIKEY = None
PUSHBULLET_DEVICEID = None
PUSHBULLET_ONSNATCH = True
TWITTER_ENABLED = False
TWITTER_ONSNATCH = False
TWITTER_USERNAME = None
TWITTER_PASSWORD = None
TWITTER_PREFIX = None
OSX_NOTIFY_ENABLED = False
OSX_NOTIFY_ONSNATCH = False
OSX_NOTIFY_APP = None
BOXCAR_ENABLED = False
BOXCAR_ONSNATCH = False
BOXCAR_TOKEN = None
SUBSONIC_ENABLED = False
SUBSONIC_HOST = None
SUBSONIC_USERNAME = None
SUBSONIC_PASSWORD = None
MIRRORLIST = ["musicbrainz.org","headphones","custom"]
MIRROR = None
CUSTOMHOST = None
CUSTOMPORT = None
CUSTOMSLEEP = None
HPUSER = None
HPPASS = None
SONGKICK_ENABLED = False
SONGKICK_APIKEY = None
SONGKICK_LOCATION = None
SONGKICK_FILTER_ENABLED = False
MPC_ENABLED = False

CACHE_SIZEMB = 32
JOURNAL_MODE = None

UMASK = None

VERIFY_SSL_CERT = True

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
    logger.debug("%s -> %s", item_name, my_val)
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

    logger.debug("%s -> %s", item_name, my_val if log else "******")
    return my_val

def initialize():

    with INIT_LOCK:

        global __INITIALIZED__, FULL_PATH, PROG_DIR, VERBOSE, QUIET, DAEMON, SYS_PLATFORM, DATA_DIR, CONFIG_FILE, CFG, CONFIG_VERSION, LOG_DIR, CACHE_DIR, \
                HTTP_PORT, HTTP_HOST, HTTP_USERNAME, HTTP_PASSWORD, HTTP_ROOT, HTTP_PROXY, LAUNCH_BROWSER, API_ENABLED, API_KEY, GIT_PATH, GIT_USER, GIT_BRANCH, DO_NOT_OVERRIDE_GIT_BRANCH, \
                CURRENT_VERSION, LATEST_VERSION, CHECK_GITHUB, CHECK_GITHUB_ON_STARTUP, CHECK_GITHUB_INTERVAL, MUSIC_DIR, DESTINATION_DIR, \
                LOSSLESS_DESTINATION_DIR, PREFERRED_QUALITY, PREFERRED_BITRATE, DETECT_BITRATE, ADD_ARTISTS, CORRECT_METADATA, FREEZE_DB, MOVE_FILES, \
                RENAME_FILES, FOLDER_FORMAT, FILE_FORMAT, FILE_UNDERSCORES, CLEANUP_FILES, KEEP_NFO, INCLUDE_EXTRAS, EXTRAS, AUTOWANT_UPCOMING, AUTOWANT_ALL, AUTOWANT_MANUALLY_ADDED, KEEP_TORRENT_FILES, PREFER_TORRENTS, OPEN_MAGNET_LINKS, \
                ADD_ALBUM_ART, ALBUM_ART_FORMAT, EMBED_ALBUM_ART, EMBED_LYRICS, REPLACE_EXISTING_FOLDERS, DOWNLOAD_DIR, BLACKHOLE, BLACKHOLE_DIR, USENET_RETENTION, SEARCH_INTERVAL, \
                TORRENTBLACKHOLE_DIR, NUMBEROFSEEDERS, KAT, KAT_PROXY_URL, KAT_RATIO, PIRATEBAY, PIRATEBAY_PROXY_URL, PIRATEBAY_RATIO, MININOVA, MININOVA_RATIO, WAFFLES, WAFFLES_UID, WAFFLES_PASSKEY, WAFFLES_RATIO, \
                RUTRACKER, RUTRACKER_USER, RUTRACKER_PASSWORD, RUTRACKER_RATIO, WHATCD, WHATCD_USERNAME, WHATCD_PASSWORD, WHATCD_RATIO, DOWNLOAD_TORRENT_DIR, \
                LIBRARYSCAN, LIBRARYSCAN_INTERVAL, DOWNLOAD_SCAN_INTERVAL, UPDATE_DB_INTERVAL, MB_IGNORE_AGE, TORRENT_REMOVAL_INTERVAL, SAB_HOST, SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, \
                NZBGET_USERNAME, NZBGET_PASSWORD, NZBGET_CATEGORY, NZBGET_PRIORITY, NZBGET_HOST, HEADPHONES_INDEXER, NZBMATRIX, TRANSMISSION_HOST, TRANSMISSION_USERNAME, TRANSMISSION_PASSWORD, \
                UTORRENT_HOST, UTORRENT_USERNAME, UTORRENT_PASSWORD, UTORRENT_LABEL, NEWZNAB, NEWZNAB_HOST, NEWZNAB_APIKEY, NEWZNAB_ENABLED, EXTRA_NEWZNABS, \
                NZBSORG, NZBSORG_UID, NZBSORG_HASH, OMGWTFNZBS, OMGWTFNZBS_UID, OMGWTFNZBS_APIKEY, \
                NZB_DOWNLOADER, TORRENT_DOWNLOADER, PREFERRED_WORDS, REQUIRED_WORDS, IGNORED_WORDS, LASTFM_USERNAME, \
                INTERFACE, FOLDER_PERMISSIONS, FILE_PERMISSIONS, ENCODERFOLDER, ENCODER_PATH, ENCODER, XLDPROFILE, BITRATE, SAMPLINGFREQUENCY, \
                MUSIC_ENCODER, ADVANCEDENCODER, ENCODEROUTPUTFORMAT, ENCODERQUALITY, ENCODERVBRCBR, ENCODERLOSSLESS, ENCODER_MULTICORE, ENCODER_MULTICORE_COUNT, DELETE_LOSSLESS_FILES, \
                GROWL_ENABLED, GROWL_HOST, GROWL_PASSWORD, GROWL_ONSNATCH, PROWL_ENABLED, PROWL_PRIORITY, PROWL_KEYS, PROWL_ONSNATCH, PUSHOVER_ENABLED, PUSHOVER_PRIORITY, PUSHOVER_KEYS, PUSHOVER_ONSNATCH, PUSHOVER_APITOKEN, MIRRORLIST, \
                TWITTER_ENABLED, TWITTER_ONSNATCH, TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_PREFIX, OSX_NOTIFY_ENABLED, OSX_NOTIFY_ONSNATCH, OSX_NOTIFY_APP, BOXCAR_ENABLED, BOXCAR_ONSNATCH, BOXCAR_TOKEN, \
                PUSHBULLET_ENABLED, PUSHBULLET_APIKEY, PUSHBULLET_DEVICEID, PUSHBULLET_ONSNATCH, \
                MIRROR, CUSTOMHOST, CUSTOMPORT, CUSTOMSLEEP, HPUSER, HPPASS, XBMC_ENABLED, XBMC_HOST, XBMC_USERNAME, XBMC_PASSWORD, XBMC_UPDATE, \
                XBMC_NOTIFY, LMS_ENABLED, LMS_HOST, NMA_ENABLED, NMA_APIKEY, NMA_PRIORITY, NMA_ONSNATCH, SYNOINDEX_ENABLED, ALBUM_COMPLETION_PCT, PREFERRED_BITRATE_HIGH_BUFFER, \
                PREFERRED_BITRATE_LOW_BUFFER, PREFERRED_BITRATE_ALLOW_LOSSLESS, LOSSLESS_BITRATE_FROM, LOSSLESS_BITRATE_TO, CACHE_SIZEMB, JOURNAL_MODE, UMASK, ENABLE_HTTPS, HTTPS_CERT, HTTPS_KEY, \
                PLEX_ENABLED, PLEX_SERVER_HOST, PLEX_CLIENT_HOST, PLEX_USERNAME, PLEX_PASSWORD, PLEX_UPDATE, PLEX_NOTIFY, PUSHALOT_ENABLED, PUSHALOT_APIKEY, \
                PUSHALOT_ONSNATCH, SONGKICK_ENABLED, SONGKICK_APIKEY, SONGKICK_LOCATION, SONGKICK_FILTER_ENABLED, SUBSONIC_ENABLED, SUBSONIC_HOST, SUBSONIC_USERNAME, SUBSONIC_PASSWORD, VERIFY_SSL_CERT


        if __INITIALIZED__:
            return False

        # Make sure all the config sections exist
        for section in ('General', 'SABnzbd', 'NZBget', 'Transmission',
                        'uTorrent', 'Headphones', 'Newznab', 'NZBsorg',
                        'omgwtfnzbs', 'Piratebay', 'Kat', 'Mininova', 'Waffles',
                        'Rutracker', 'What.cd', 'Growl', 'Prowl', 'Pushover',
                        'PushBullet', 'XBMC', 'LMS', 'Plex', 'NMA', 'Pushalot',
                        'Synoindex', 'Twitter', 'OSX_Notify', 'Boxcar',
                        'Songkick', 'Advanced'):
            CheckSection(section)

        # Set global variables based on config file or use defaults
        CONFIG_VERSION = check_setting_str(CFG, 'General', 'config_version', '0')

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
        HTTP_PROXY = bool(check_setting_int(CFG, 'General', 'http_proxy', 0))
        ENABLE_HTTPS = bool(check_setting_int(CFG, 'General', 'enable_https', 0))
        HTTPS_CERT = check_setting_str(CFG, 'General', 'https_cert', os.path.join(DATA_DIR, 'server.crt'))
        HTTPS_KEY = check_setting_str(CFG, 'General', 'https_key', os.path.join(DATA_DIR, 'server.key'))
        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))
        API_ENABLED = bool(check_setting_int(CFG, 'General', 'api_enabled', 0))
        API_KEY = check_setting_str(CFG, 'General', 'api_key', '')
        GIT_PATH = check_setting_str(CFG, 'General', 'git_path', '')
        GIT_USER = check_setting_str(CFG, 'General', 'git_user', 'rembo10')
        GIT_BRANCH = check_setting_str(CFG, 'General', 'git_branch', 'master')
        DO_NOT_OVERRIDE_GIT_BRANCH = check_setting_int(CFG, 'General', 'do_not_override_git_branch', 0)
        LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', '')
        CACHE_DIR = check_setting_str(CFG, 'General', 'cache_dir', '')

        CHECK_GITHUB = bool(check_setting_int(CFG, 'General', 'check_github', 1))
        CHECK_GITHUB_ON_STARTUP = bool(check_setting_int(CFG, 'General', 'check_github_on_startup', 1))
        CHECK_GITHUB_INTERVAL = check_setting_int(CFG, 'General', 'check_github_interval', 360)

        MUSIC_DIR = check_setting_str(CFG, 'General', 'music_dir', '')
        DESTINATION_DIR = check_setting_str(CFG, 'General', 'destination_dir', '')
        LOSSLESS_DESTINATION_DIR = check_setting_str(CFG, 'General', 'lossless_destination_dir', '')
        PREFERRED_QUALITY = check_setting_int(CFG, 'General', 'preferred_quality', 0)
        PREFERRED_BITRATE = check_setting_str(CFG, 'General', 'preferred_bitrate', '')
        PREFERRED_BITRATE_HIGH_BUFFER = check_setting_int(CFG, 'General', 'preferred_bitrate_high_buffer', '')
        PREFERRED_BITRATE_LOW_BUFFER = check_setting_int(CFG, 'General', 'preferred_bitrate_low_buffer', '')
        PREFERRED_BITRATE_ALLOW_LOSSLESS = bool(check_setting_int(CFG, 'General', 'preferred_bitrate_allow_lossless', 0))
        DETECT_BITRATE = bool(check_setting_int(CFG, 'General', 'detect_bitrate', 0))
        LOSSLESS_BITRATE_FROM = check_setting_int(CFG, 'General', 'lossless_bitrate_from', '')
        LOSSLESS_BITRATE_TO = check_setting_int(CFG, 'General', 'lossless_bitrate_to', '')
        ADD_ARTISTS = bool(check_setting_int(CFG, 'General', 'auto_add_artists', 1))
        CORRECT_METADATA = bool(check_setting_int(CFG, 'General', 'correct_metadata', 0))
        FREEZE_DB = bool(check_setting_int(CFG, 'General', 'freeze_db', 0))
        MOVE_FILES = bool(check_setting_int(CFG, 'General', 'move_files', 0))
        RENAME_FILES = bool(check_setting_int(CFG, 'General', 'rename_files', 0))
        FOLDER_FORMAT = check_setting_str(CFG, 'General', 'folder_format', 'Artist/Album [Year]')
        FILE_FORMAT = check_setting_str(CFG, 'General', 'file_format', 'Track Artist - Album [Year] - Title')
        FILE_UNDERSCORES = bool(check_setting_int(CFG, 'General', 'file_underscores', 0))
        CLEANUP_FILES = bool(check_setting_int(CFG, 'General', 'cleanup_files', 0))
        KEEP_NFO = bool(check_setting_int(CFG, 'General', 'keep_nfo', 0))
        ADD_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'add_album_art', 0))
        ALBUM_ART_FORMAT = check_setting_str(CFG, 'General', 'album_art_format', 'folder')
        EMBED_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'embed_album_art', 0))
        EMBED_LYRICS = bool(check_setting_int(CFG, 'General', 'embed_lyrics', 0))
        REPLACE_EXISTING_FOLDERS = bool(check_setting_int(CFG, 'General', 'replace_existing_folders', 0))
        NZB_DOWNLOADER = check_setting_int(CFG, 'General', 'nzb_downloader', 0)
        TORRENT_DOWNLOADER = check_setting_int(CFG, 'General', 'torrent_downloader', 0)
        DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'download_dir', '')
        BLACKHOLE = bool(check_setting_int(CFG, 'General', 'blackhole', 0))
        BLACKHOLE_DIR = check_setting_str(CFG, 'General', 'blackhole_dir', '')
        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', '1500')
        INCLUDE_EXTRAS = bool(check_setting_int(CFG, 'General', 'include_extras', 0))
        EXTRAS = check_setting_str(CFG, 'General', 'extras', '')
        AUTOWANT_UPCOMING = bool(check_setting_int(CFG, 'General', 'autowant_upcoming', 1))
        AUTOWANT_ALL = bool(check_setting_int(CFG, 'General', 'autowant_all', 0))
        AUTOWANT_MANUALLY_ADDED  = bool(check_setting_int(CFG, 'General', 'autowant_manually_added', 1))
        KEEP_TORRENT_FILES = bool(check_setting_int(CFG, 'General', 'keep_torrent_files', 0))
        PREFER_TORRENTS = check_setting_int(CFG, 'General', 'prefer_torrents', 0)
        OPEN_MAGNET_LINKS = bool(check_setting_int(CFG, 'General', 'open_magnet_links', 0))

        SEARCH_INTERVAL = check_setting_int(CFG, 'General', 'search_interval', 1440)
        LIBRARYSCAN = bool(check_setting_int(CFG, 'General', 'libraryscan', 1))
        LIBRARYSCAN_INTERVAL = check_setting_int(CFG, 'General', 'libraryscan_interval', 300)
        DOWNLOAD_SCAN_INTERVAL = check_setting_int(CFG, 'General', 'download_scan_interval', 5)
        UPDATE_DB_INTERVAL = check_setting_int(CFG, 'General', 'update_db_interval', 24)
        MB_IGNORE_AGE = check_setting_int(CFG, 'General', 'mb_ignore_age', 365)
        TORRENT_REMOVAL_INTERVAL = check_setting_int(CFG, 'General', 'torrent_removal_interval', 720)

        TORRENTBLACKHOLE_DIR = check_setting_str(CFG, 'General', 'torrentblackhole_dir', '')
        NUMBEROFSEEDERS = check_setting_str(CFG, 'General', 'numberofseeders', '10')
        DOWNLOAD_TORRENT_DIR = check_setting_str(CFG, 'General', 'download_torrent_dir', '')

        KAT = bool(check_setting_int(CFG, 'Kat', 'kat', 0))
        KAT_PROXY_URL = check_setting_str(CFG, 'Kat', 'kat_proxy_url', '')
        KAT_RATIO = check_setting_str(CFG, 'Kat', 'kat_ratio', '')

        PIRATEBAY = bool(check_setting_int(CFG, 'Piratebay', 'piratebay', 0))
        PIRATEBAY_PROXY_URL = check_setting_str(CFG, 'Piratebay', 'piratebay_proxy_url', '')
        PIRATEBAY_RATIO = check_setting_str(CFG, 'Piratebay', 'piratebay_ratio', '')

        MININOVA = bool(check_setting_int(CFG, 'Mininova', 'mininova', 0))
        MININOVA_RATIO = check_setting_str(CFG, 'Mininova', 'mininova_ratio', '')

        WAFFLES = bool(check_setting_int(CFG, 'Waffles', 'waffles', 0))
        WAFFLES_UID = check_setting_str(CFG, 'Waffles', 'waffles_uid', '')
        WAFFLES_PASSKEY = check_setting_str(CFG, 'Waffles', 'waffles_passkey', '')
        WAFFLES_RATIO = check_setting_str(CFG, 'Waffles', 'waffles_ratio', '')

        RUTRACKER = bool(check_setting_int(CFG, 'Rutracker', 'rutracker', 0))
        RUTRACKER_USER = check_setting_str(CFG, 'Rutracker', 'rutracker_user', '')
        RUTRACKER_PASSWORD = check_setting_str(CFG, 'Rutracker', 'rutracker_password', '')
        RUTRACKER_RATIO = check_setting_str(CFG, 'Rutracker', 'rutracker_ratio', '')

        WHATCD = bool(check_setting_int(CFG, 'What.cd', 'whatcd', 0))
        WHATCD_USERNAME = check_setting_str(CFG, 'What.cd', 'whatcd_username', '')
        WHATCD_PASSWORD = check_setting_str(CFG, 'What.cd', 'whatcd_password', '')
        WHATCD_RATIO = check_setting_str(CFG, 'What.cd', 'whatcd_ratio', '')

        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')
        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', '')

        NZBGET_USERNAME = check_setting_str(CFG, 'NZBget', 'nzbget_username', 'nzbget')
        NZBGET_PASSWORD = check_setting_str(CFG, 'NZBget', 'nzbget_password', '')
        NZBGET_CATEGORY = check_setting_str(CFG, 'NZBget', 'nzbget_category', '')
        NZBGET_HOST = check_setting_str(CFG, 'NZBget', 'nzbget_host', '')
        NZBGET_PRIORITY = check_setting_int(CFG, 'NZBget', 'nzbget_priority', 0)

        HEADPHONES_INDEXER = bool(check_setting_int(CFG, 'Headphones', 'headphones_indexer', 0))

        TRANSMISSION_HOST = check_setting_str(CFG, 'Transmission', 'transmission_host', '')
        TRANSMISSION_USERNAME = check_setting_str(CFG, 'Transmission', 'transmission_username', '')
        TRANSMISSION_PASSWORD = check_setting_str(CFG, 'Transmission', 'transmission_password', '')

        UTORRENT_HOST = check_setting_str(CFG, 'uTorrent', 'utorrent_host', '')
        UTORRENT_USERNAME = check_setting_str(CFG, 'uTorrent', 'utorrent_username', '')
        UTORRENT_PASSWORD = check_setting_str(CFG, 'uTorrent', 'utorrent_password', '')
        UTORRENT_LABEL = check_setting_str(CFG, 'uTorrent', 'utorrent_label', '')

        NEWZNAB = bool(check_setting_int(CFG, 'Newznab', 'newznab', 0))
        NEWZNAB_HOST = check_setting_str(CFG, 'Newznab', 'newznab_host', '')
        NEWZNAB_APIKEY = check_setting_str(CFG, 'Newznab', 'newznab_apikey', '')
        NEWZNAB_ENABLED = bool(check_setting_int(CFG, 'Newznab', 'newznab_enabled', 1))

        # Need to pack the extra newznabs back into a list of tuples
        flattened_newznabs = check_setting_str(CFG, 'Newznab', 'extra_newznabs', [], log=False)
        EXTRA_NEWZNABS = list(itertools.izip(*[itertools.islice(flattened_newznabs, i, None, 3) for i in range(3)]))

        NZBSORG = bool(check_setting_int(CFG, 'NZBsorg', 'nzbsorg', 0))
        NZBSORG_UID = check_setting_str(CFG, 'NZBsorg', 'nzbsorg_uid', '')
        NZBSORG_HASH = check_setting_str(CFG, 'NZBsorg', 'nzbsorg_hash', '')

        OMGWTFNZBS = bool(check_setting_int(CFG, 'omgwtfnzbs', 'omgwtfnzbs', 0))
        OMGWTFNZBS_UID = check_setting_str(CFG, 'omgwtfnzbs', 'omgwtfnzbs_uid', '')
        OMGWTFNZBS_APIKEY = check_setting_str(CFG, 'omgwtfnzbs', 'omgwtfnzbs_apikey', '')

        PREFERRED_WORDS = check_setting_str(CFG, 'General', 'preferred_words', '')
        IGNORED_WORDS = check_setting_str(CFG, 'General', 'ignored_words', '')
        REQUIRED_WORDS = check_setting_str(CFG, 'General', 'required_words', '')

        LASTFM_USERNAME = check_setting_str(CFG, 'General', 'lastfm_username', '')

        INTERFACE = check_setting_str(CFG, 'General', 'interface', 'default')
        FOLDER_PERMISSIONS = check_setting_str(CFG, 'General', 'folder_permissions', '0755')
        FILE_PERMISSIONS = check_setting_str(CFG, 'General', 'file_permissions', '0644')

        ENCODERFOLDER = check_setting_str(CFG, 'General', 'encoderfolder', '')
        ENCODER_PATH = check_setting_str(CFG, 'General', 'encoder_path', '')
        ENCODER = check_setting_str(CFG, 'General', 'encoder', 'ffmpeg')
        XLDPROFILE = check_setting_str(CFG, 'General', 'xldprofile', '')
        BITRATE = check_setting_int(CFG, 'General', 'bitrate', 192)
        SAMPLINGFREQUENCY= check_setting_int(CFG, 'General', 'samplingfrequency', 44100)
        MUSIC_ENCODER = bool(check_setting_int(CFG, 'General', 'music_encoder', 0))
        ADVANCEDENCODER = check_setting_str(CFG, 'General', 'advancedencoder', '')
        ENCODEROUTPUTFORMAT = check_setting_str(CFG, 'General', 'encoderoutputformat', 'mp3')
        ENCODERQUALITY = check_setting_int(CFG, 'General', 'encoderquality', 2)
        ENCODERVBRCBR = check_setting_str(CFG, 'General', 'encodervbrcbr', 'cbr')
        ENCODERLOSSLESS = bool(check_setting_int(CFG, 'General', 'encoderlossless', 1))
        ENCODER_MULTICORE = bool(check_setting_int(CFG, 'General', 'encoder_multicore', 0))
        ENCODER_MULTICORE_COUNT = max(0, check_setting_int(CFG, 'General', 'encoder_multicore_count', 0))
        DELETE_LOSSLESS_FILES = bool(check_setting_int(CFG, 'General', 'delete_lossless_files', 1))

        GROWL_ENABLED = bool(check_setting_int(CFG, 'Growl', 'growl_enabled', 0))
        GROWL_HOST = check_setting_str(CFG, 'Growl', 'growl_host', '')
        GROWL_PASSWORD = check_setting_str(CFG, 'Growl', 'growl_password', '')
        GROWL_ONSNATCH = bool(check_setting_int(CFG, 'Growl', 'growl_onsnatch', 0))

        PROWL_ENABLED = bool(check_setting_int(CFG, 'Prowl', 'prowl_enabled', 0))
        PROWL_KEYS = check_setting_str(CFG, 'Prowl', 'prowl_keys', '')
        PROWL_ONSNATCH = bool(check_setting_int(CFG, 'Prowl', 'prowl_onsnatch', 0))
        PROWL_PRIORITY = check_setting_int(CFG, 'Prowl', 'prowl_priority', 0)

        XBMC_ENABLED = bool(check_setting_int(CFG, 'XBMC', 'xbmc_enabled', 0))
        XBMC_HOST = check_setting_str(CFG, 'XBMC', 'xbmc_host', '')
        XBMC_USERNAME = check_setting_str(CFG, 'XBMC', 'xbmc_username', '')
        XBMC_PASSWORD = check_setting_str(CFG, 'XBMC', 'xbmc_password', '')
        XBMC_UPDATE = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update', 0))
        XBMC_NOTIFY = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify', 0))

        LMS_ENABLED = bool(check_setting_int(CFG, 'LMS', 'lms_enabled', 0))
        LMS_HOST = check_setting_str(CFG, 'LMS', 'lms_host', '')

        PLEX_ENABLED = bool(check_setting_int(CFG, 'Plex', 'plex_enabled', 0))
        PLEX_SERVER_HOST = check_setting_str(CFG, 'Plex', 'plex_server_host', '')
        PLEX_CLIENT_HOST = check_setting_str(CFG, 'Plex', 'plex_client_host', '')
        PLEX_USERNAME = check_setting_str(CFG, 'Plex', 'plex_username', '')
        PLEX_PASSWORD = check_setting_str(CFG, 'Plex', 'plex_password', '')
        PLEX_UPDATE = bool(check_setting_int(CFG, 'Plex', 'plex_update', 0))
        PLEX_NOTIFY = bool(check_setting_int(CFG, 'Plex', 'plex_notify', 0))

        NMA_ENABLED = bool(check_setting_int(CFG, 'NMA', 'nma_enabled', 0))
        NMA_APIKEY = check_setting_str(CFG, 'NMA', 'nma_apikey', '')
        NMA_PRIORITY = check_setting_int(CFG, 'NMA', 'nma_priority', 0)
        NMA_ONSNATCH = bool(check_setting_int(CFG, 'NMA', 'nma_onsnatch', 0))

        PUSHALOT_ENABLED = bool(check_setting_int(CFG, 'Pushalot', 'pushalot_enabled', 0))
        PUSHALOT_APIKEY = check_setting_str(CFG, 'Pushalot', 'pushalot_apikey', '')
        PUSHALOT_ONSNATCH = bool(check_setting_int(CFG, 'Pushalot', 'pushalot_onsnatch', 0))

        SYNOINDEX_ENABLED = bool(check_setting_int(CFG, 'Synoindex', 'synoindex_enabled', 0))

        PUSHOVER_ENABLED = bool(check_setting_int(CFG, 'Pushover', 'pushover_enabled', 0))
        PUSHOVER_KEYS = check_setting_str(CFG, 'Pushover', 'pushover_keys', '')
        PUSHOVER_ONSNATCH = bool(check_setting_int(CFG, 'Pushover', 'pushover_onsnatch', 0))
        PUSHOVER_PRIORITY = check_setting_int(CFG, 'Pushover', 'pushover_priority', 0)
        PUSHOVER_APITOKEN = check_setting_str(CFG, 'Pushover', 'pushover_apitoken', '')

        PUSHBULLET_ENABLED = bool(check_setting_int(CFG, 'PushBullet', 'pushbullet_enabled', 0))
        PUSHBULLET_APIKEY = check_setting_str(CFG, 'PushBullet', 'pushbullet_apikey', '')
        PUSHBULLET_DEVICEID = check_setting_str(CFG, 'PushBullet', 'pushbullet_deviceid', '')
        PUSHBULLET_ONSNATCH = bool(check_setting_int(CFG, 'PushBullet', 'pushbullet_onsnatch', 0))

        TWITTER_ENABLED = bool(check_setting_int(CFG, 'Twitter', 'twitter_enabled', 0))
        TWITTER_ONSNATCH = bool(check_setting_int(CFG, 'Twitter', 'twitter_onsnatch', 0))
        TWITTER_USERNAME = check_setting_str(CFG, 'Twitter', 'twitter_username', '')
        TWITTER_PASSWORD = check_setting_str(CFG, 'Twitter', 'twitter_password', '')
        TWITTER_PREFIX = check_setting_str(CFG, 'Twitter', 'twitter_prefix', 'Headphones')

        OSX_NOTIFY_ENABLED = bool(check_setting_int(CFG, 'OSX_Notify', 'osx_notify_enabled', 0))
        OSX_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'OSX_Notify', 'osx_notify_onsnatch', 0))
        OSX_NOTIFY_APP = check_setting_str(CFG, 'OSX_Notify', 'osx_notify_app', '/Applications/Headphones')

        BOXCAR_ENABLED = bool(check_setting_int(CFG, 'Boxcar', 'boxcar_enabled', 0))
        BOXCAR_ONSNATCH = bool(check_setting_int(CFG, 'Boxcar', 'boxcar_onsnatch', 0))
        BOXCAR_TOKEN = check_setting_str(CFG, 'Boxcar', 'boxcar_token', '')

        SUBSONIC_ENABLED = bool(check_setting_int(CFG, 'Subsonic', 'subsonic_enabled', 0))
        SUBSONIC_HOST = check_setting_str(CFG, 'Subsonic', 'subsonic_host', '')
        SUBSONIC_USERNAME = check_setting_str(CFG, 'Subsonic', 'subsonic_username', '')
        SUBSONIC_PASSWORD = check_setting_str(CFG, 'Subsonic', 'subsonic_password', '')

        SONGKICK_ENABLED = bool(check_setting_int(CFG, 'Songkick', 'songkick_enabled', 1))
        SONGKICK_APIKEY = check_setting_str(CFG, 'Songkick', 'songkick_apikey', 'nd1We7dFW2RqxPw8')
        SONGKICK_LOCATION = check_setting_str(CFG, 'Songkick', 'songkick_location', '')
        SONGKICK_FILTER_ENABLED = bool(check_setting_int(CFG, 'Songkick', 'songkick_filter_enabled', 0))

        MIRROR = check_setting_str(CFG, 'General', 'mirror', 'musicbrainz.org')
        CUSTOMHOST = check_setting_str(CFG, 'General', 'customhost', 'localhost')
        CUSTOMPORT = check_setting_int(CFG, 'General', 'customport', 5000)
        CUSTOMSLEEP = check_setting_int(CFG, 'General', 'customsleep', 1)
        HPUSER = check_setting_str(CFG, 'General', 'hpuser', '')
        HPPASS = check_setting_str(CFG, 'General', 'hppass', '')

        CACHE_SIZEMB = check_setting_int(CFG,'Advanced','cache_sizemb',32)
        JOURNAL_MODE = check_setting_int(CFG,'Advanced', 'journal_mode', 'wal')

        ALBUM_COMPLETION_PCT = check_setting_int(CFG, 'Advanced', 'album_completion_pct', 80)

        VERIFY_SSL_CERT = bool(check_setting_int(CFG, 'Advanced', 'verify_ssl_cert', 1))

        # update folder formats in the config & bump up config version
        if CONFIG_VERSION == '0':
            from headphones.helpers import replace_all
            file_values = { 'tracknumber':  'Track', 'title': 'Title','artist' : 'Artist', 'album' : 'Album', 'year' : 'Year' }
            folder_values = { 'artist' : 'Artist', 'album':'Album', 'year' : 'Year', 'releasetype' : 'Type', 'first' : 'First', 'lowerfirst' : 'first' }
            FILE_FORMAT = replace_all(FILE_FORMAT, file_values)
            FOLDER_FORMAT = replace_all(FOLDER_FORMAT, folder_values)

            CONFIG_VERSION = '1'

        if CONFIG_VERSION == '1':

            from headphones.helpers import replace_all

            file_values = { 'Track':        '$Track',
                            'Title':        '$Title',
                            'Artist':       '$Artist',
                            'Album':        '$Album',
                            'Year':         '$Year',
                            'track':        '$track',
                            'title':        '$title',
                            'artist':       '$artist',
                            'album':        '$album',
                            'year':         '$year'
                            }
            folder_values = {   'Artist':   '$Artist',
                                'Album':    '$Album',
                                'Year':     '$Year',
                                'Type':     '$Type',
                                'First':    '$First',
                                'artist':   '$artist',
                                'album':    '$album',
                                'year':     '$year',
                                'type':     '$type',
                                'first':    '$first'
                            }
            FILE_FORMAT = replace_all(FILE_FORMAT, file_values)
            FOLDER_FORMAT = replace_all(FOLDER_FORMAT, folder_values)

            CONFIG_VERSION = '2'

        if CONFIG_VERSION == '2':

            # Update the config to use direct path to the encoder rather than the encoder folder
            if ENCODERFOLDER:
                ENCODER_PATH = os.path.join(ENCODERFOLDER, ENCODER)
            CONFIG_VERSION = '3'

        if CONFIG_VERSION == '3':
            #Update the BLACKHOLE option to the NZB_DOWNLOADER format
            if BLACKHOLE:
                NZB_DOWNLOADER = 2
            CONFIG_VERSION = '4'

        # Enable Headphones Indexer if they have a VIP account
        if CONFIG_VERSION == '4':
            if HPUSER and HPPASS:
                HEADPHONES_INDEXER = True
            CONFIG_VERSION = '5'

        if not LOG_DIR:
            LOG_DIR = os.path.join(DATA_DIR, 'logs')

        if not os.path.exists(LOG_DIR):
            try:
                os.makedirs(LOG_DIR)
            except OSError:
                if VERBOSE:
                    sys.stderr.write('Unable to create the log directory. Logging to screen only.\n')

        # Start the logger, disable console if needed
        logger.initLogger(console=not QUIET, verbose=VERBOSE)

        if not CACHE_DIR:
            # Put the cache dir in the data dir for now
            CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CACHE_DIR):
            try:
                os.makedirs(CACHE_DIR)
            except OSError:
                logger.error('Could not create cache dir. Check permissions of datadir: %s', DATA_DIR)

        # Sanity check for search interval. Set it to at least 6 hours
        if SEARCH_INTERVAL < 360:
            logger.info("Search interval too low. Resetting to 6 hour minimum")
            SEARCH_INTERVAL = 360

        # Initialize the database
        logger.info('Checking to see if the database has all tables....')
        try:
            dbcheck()
        except Exception, e:
            logger.error("Can't connect to the database: %s", e)

        # Get the currently installed version - returns None, 'win32' or the git hash
        # Also sets INSTALL_TYPE variable to 'win', 'git' or 'source'
        CURRENT_VERSION, GIT_BRANCH = versioncheck.getVersion()

        # Check for new versions
        if CHECK_GITHUB_ON_STARTUP:
            try:
                LATEST_VERSION = versioncheck.checkGithub()
            except:
                logger.exception("Unhandled exception")
                LATEST_VERSION = CURRENT_VERSION
        else:
            LATEST_VERSION = CURRENT_VERSION

        # Store the original umask
        UMASK = os.umask(0)
        os.umask(UMASK)

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
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]", e.strerror, e.errno)

    os.setsid()

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)  # @UndefinedVariable - only available in UNIX
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2nd fork failed: %s [%d]", e.strerror, e.errno)

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = os.getpid()
    logger.info('Daemonized to PID: %d', pid)

    if CREATEPID:
        logger.info("Writing PID %d to %s", pid, PIDFILE)
        with file(PIDFILE, 'w') as fp:
            fp.write("%s\n" % pid)

def launch_browser(host, port, root):

    if host == '0.0.0.0':
        host = 'localhost'

    if ENABLE_HTTPS:
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
    except Exception as e:
        logger.error('Could not launch browser: %s', e)

def config_write():
    """
    Write configuration to file. If an IOError occures during a write, it will
    be caught.
    """

    new_config = ConfigObj(encoding="UTF-8")
    new_config.filename = CONFIG_FILE

    new_config['General'] = {}
    new_config['General']['config_version'] = CONFIG_VERSION
    new_config['General']['http_port'] = HTTP_PORT
    new_config['General']['http_host'] = HTTP_HOST
    new_config['General']['http_username'] = HTTP_USERNAME
    new_config['General']['http_password'] = HTTP_PASSWORD
    new_config['General']['http_root'] = HTTP_ROOT
    new_config['General']['http_proxy'] = int(HTTP_PROXY)
    new_config['General']['enable_https'] = int(ENABLE_HTTPS)
    new_config['General']['https_cert'] = HTTPS_CERT
    new_config['General']['https_key'] = HTTPS_KEY
    new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)
    new_config['General']['api_enabled'] = int(API_ENABLED)
    new_config['General']['api_key'] = API_KEY
    new_config['General']['log_dir'] = LOG_DIR
    new_config['General']['cache_dir'] = CACHE_DIR
    new_config['General']['git_path'] = GIT_PATH
    new_config['General']['git_user'] = GIT_USER
    new_config['General']['git_branch'] = GIT_BRANCH
    new_config['General']['do_not_override_git_branch'] = int(DO_NOT_OVERRIDE_GIT_BRANCH)

    new_config['General']['check_github'] = int(CHECK_GITHUB)
    new_config['General']['check_github_on_startup'] = int(CHECK_GITHUB_ON_STARTUP)
    new_config['General']['check_github_interval'] = CHECK_GITHUB_INTERVAL

    new_config['General']['music_dir'] = MUSIC_DIR
    new_config['General']['destination_dir'] = DESTINATION_DIR
    new_config['General']['lossless_destination_dir'] = LOSSLESS_DESTINATION_DIR
    new_config['General']['preferred_quality'] = PREFERRED_QUALITY
    new_config['General']['preferred_bitrate'] = PREFERRED_BITRATE
    new_config['General']['preferred_bitrate_high_buffer'] = PREFERRED_BITRATE_HIGH_BUFFER
    new_config['General']['preferred_bitrate_low_buffer'] = PREFERRED_BITRATE_LOW_BUFFER
    new_config['General']['preferred_bitrate_allow_lossless'] = int(PREFERRED_BITRATE_ALLOW_LOSSLESS)
    new_config['General']['detect_bitrate'] = int(DETECT_BITRATE)
    new_config['General']['lossless_bitrate_from'] = LOSSLESS_BITRATE_FROM
    new_config['General']['lossless_bitrate_to'] = LOSSLESS_BITRATE_TO
    new_config['General']['auto_add_artists'] = int(ADD_ARTISTS)
    new_config['General']['correct_metadata'] = int(CORRECT_METADATA)
    new_config['General']['freeze_db'] = int(FREEZE_DB)
    new_config['General']['move_files'] = int(MOVE_FILES)
    new_config['General']['rename_files'] = int(RENAME_FILES)
    new_config['General']['folder_format'] = FOLDER_FORMAT
    new_config['General']['file_format'] = FILE_FORMAT
    new_config['General']['file_underscores'] = int(FILE_UNDERSCORES)
    new_config['General']['cleanup_files'] = int(CLEANUP_FILES)
    new_config['General']['keep_nfo'] = int(KEEP_NFO)
    new_config['General']['add_album_art'] = int(ADD_ALBUM_ART)
    new_config['General']['album_art_format'] = ALBUM_ART_FORMAT
    new_config['General']['embed_album_art'] = int(EMBED_ALBUM_ART)
    new_config['General']['embed_lyrics'] = int(EMBED_LYRICS)
    new_config['General']['replace_existing_folders'] = int(REPLACE_EXISTING_FOLDERS)
    new_config['General']['nzb_downloader'] = NZB_DOWNLOADER
    new_config['General']['torrent_downloader'] = TORRENT_DOWNLOADER
    new_config['General']['download_dir'] = DOWNLOAD_DIR
    new_config['General']['blackhole_dir'] = BLACKHOLE_DIR
    new_config['General']['usenet_retention'] = USENET_RETENTION
    new_config['General']['include_extras'] = int(INCLUDE_EXTRAS)
    new_config['General']['extras'] = EXTRAS
    new_config['General']['autowant_upcoming'] = int(AUTOWANT_UPCOMING)
    new_config['General']['autowant_all'] = int(AUTOWANT_ALL)
    new_config['General']['autowant_manually_added'] = int(AUTOWANT_MANUALLY_ADDED)
    new_config['General']['keep_torrent_files'] = int(KEEP_TORRENT_FILES)
    new_config['General']['prefer_torrents'] = PREFER_TORRENTS
    new_config['General']['open_magnet_links'] = OPEN_MAGNET_LINKS

    new_config['General']['numberofseeders'] = NUMBEROFSEEDERS
    new_config['General']['torrentblackhole_dir'] = TORRENTBLACKHOLE_DIR
    new_config['General']['download_torrent_dir'] = DOWNLOAD_TORRENT_DIR

    new_config['Kat'] = {}
    new_config['Kat']['kat'] = int(KAT)
    new_config['Kat']['kat_proxy_url'] = KAT_PROXY_URL
    new_config['Kat']['kat_ratio'] = KAT_RATIO

    new_config['Mininova'] = {}
    new_config['Mininova']['mininova'] = int(MININOVA)
    new_config['Mininova']['mininova_ratio'] = MININOVA_RATIO

    new_config['Piratebay'] = {}
    new_config['Piratebay']['piratebay'] = int(PIRATEBAY)
    new_config['Piratebay']['piratebay_proxy_url'] = PIRATEBAY_PROXY_URL
    new_config['Piratebay']['piratebay_ratio'] = PIRATEBAY_RATIO

    new_config['Waffles'] = {}
    new_config['Waffles']['waffles'] = int(WAFFLES)
    new_config['Waffles']['waffles_uid'] = WAFFLES_UID
    new_config['Waffles']['waffles_passkey'] = WAFFLES_PASSKEY
    new_config['Waffles']['waffles_ratio'] = WAFFLES_RATIO

    new_config['Rutracker'] = {}
    new_config['Rutracker']['rutracker'] = int(RUTRACKER)
    new_config['Rutracker']['rutracker_user'] = RUTRACKER_USER
    new_config['Rutracker']['rutracker_password'] = RUTRACKER_PASSWORD
    new_config['Rutracker']['rutracker_ratio'] = RUTRACKER_RATIO

    new_config['What.cd'] = {}
    new_config['What.cd']['whatcd'] = int(WHATCD)
    new_config['What.cd']['whatcd_username'] = WHATCD_USERNAME
    new_config['What.cd']['whatcd_password'] = WHATCD_PASSWORD
    new_config['What.cd']['whatcd_ratio'] = WHATCD_RATIO

    new_config['General']['search_interval'] = SEARCH_INTERVAL
    new_config['General']['libraryscan'] = int(LIBRARYSCAN)
    new_config['General']['libraryscan_interval'] = LIBRARYSCAN_INTERVAL
    new_config['General']['download_scan_interval'] = DOWNLOAD_SCAN_INTERVAL
    new_config['General']['update_db_interval'] = UPDATE_DB_INTERVAL
    new_config['General']['mb_ignore_age'] = MB_IGNORE_AGE
    new_config['General']['torrent_removal_interval'] = TORRENT_REMOVAL_INTERVAL

    new_config['SABnzbd'] = {}
    new_config['SABnzbd']['sab_host'] = SAB_HOST
    new_config['SABnzbd']['sab_username'] = SAB_USERNAME
    new_config['SABnzbd']['sab_password'] = SAB_PASSWORD
    new_config['SABnzbd']['sab_apikey'] = SAB_APIKEY
    new_config['SABnzbd']['sab_category'] = SAB_CATEGORY

    new_config['NZBget'] = {}
    new_config['NZBget']['nzbget_username'] = NZBGET_USERNAME
    new_config['NZBget']['nzbget_password'] = NZBGET_PASSWORD
    new_config['NZBget']['nzbget_category'] = NZBGET_CATEGORY
    new_config['NZBget']['nzbget_host'] = NZBGET_HOST
    new_config['NZBget']['nzbget_priority'] = NZBGET_PRIORITY

    new_config['Headphones'] = {}
    new_config['Headphones']['headphones_indexer'] = int(HEADPHONES_INDEXER)

    new_config['Transmission'] = {}
    new_config['Transmission']['transmission_host'] = TRANSMISSION_HOST
    new_config['Transmission']['transmission_username'] = TRANSMISSION_USERNAME
    new_config['Transmission']['transmission_password'] = TRANSMISSION_PASSWORD

    new_config['uTorrent'] = {}
    new_config['uTorrent']['utorrent_host'] = UTORRENT_HOST
    new_config['uTorrent']['utorrent_username'] = UTORRENT_USERNAME
    new_config['uTorrent']['utorrent_password'] = UTORRENT_PASSWORD
    new_config['uTorrent']['utorrent_label'] = UTORRENT_LABEL

    new_config['Newznab'] = {}
    new_config['Newznab']['newznab'] = int(NEWZNAB)
    new_config['Newznab']['newznab_host'] = NEWZNAB_HOST
    new_config['Newznab']['newznab_apikey'] = NEWZNAB_APIKEY
    new_config['Newznab']['newznab_enabled'] = int(NEWZNAB_ENABLED)
    # Need to unpack the extra newznabs for saving in config.ini
    flattened_newznabs = []
    for newznab in EXTRA_NEWZNABS:
        for item in newznab:
            flattened_newznabs.append(item)

    new_config['Newznab']['extra_newznabs'] = flattened_newznabs

    new_config['NZBsorg'] = {}
    new_config['NZBsorg']['nzbsorg'] = int(NZBSORG)
    new_config['NZBsorg']['nzbsorg_uid'] = NZBSORG_UID
    new_config['NZBsorg']['nzbsorg_hash'] = NZBSORG_HASH

    new_config['omgwtfnzbs'] = {}
    new_config['omgwtfnzbs']['omgwtfnzbs'] = int(OMGWTFNZBS)
    new_config['omgwtfnzbs']['omgwtfnzbs_uid'] = OMGWTFNZBS_UID
    new_config['omgwtfnzbs']['omgwtfnzbs_apikey'] = OMGWTFNZBS_APIKEY

    new_config['General']['preferred_words'] = PREFERRED_WORDS
    new_config['General']['ignored_words'] = IGNORED_WORDS
    new_config['General']['required_words'] = REQUIRED_WORDS

    new_config['Growl'] = {}
    new_config['Growl']['growl_enabled'] = int(GROWL_ENABLED)
    new_config['Growl']['growl_host'] = GROWL_HOST
    new_config['Growl']['growl_password'] = GROWL_PASSWORD
    new_config['Growl']['growl_onsnatch'] = int(GROWL_ONSNATCH)

    new_config['Prowl'] = {}
    new_config['Prowl']['prowl_enabled'] = int(PROWL_ENABLED)
    new_config['Prowl']['prowl_keys'] = PROWL_KEYS
    new_config['Prowl']['prowl_onsnatch'] = int(PROWL_ONSNATCH)
    new_config['Prowl']['prowl_priority'] = int(PROWL_PRIORITY)

    new_config['XBMC'] = {}
    new_config['XBMC']['xbmc_enabled'] = int(XBMC_ENABLED)
    new_config['XBMC']['xbmc_host'] = XBMC_HOST
    new_config['XBMC']['xbmc_username'] = XBMC_USERNAME
    new_config['XBMC']['xbmc_password'] = XBMC_PASSWORD
    new_config['XBMC']['xbmc_update'] = int(XBMC_UPDATE)
    new_config['XBMC']['xbmc_notify'] = int(XBMC_NOTIFY)

    new_config['LMS'] = {}
    new_config['LMS']['lms_enabled'] = int(LMS_ENABLED)
    new_config['LMS']['lms_host'] = LMS_HOST

    new_config['Plex'] = {}
    new_config['Plex']['plex_enabled'] = int(PLEX_ENABLED)
    new_config['Plex']['plex_server_host'] = PLEX_SERVER_HOST
    new_config['Plex']['plex_client_host'] = PLEX_CLIENT_HOST
    new_config['Plex']['plex_username'] = PLEX_USERNAME
    new_config['Plex']['plex_password'] = PLEX_PASSWORD
    new_config['Plex']['plex_update'] = int(PLEX_UPDATE)
    new_config['Plex']['plex_notify'] = int(PLEX_NOTIFY)

    new_config['NMA'] = {}
    new_config['NMA']['nma_enabled'] = int(NMA_ENABLED)
    new_config['NMA']['nma_apikey'] = NMA_APIKEY
    new_config['NMA']['nma_priority'] = int(NMA_PRIORITY)
    new_config['NMA']['nma_onsnatch'] = int(NMA_ONSNATCH)

    new_config['Pushalot'] = {}
    new_config['Pushalot']['pushalot_enabled'] = int(PUSHALOT_ENABLED)
    new_config['Pushalot']['pushalot_apikey'] = PUSHALOT_APIKEY
    new_config['Pushalot']['pushalot_onsnatch'] = int(PUSHALOT_ONSNATCH)

    new_config['Pushover'] = {}
    new_config['Pushover']['pushover_enabled'] = int(PUSHOVER_ENABLED)
    new_config['Pushover']['pushover_keys'] = PUSHOVER_KEYS
    new_config['Pushover']['pushover_onsnatch'] = int(PUSHOVER_ONSNATCH)
    new_config['Pushover']['pushover_priority'] = int(PUSHOVER_PRIORITY)
    new_config['Pushover']['pushover_apitoken'] = PUSHOVER_APITOKEN

    new_config['PushBullet'] = {}
    new_config['PushBullet']['pushbullet_enabled'] = int(PUSHBULLET_ENABLED)
    new_config['PushBullet']['pushbullet_apikey'] = PUSHBULLET_APIKEY
    new_config['PushBullet']['pushbullet_deviceid'] = PUSHBULLET_DEVICEID
    new_config['PushBullet']['pushbullet_onsnatch'] = int(PUSHBULLET_ONSNATCH)

    new_config['Twitter'] = {}
    new_config['Twitter']['twitter_enabled'] = int(TWITTER_ENABLED)
    new_config['Twitter']['twitter_onsnatch'] = int(TWITTER_ONSNATCH)
    new_config['Twitter']['twitter_username'] = TWITTER_USERNAME
    new_config['Twitter']['twitter_password'] = TWITTER_PASSWORD
    new_config['Twitter']['twitter_prefix'] = TWITTER_PREFIX

    new_config['OSX_Notify'] = {}
    new_config['OSX_Notify']['osx_notify_enabled'] = int(OSX_NOTIFY_ENABLED)
    new_config['OSX_Notify']['osx_notify_onsnatch'] = int(OSX_NOTIFY_ONSNATCH)
    new_config['OSX_Notify']['osx_notify_app'] = OSX_NOTIFY_APP

    new_config['Boxcar'] = {}
    new_config['Boxcar']['boxcar_enabled'] = int(BOXCAR_ENABLED)
    new_config['Boxcar']['boxcar_onsnatch'] = int(BOXCAR_ONSNATCH)
    new_config['Boxcar']['boxcar_token'] = BOXCAR_TOKEN

    new_config['Subsonic'] = {}
    new_config['Subsonic']['subsonic_enabled'] = int(SUBSONIC_ENABLED)
    new_config['Subsonic']['subsonic_host'] = SUBSONIC_HOST
    new_config['Subsonic']['subsonic_username'] = SUBSONIC_USERNAME
    new_config['Subsonic']['subsonic_password'] = SUBSONIC_PASSWORD

    new_config['Songkick'] = {}
    new_config['Songkick']['songkick_enabled'] = int(SONGKICK_ENABLED)
    new_config['Songkick']['songkick_apikey'] = SONGKICK_APIKEY
    new_config['Songkick']['songkick_location'] = SONGKICK_LOCATION
    new_config['Songkick']['songkick_filter_enabled'] = int(SONGKICK_FILTER_ENABLED)

    new_config['Synoindex'] = {}
    new_config['Synoindex']['synoindex_enabled'] = int(SYNOINDEX_ENABLED)

    new_config['General']['lastfm_username'] = LASTFM_USERNAME
    new_config['General']['interface'] = INTERFACE
    new_config['General']['folder_permissions'] = FOLDER_PERMISSIONS
    new_config['General']['file_permissions'] = FILE_PERMISSIONS

    new_config['General']['music_encoder'] = int(MUSIC_ENCODER)
    new_config['General']['encoder'] = ENCODER
    new_config['General']['xldprofile'] = XLDPROFILE
    new_config['General']['bitrate'] = int(BITRATE)
    new_config['General']['samplingfrequency'] = int(SAMPLINGFREQUENCY)
    new_config['General']['encoder_path'] = ENCODER_PATH
    new_config['General']['advancedencoder'] = ADVANCEDENCODER
    new_config['General']['encoderoutputformat'] = ENCODEROUTPUTFORMAT
    new_config['General']['encoderquality'] = ENCODERQUALITY
    new_config['General']['encodervbrcbr'] = ENCODERVBRCBR
    new_config['General']['encoderlossless'] = int(ENCODERLOSSLESS)
    new_config['General']['encoder_multicore'] = int(ENCODER_MULTICORE)
    new_config['General']['encoder_multicore_count'] = int(ENCODER_MULTICORE_COUNT)
    new_config['General']['delete_lossless_files'] = int(DELETE_LOSSLESS_FILES)

    new_config['General']['mirror'] = MIRROR
    new_config['General']['customhost'] = CUSTOMHOST
    new_config['General']['customport'] = CUSTOMPORT
    new_config['General']['customsleep'] = CUSTOMSLEEP
    new_config['General']['hpuser'] = HPUSER
    new_config['General']['hppass'] = HPPASS

    new_config['Advanced'] = {}
    new_config['Advanced']['album_completion_pct'] = ALBUM_COMPLETION_PCT
    new_config['Advanced']['cache_sizemb'] = CACHE_SIZEMB
    new_config['Advanced']['journal_mode'] = JOURNAL_MODE
    new_config['Advanced']['verify_ssl_cert'] = int(VERIFY_SSL_CERT)

    # Write it to file
    logger.info("Writing configuration to file")

    try:
        new_config.write()
    except IOError as e:
        logger.error("Error writing configuration file: %s", e)

def start():

    global __INITIALIZED__, started

    if __INITIALIZED__:

        # Start our scheduled background tasks
        from headphones import updater, searcher, librarysync, postprocessor, torrentfinished

        SCHED.add_interval_job(updater.dbUpdate, hours=UPDATE_DB_INTERVAL)
        SCHED.add_interval_job(searcher.searchforalbum, minutes=SEARCH_INTERVAL)
        SCHED.add_interval_job(librarysync.libraryScan, hours=LIBRARYSCAN_INTERVAL, kwargs={'cron':True})

        if CHECK_GITHUB:
            SCHED.add_interval_job(versioncheck.checkGithub, minutes=CHECK_GITHUB_INTERVAL)

        if DOWNLOAD_SCAN_INTERVAL > 0:
            SCHED.add_interval_job(postprocessor.checkFolder, minutes=DOWNLOAD_SCAN_INTERVAL)

        # Remove Torrent + data if Post Processed and finished Seeding
        if TORRENT_REMOVAL_INTERVAL > 0:
            SCHED.add_interval_job(torrentfinished.checkTorrentFinished, minutes=TORRENT_REMOVAL_INTERVAL)

        SCHED.start()

        started = True

def sig_handler(signum=None, frame=None):
    if signum is not None:
        logger.info("Signal %i caught, saving and exiting...", signum)
        shutdown()

def dbcheck():

    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT, IncludeExtras INTEGER, LatestAlbum TEXT, ReleaseDate TEXT, AlbumID TEXT, HaveTracks INTEGER, TotalTracks INTEGER, LastUpdated TEXT, ArtworkURL TEXT, ThumbURL TEXT, Extras TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT, Type TEXT, ArtworkURL TEXT, ThumbURL TEXT, ReleaseID TEXT, ReleaseCountry TEXT, ReleaseFormat TEXT, SearchTerm TEXT)')   # ReleaseFormat here means CD,Digital,Vinyl, etc. If using the default Headphones hybrid release, ReleaseID will equal AlbumID (AlbumID is releasegroup id)
    c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT, TrackNumber INTEGER, Location TEXT, BitRate INTEGER, CleanName TEXT, Format TEXT, ReleaseID TEXT)')    # Format here means mp3, flac, etc.
    c.execute('CREATE TABLE IF NOT EXISTS allalbums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, AlbumID TEXT, Type TEXT, ReleaseID TEXT, ReleaseCountry TEXT, ReleaseFormat TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS alltracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT, TrackNumber INTEGER, Location TEXT, BitRate INTEGER, CleanName TEXT, Format TEXT, ReleaseID TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS snatched (AlbumID TEXT, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT, FolderName TEXT, Kind TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS have (ArtistName TEXT, AlbumTitle TEXT, TrackNumber TEXT, TrackTitle TEXT, TrackLength TEXT, BitRate TEXT, Genre TEXT, Date TEXT, TrackID TEXT, Location TEXT, CleanName TEXT, Format TEXT, Matched TEXT)') # Matched is a temporary value used to see if there was a match found in alltracks
    c.execute('CREATE TABLE IF NOT EXISTS lastfmcloud (ArtistName TEXT, ArtistID TEXT, Count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS descriptions (ArtistID TEXT, ReleaseGroupID TEXT, ReleaseID TEXT, Summary TEXT, Content TEXT, LastUpdated TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (ArtistID TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS newartists (ArtistName TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS releases (ReleaseID TEXT, ReleaseGroupID TEXT, UNIQUE(ReleaseID, ReleaseGroupID))')
    c.execute('CREATE INDEX IF NOT EXISTS tracks_albumid ON tracks(AlbumID ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS album_artistid_reldate ON albums(ArtistID ASC, ReleaseDate DESC)')
    #Below creates indices to speed up Active Artist updating
    c.execute('CREATE INDEX IF NOT EXISTS alltracks_relid ON alltracks(ReleaseID ASC, TrackID ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS allalbums_relid ON allalbums(ReleaseID ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS have_location ON have(Location ASC)')
    #Below creates indices to speed up library scanning & matching
    c.execute('CREATE INDEX IF NOT EXISTS have_Metadata ON have(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS have_CleanName ON have(CleanName ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS tracks_Metadata ON tracks(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS tracks_CleanName ON tracks(CleanName ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS alltracks_Metadata ON alltracks(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS alltracks_CleanName ON alltracks(CleanName ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS tracks_Location ON tracks(Location ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS alltracks_Location ON alltracks(Location ASC)')

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

    try:
        c.execute('SELECT LastUpdated from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN LastUpdated TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ArtworkURL from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN ArtworkURL TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ArtworkURL from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ArtworkURL TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ThumbURL from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN ThumbURL TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ThumbURL from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ThumbURL TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ArtistID from descriptions')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE descriptions ADD COLUMN ArtistID TEXT DEFAULT NULL')

    try:
        c.execute('SELECT LastUpdated from descriptions')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE descriptions ADD COLUMN LastUpdated TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseID from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ReleaseID TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseFormat from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ReleaseFormat TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseCountry from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ReleaseCountry TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseID from tracks')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE tracks ADD COLUMN ReleaseID TEXT DEFAULT NULL')

    try:
        c.execute('SELECT Matched from have')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE have ADD COLUMN Matched TEXT DEFAULT NULL')

    try:
        c.execute('SELECT Extras from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN Extras TEXT DEFAULT NULL')
        # Need to update some stuff when people are upgrading and have 'include extras' set globally/for an artist
        if INCLUDE_EXTRAS:
            EXTRAS = "1,2,3,4,5,6,7,8"
        logger.info("Copying over current artist IncludeExtras information")
        artists = c.execute('SELECT ArtistID, IncludeExtras from artists').fetchall()
        for artist in artists:
            if artist[1]:
                c.execute('UPDATE artists SET Extras=? WHERE ArtistID=?', ("1,2,3,4,5,6,7,8", artist[0]))

    try:
        c.execute('SELECT Kind from snatched')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE snatched ADD COLUMN Kind TEXT DEFAULT NULL')

    try:
        c.execute('SELECT SearchTerm from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN SearchTerm TEXT DEFAULT NULL')


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
            logger.warn('Headphones failed to update: %s. Restarting.', e)

    if CREATEPID :
        logger.info ('Removing pidfile %s', PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logger.info('Headphones is restarting...')
        popen_list = [sys.executable, FULL_PATH]
        popen_list += ARGS
        if '--nolaunch' not in popen_list:
            popen_list += ['--nolaunch']
        logger.info('Restarting Headphones with %s', popen_list)
        subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)
