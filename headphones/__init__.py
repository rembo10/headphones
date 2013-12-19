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

from __future__ import with_statement

import os, sys, subprocess

import threading
import webbrowser
import sqlite3
import itertools

from lib.apscheduler.scheduler import Scheduler
from lib.configobj import ConfigObj

import cherrypy

from headphones import versioncheck, logger, version
from headphones.common import *

FULL_PATH = None
PROG_DIR = None

ARGS = None
SIGNAL = None

SYS_PLATFORM = None
SYS_ENCODING = None

VERBOSE = 1
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
GIT_BRANCH =None
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
ADD_ARTISTS = False
CORRECT_METADATA = False
MOVE_FILES = False
RENAME_FILES = False
CLEANUP_FILES = False
ADD_ALBUM_ART = False
ALBUM_ART_FORMAT = None
EMBED_ALBUM_ART = False
EMBED_LYRICS = False
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
KEEP_TORRENT_FILES = False

SEARCH_INTERVAL = 360
LIBRARYSCAN = False
LIBRARYSCAN_INTERVAL = 300
DOWNLOAD_SCAN_INTERVAL = 5

SAB_HOST = None
SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None

NZBGET_USERNAME = None
NZBGET_PASSWORD = None
NZBGET_CATEGORY = None
NZBGET_HOST = None

HEADPHONES_INDEXER = False

TRANSMISSION_HOST = None
TRANSMISSION_USERNAME = None
TRANSMISSION_PASSWORD = None

UTORRENT_HOST = None
UTORRENT_USERNAME = None
UTORRENT_PASSWORD = None

NEWZNAB = False
NEWZNAB_HOST = None
NEWZNAB_APIKEY = None
NEWZNAB_ENABLED = False
EXTRA_NEWZNABS = []

NZBSORG = False
NZBSORG_UID = None
NZBSORG_HASH = None

NZBSRUS = False
NZBSRUS_UID = None
NZBSRUS_APIKEY = None

OMGWTFNZBS = False
OMGWTFNZBS_UID = None
OMGWTFNZBS_APIKEY = None

PREFERRED_WORDS = None
IGNORED_WORDS = None
REQUIRED_WORDS = None

LASTFM_USERNAME = None

LOSSY_MEDIA_FORMATS = ["mp3", "aac", "ogg", "ape", "m4a"]
LOSSLESS_MEDIA_FORMATS = ["flac"]
MEDIA_FORMATS = LOSSY_MEDIA_FORMATS + LOSSLESS_MEDIA_FORMATS

ALBUM_COMPLETION_PCT = None    # This is used in importer.py to determine how complete an album needs to be - to be considered "downloaded". Percentage from 0-100

TORRENTBLACKHOLE_DIR = None
NUMBEROFSEEDERS = 10
ISOHUNT = None
KAT = None
MININOVA = None
PIRATEBAY = None
PIRATEBAY_PROXY_URL = None
WAFFLES = None
WAFFLES_UID = None
WAFFLES_PASSKEY = None
RUTRACKER = None
RUTRACKER_USER = None
RUTRACKER_PASSWORD = None
WHATCD = None
WHATCD_USERNAME = None
WHATCD_PASSWORD = None
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
DELETE_LOSSLESS_FILES = False
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
NMA_ENABLED = False
NMA_APIKEY = None
NMA_PRIORITY = None
NMA_ONSNATCH = None
SYNOINDEX_ENABLED = False
PUSHOVER_ENABLED = True
PUSHOVER_PRIORITY = 1
PUSHOVER_KEYS = None
PUSHOVER_ONSNATCH = True
MIRRORLIST = ["musicbrainz.org","headphones","custom"]
MIRROR = None
CUSTOMHOST = None
CUSTOMPORT = None
CUSTOMSLEEP = None
HPUSER = None
HPPASS = None

CACHE_SIZEMB = 32
JOURNAL_MODE = None

UMASK = None

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

        global __INITIALIZED__, FULL_PATH, PROG_DIR, VERBOSE, DAEMON, SYS_PLATFORM, DATA_DIR, CONFIG_FILE, CFG, CONFIG_VERSION, LOG_DIR, CACHE_DIR, \
                HTTP_PORT, HTTP_HOST, HTTP_USERNAME, HTTP_PASSWORD, HTTP_ROOT, HTTP_PROXY, LAUNCH_BROWSER, API_ENABLED, API_KEY, GIT_PATH, GIT_USER, GIT_BRANCH, \
                CURRENT_VERSION, LATEST_VERSION, CHECK_GITHUB, CHECK_GITHUB_ON_STARTUP, CHECK_GITHUB_INTERVAL, MUSIC_DIR, DESTINATION_DIR, \
                LOSSLESS_DESTINATION_DIR, PREFERRED_QUALITY, PREFERRED_BITRATE, DETECT_BITRATE, ADD_ARTISTS, CORRECT_METADATA, MOVE_FILES, \
                RENAME_FILES, FOLDER_FORMAT, FILE_FORMAT, FILE_UNDERSCORES, CLEANUP_FILES, INCLUDE_EXTRAS, EXTRAS, AUTOWANT_UPCOMING, AUTOWANT_ALL, KEEP_TORRENT_FILES, \
                ADD_ALBUM_ART, ALBUM_ART_FORMAT, EMBED_ALBUM_ART, EMBED_LYRICS, DOWNLOAD_DIR, BLACKHOLE, BLACKHOLE_DIR, USENET_RETENTION, SEARCH_INTERVAL, \
                TORRENTBLACKHOLE_DIR, NUMBEROFSEEDERS, ISOHUNT, KAT, PIRATEBAY, PIRATEBAY_PROXY_URL, MININOVA, WAFFLES, WAFFLES_UID, WAFFLES_PASSKEY, \
                RUTRACKER, RUTRACKER_USER, RUTRACKER_PASSWORD, WHATCD, WHATCD_USERNAME, WHATCD_PASSWORD, DOWNLOAD_TORRENT_DIR, \
                LIBRARYSCAN, LIBRARYSCAN_INTERVAL, DOWNLOAD_SCAN_INTERVAL, SAB_HOST, SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, \
                NZBGET_USERNAME, NZBGET_PASSWORD, NZBGET_CATEGORY, NZBGET_HOST, HEADPHONES_INDEXER, NZBMATRIX, TRANSMISSION_HOST, TRANSMISSION_USERNAME, TRANSMISSION_PASSWORD, \
                UTORRENT_HOST, UTORRENT_USERNAME, UTORRENT_PASSWORD, NEWZNAB, NEWZNAB_HOST, NEWZNAB_APIKEY, NEWZNAB_ENABLED, EXTRA_NEWZNABS, \
                NZBSORG, NZBSORG_UID, NZBSORG_HASH, NZBSRUS, NZBSRUS_UID, NZBSRUS_APIKEY, OMGWTFNZBS, OMGWTFNZBS_UID, OMGWTFNZBS_APIKEY, \
		NZB_DOWNLOADER, TORRENT_DOWNLOADER, PREFERRED_WORDS, REQUIRED_WORDS, IGNORED_WORDS, LASTFM_USERNAME, \
                INTERFACE, FOLDER_PERMISSIONS, FILE_PERMISSIONS, ENCODERFOLDER, ENCODER_PATH, ENCODER, XLDPROFILE, BITRATE, SAMPLINGFREQUENCY, \
                MUSIC_ENCODER, ADVANCEDENCODER, ENCODEROUTPUTFORMAT, ENCODERQUALITY, ENCODERVBRCBR, ENCODERLOSSLESS, DELETE_LOSSLESS_FILES, \
                PROWL_ENABLED, PROWL_PRIORITY, PROWL_KEYS, PROWL_ONSNATCH, PUSHOVER_ENABLED, PUSHOVER_PRIORITY, PUSHOVER_KEYS, PUSHOVER_ONSNATCH, MIRRORLIST, \
                MIRROR, CUSTOMHOST, CUSTOMPORT, CUSTOMSLEEP, HPUSER, HPPASS, XBMC_ENABLED, XBMC_HOST, XBMC_USERNAME, XBMC_PASSWORD, XBMC_UPDATE, \
                XBMC_NOTIFY, NMA_ENABLED, NMA_APIKEY, NMA_PRIORITY, NMA_ONSNATCH, SYNOINDEX_ENABLED, ALBUM_COMPLETION_PCT, PREFERRED_BITRATE_HIGH_BUFFER, \
                PREFERRED_BITRATE_LOW_BUFFER, PREFERRED_BITRATE_ALLOW_LOSSLESS, CACHE_SIZEMB, JOURNAL_MODE, UMASK, ENABLE_HTTPS, HTTPS_CERT, HTTPS_KEY

        if __INITIALIZED__:
            return False

        # Make sure all the config sections exist
        CheckSection('General')
        CheckSection('SABnzbd')
        CheckSection('NZBget')
        CheckSection('Transmission')
        CheckSection('uTorrent')
        CheckSection('Headphones')
        CheckSection('Newznab')
        CheckSection('NZBsorg')
        CheckSection('NZBsRus')
        CheckSection('omgwtfnzbs')
        CheckSection('Waffles')
        CheckSection('Rutracker')
        CheckSection('What.cd')
        CheckSection('Prowl')
        CheckSection('Pushover')
        CheckSection('XBMC')
        CheckSection('NMA')
        CheckSection('Synoindex')
        CheckSection('Advanced')

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
        ADD_ARTISTS = bool(check_setting_int(CFG, 'General', 'auto_add_artists', 1))
        CORRECT_METADATA = bool(check_setting_int(CFG, 'General', 'correct_metadata', 0))
        MOVE_FILES = bool(check_setting_int(CFG, 'General', 'move_files', 0))
        RENAME_FILES = bool(check_setting_int(CFG, 'General', 'rename_files', 0))
        FOLDER_FORMAT = check_setting_str(CFG, 'General', 'folder_format', 'Artist/Album [Year]')
        FILE_FORMAT = check_setting_str(CFG, 'General', 'file_format', 'Track Artist - Album [Year] - Title')
        FILE_UNDERSCORES = bool(check_setting_int(CFG, 'General', 'file_underscores', 0))
        CLEANUP_FILES = bool(check_setting_int(CFG, 'General', 'cleanup_files', 0))
        ADD_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'add_album_art', 0))
        ALBUM_ART_FORMAT = check_setting_str(CFG, 'General', 'album_art_format', 'folder')
        EMBED_ALBUM_ART = bool(check_setting_int(CFG, 'General', 'embed_album_art', 0))
        EMBED_LYRICS = bool(check_setting_int(CFG, 'General', 'embed_lyrics', 0))
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
        KEEP_TORRENT_FILES = bool(check_setting_int(CFG, 'General', 'keep_torrent_files', 0))

        SEARCH_INTERVAL = check_setting_int(CFG, 'General', 'search_interval', 1440)
        LIBRARYSCAN = bool(check_setting_int(CFG, 'General', 'libraryscan', 1))
        LIBRARYSCAN_INTERVAL = check_setting_int(CFG, 'General', 'libraryscan_interval', 300)
        DOWNLOAD_SCAN_INTERVAL = check_setting_int(CFG, 'General', 'download_scan_interval', 5)

        TORRENTBLACKHOLE_DIR = check_setting_str(CFG, 'General', 'torrentblackhole_dir', '')
        NUMBEROFSEEDERS = check_setting_str(CFG, 'General', 'numberofseeders', '10')
        ISOHUNT = bool(check_setting_int(CFG, 'General', 'isohunt', 0))
        KAT = bool(check_setting_int(CFG, 'General', 'kat', 0))
        PIRATEBAY = bool(check_setting_int(CFG, 'General', 'piratebay', 0))
        PIRATEBAY_PROXY_URL = check_setting_str(CFG, 'General', 'piratebay_proxy_url', '')
        MININOVA = bool(check_setting_int(CFG, 'General', 'mininova', 0))
        DOWNLOAD_TORRENT_DIR = check_setting_str(CFG, 'General', 'download_torrent_dir', '')

        WAFFLES = bool(check_setting_int(CFG, 'Waffles', 'waffles', 0))
        WAFFLES_UID = check_setting_str(CFG, 'Waffles', 'waffles_uid', '')
        WAFFLES_PASSKEY = check_setting_str(CFG, 'Waffles', 'waffles_passkey', '')

        RUTRACKER = bool(check_setting_int(CFG, 'Rutracker', 'rutracker', 0))
        RUTRACKER_USER = check_setting_str(CFG, 'Rutracker', 'rutracker_user', '')
        RUTRACKER_PASSWORD = check_setting_str(CFG, 'Rutracker', 'rutracker_password', '')

        WHATCD = bool(check_setting_int(CFG, 'What.cd', 'whatcd', 0))
        WHATCD_USERNAME = check_setting_str(CFG, 'What.cd', 'whatcd_username', '')
        WHATCD_PASSWORD = check_setting_str(CFG, 'What.cd', 'whatcd_password', '')

        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')
        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', '')

        NZBGET_USERNAME = check_setting_str(CFG, 'NZBget', 'nzbget_username', 'nzbget')
        NZBGET_PASSWORD = check_setting_str(CFG, 'NZBget', 'nzbget_password', '')
        NZBGET_CATEGORY = check_setting_str(CFG, 'NZBget', 'nzbget_category', '')
        NZBGET_HOST = check_setting_str(CFG, 'NZBget', 'nzbget_host', '')

        HEADPHONES_INDEXER = bool(check_setting_int(CFG, 'Headphones', 'headphones_indexer', 0))
        
        TRANSMISSION_HOST = check_setting_str(CFG, 'Transmission', 'transmission_host', '')
        TRANSMISSION_USERNAME = check_setting_str(CFG, 'Transmission', 'transmission_username', '')
        TRANSMISSION_PASSWORD = check_setting_str(CFG, 'Transmission', 'transmission_password', '')
        
        UTORRENT_HOST = check_setting_str(CFG, 'uTorrent', 'utorrent_host', '')
        UTORRENT_USERNAME = check_setting_str(CFG, 'uTorrent', 'utorrent_username', '')
        UTORRENT_PASSWORD = check_setting_str(CFG, 'uTorrent', 'utorrent_password', '')

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

        NZBSRUS = bool(check_setting_int(CFG, 'NZBsRus', 'nzbsrus', 0))
        NZBSRUS_UID = check_setting_str(CFG, 'NZBsRus', 'nzbsrus_uid', '')
        NZBSRUS_APIKEY = check_setting_str(CFG, 'NZBsRus', 'nzbsrus_apikey', '')

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
        DELETE_LOSSLESS_FILES = bool(check_setting_int(CFG, 'General', 'delete_lossless_files', 1))

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

        NMA_ENABLED = bool(check_setting_int(CFG, 'NMA', 'nma_enabled', 0))
        NMA_APIKEY = check_setting_str(CFG, 'NMA', 'nma_apikey', '')
        NMA_PRIORITY = check_setting_int(CFG, 'NMA', 'nma_priority', 0)
        NMA_ONSNATCH = bool(check_setting_int(CFG, 'NMA', 'nma_onsnatch', 0))

        SYNOINDEX_ENABLED = bool(check_setting_int(CFG, 'Synoindex', 'synoindex_enabled', 0))

        PUSHOVER_ENABLED = bool(check_setting_int(CFG, 'Pushover', 'pushover_enabled', 0))
        PUSHOVER_KEYS = check_setting_str(CFG, 'Pushover', 'pushover_keys', '')
        PUSHOVER_ONSNATCH = bool(check_setting_int(CFG, 'Pushover', 'pushover_onsnatch', 0))
        PUSHOVER_PRIORITY = check_setting_int(CFG, 'Pushover', 'pushover_priority', 0)

        MIRROR = check_setting_str(CFG, 'General', 'mirror', 'musicbrainz.org')
        CUSTOMHOST = check_setting_str(CFG, 'General', 'customhost', 'localhost')
        CUSTOMPORT = check_setting_int(CFG, 'General', 'customport', 5000)
        CUSTOMSLEEP = check_setting_int(CFG, 'General', 'customsleep', 1)
        HPUSER = check_setting_str(CFG, 'General', 'hpuser', '')
        HPPASS = check_setting_str(CFG, 'General', 'hppass', '')

        CACHE_SIZEMB = check_setting_int(CFG,'Advanced','cache_sizemb',32)
        JOURNAL_MODE = check_setting_int(CFG,'Advanced', 'journal_mode', 'wal')

        ALBUM_COMPLETION_PCT = check_setting_int(CFG, 'Advanced', 'album_completion_pct', 80)

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
                    print 'Unable to create the log directory. Logging to screen only.'

        # Start the logger, silence console logging if we need to
        logger.headphones_log.initLogger(verbose=VERBOSE)

        if not CACHE_DIR:
            # Put the cache dir in the data dir for now
            CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CACHE_DIR):
            try:
                os.makedirs(CACHE_DIR)
            except OSError:
                logger.error('Could not create cache dir. Check permissions of datadir: ' + DATA_DIR)

        # Sanity check for search interval. Set it to at least 6 hours
        if SEARCH_INTERVAL < 360:
            logger.info("Search interval too low. Resetting to 6 hour minimum")
            SEARCH_INTERVAL = 360

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
        if CHECK_GITHUB_ON_STARTUP:
            try:
                LATEST_VERSION = versioncheck.checkGithub()
            except:
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
        raise RuntimeError("1st fork failed: %s [%d]" % (e.strerror, e.errno))

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
        raise RuntimeError("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = str(os.getpid())
    logger.info('Daemonized to PID: %s' % pid)

    if CREATEPID:
        logger.info("Writing PID " + pid + " to " + str(PIDFILE))
        file(PIDFILE, 'w').write("%s\n" % pid)

def launch_browser(host, port, root):

    if host == '0.0.0.0':
        host = 'localhost'
        
    if ENABLE_HTTPS:
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
    except Exception, e:
        logger.error('Could not launch browser: %s' % e)

def config_write():

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
    new_config['General']['auto_add_artists'] = int(ADD_ARTISTS)
    new_config['General']['correct_metadata'] = int(CORRECT_METADATA)
    new_config['General']['move_files'] = int(MOVE_FILES)
    new_config['General']['rename_files'] = int(RENAME_FILES)
    new_config['General']['folder_format'] = FOLDER_FORMAT
    new_config['General']['file_format'] = FILE_FORMAT
    new_config['General']['file_underscores'] = int(FILE_UNDERSCORES)
    new_config['General']['cleanup_files'] = int(CLEANUP_FILES)
    new_config['General']['add_album_art'] = int(ADD_ALBUM_ART)
    new_config['General']['album_art_format'] = ALBUM_ART_FORMAT
    new_config['General']['embed_album_art'] = int(EMBED_ALBUM_ART)
    new_config['General']['embed_lyrics'] = int(EMBED_LYRICS)
    new_config['General']['nzb_downloader'] = NZB_DOWNLOADER
    new_config['General']['torrent_downloader'] = TORRENT_DOWNLOADER
    new_config['General']['download_dir'] = DOWNLOAD_DIR
    new_config['General']['blackhole_dir'] = BLACKHOLE_DIR
    new_config['General']['usenet_retention'] = USENET_RETENTION
    new_config['General']['include_extras'] = int(INCLUDE_EXTRAS)
    new_config['General']['extras'] = EXTRAS
    new_config['General']['autowant_upcoming'] = int(AUTOWANT_UPCOMING)
    new_config['General']['autowant_all'] = int(AUTOWANT_ALL)
    new_config['General']['keep_torrent_files'] = int(KEEP_TORRENT_FILES)

    new_config['General']['numberofseeders'] = NUMBEROFSEEDERS
    new_config['General']['torrentblackhole_dir'] = TORRENTBLACKHOLE_DIR
    new_config['General']['isohunt'] = int(ISOHUNT)
    new_config['General']['kat'] = int(KAT)
    new_config['General']['mininova'] = int(MININOVA)
    new_config['General']['piratebay'] = int(PIRATEBAY)
    new_config['General']['piratebay_proxy_url'] = PIRATEBAY_PROXY_URL
    new_config['General']['download_torrent_dir'] = DOWNLOAD_TORRENT_DIR

    new_config['Waffles'] = {}
    new_config['Waffles']['waffles'] = int(WAFFLES)
    new_config['Waffles']['waffles_uid'] = WAFFLES_UID
    new_config['Waffles']['waffles_passkey'] = WAFFLES_PASSKEY

    new_config['Rutracker'] = {}
    new_config['Rutracker']['rutracker'] = int(RUTRACKER)
    new_config['Rutracker']['rutracker_user'] = RUTRACKER_USER
    new_config['Rutracker']['rutracker_password'] = RUTRACKER_PASSWORD

    new_config['What.cd'] = {}
    new_config['What.cd']['whatcd'] = int(WHATCD)
    new_config['What.cd']['whatcd_username'] = WHATCD_USERNAME
    new_config['What.cd']['whatcd_password'] = WHATCD_PASSWORD

    new_config['General']['search_interval'] = SEARCH_INTERVAL
    new_config['General']['libraryscan'] = int(LIBRARYSCAN)
    new_config['General']['libraryscan_interval'] = LIBRARYSCAN_INTERVAL
    new_config['General']['download_scan_interval'] = DOWNLOAD_SCAN_INTERVAL

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

    new_config['NZBsRus'] = {}
    new_config['NZBsRus']['nzbsrus'] = int(NZBSRUS)
    new_config['NZBsRus']['nzbsrus_uid'] = NZBSRUS_UID
    new_config['NZBsRus']['nzbsrus_apikey'] = NZBSRUS_APIKEY

    new_config['omgwtfnzbs'] = {}
    new_config['omgwtfnzbs']['omgwtfnzbs'] = int(OMGWTFNZBS)
    new_config['omgwtfnzbs']['omgwtfnzbs_uid'] = OMGWTFNZBS_UID
    new_config['omgwtfnzbs']['omgwtfnzbs_apikey'] = OMGWTFNZBS_APIKEY

    new_config['General']['preferred_words'] = PREFERRED_WORDS
    new_config['General']['ignored_words'] = IGNORED_WORDS
    new_config['General']['required_words'] = REQUIRED_WORDS

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

    new_config['NMA'] = {}
    new_config['NMA']['nma_enabled'] = int(NMA_ENABLED)
    new_config['NMA']['nma_apikey'] = NMA_APIKEY
    new_config['NMA']['nma_priority'] = NMA_PRIORITY
    new_config['NMA']['nma_onsnatch'] = int(PROWL_ONSNATCH)

    new_config['Pushover'] = {}
    new_config['Pushover']['pushover_enabled'] = int(PUSHOVER_ENABLED)
    new_config['Pushover']['pushover_keys'] = PUSHOVER_KEYS
    new_config['Pushover']['pushover_onsnatch'] = int(PUSHOVER_ONSNATCH)
    new_config['Pushover']['pushover_priority'] = int(PUSHOVER_PRIORITY)

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

    new_config.write()


def start():

    global __INITIALIZED__, started

    if __INITIALIZED__:

        # Start our scheduled background tasks
        from headphones import updater, searcher, librarysync, postprocessor

        SCHED.add_interval_job(updater.dbUpdate, hours=24)
        SCHED.add_interval_job(searcher.searchforalbum, minutes=SEARCH_INTERVAL)
        SCHED.add_interval_job(librarysync.libraryScan, minutes=LIBRARYSCAN_INTERVAL, kwargs={'cron':True})

        if CHECK_GITHUB:
            SCHED.add_interval_job(versioncheck.checkGithub, minutes=CHECK_GITHUB_INTERVAL)

        SCHED.add_interval_job(postprocessor.checkFolder, minutes=DOWNLOAD_SCAN_INTERVAL)

        SCHED.start()

        started = True

def sig_handler(signum=None, frame=None):
    if type(signum) != type(None):
        logger.info("Signal %i caught, saving and exiting..." % int(signum))
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
            logger.warn('Headphones failed to update: %s. Restarting.' % e)

    if CREATEPID :
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
