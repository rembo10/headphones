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

# NZBGet support added by CurlyMo <curlymoo1@gmail.com> as a part of
# XBian - XBMC on the Raspberry Pi

import sys
import subprocess
import threading
import webbrowser
import sqlite3
import datetime

import os
import cherrypy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from headphones import versioncheck, logger
import headphones.config


# (append new extras to the end)
POSSIBLE_EXTRAS = [
    "single",
    "ep",
    "compilation",
    "soundtrack",
    "live",
    "remix",
    "spokenword",
    "audiobook",
    "other",
    "dj-mix",
    "mixtape/street",
    "broadcast",
    "interview",
    "demo"
]

PROG_DIR = None
FULL_PATH = None

ARGS = None
SIGNAL = None

SYS_PLATFORM = None
SYS_ENCODING = None

QUIET = False
VERBOSE = False
DAEMON = False
CREATEPID = False
PIDFILE = None

SCHED = BackgroundScheduler()
SCHED_LOCK = threading.Lock()

INIT_LOCK = threading.Lock()
_INITIALIZED = False
started = False

DATA_DIR = None

CONFIG = None

DB_FILE = None

LOG_LIST = []

INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

LOSSY_MEDIA_FORMATS = ["mp3", "aac", "ogg", "ape", "m4a", "asf", "wma"]
LOSSLESS_MEDIA_FORMATS = ["flac"]
MEDIA_FORMATS = LOSSY_MEDIA_FORMATS + LOSSLESS_MEDIA_FORMATS

MIRRORLIST = ["musicbrainz.org", "headphones", "custom"]

UMASK = None


def initialize(config_file):
    with INIT_LOCK:

        global CONFIG
        global _INITIALIZED
        global CURRENT_VERSION
        global LATEST_VERSION
        global UMASK

        CONFIG = headphones.config.Config(config_file)

        assert CONFIG is not None

        if _INITIALIZED:
            return False

        if CONFIG.HTTP_PORT < 21 or CONFIG.HTTP_PORT > 65535:
            headphones.logger.warn(
                'HTTP_PORT out of bounds: 21 < %s < 65535', CONFIG.HTTP_PORT)
            CONFIG.HTTP_PORT = 8181

        if CONFIG.HTTPS_CERT == '':
            CONFIG.HTTPS_CERT = os.path.join(DATA_DIR, 'server.crt')
        if CONFIG.HTTPS_KEY == '':
            CONFIG.HTTPS_KEY = os.path.join(DATA_DIR, 'server.key')

        if not CONFIG.LOG_DIR:
            CONFIG.LOG_DIR = os.path.join(DATA_DIR, 'logs')

        if not os.path.exists(CONFIG.LOG_DIR):
            try:
                os.makedirs(CONFIG.LOG_DIR)
            except OSError:
                CONFIG.LOG_DIR = None

                if not QUIET:
                    sys.stderr.write("Unable to create the log directory. " \
                                     "Logging to screen only.\n")

        # Start the logger, disable console if needed
        logger.initLogger(console=not QUIET, log_dir=CONFIG.LOG_DIR,
                          verbose=VERBOSE)

        if not CONFIG.CACHE_DIR:
            # Put the cache dir in the data dir for now
            CONFIG.CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CONFIG.CACHE_DIR):
            try:
                os.makedirs(CONFIG.CACHE_DIR)
            except OSError as e:
                logger.error("Could not create cache dir '%s': %s", DATA_DIR, e)

        # Sanity check for search interval. Set it to at least 6 hours
        if CONFIG.SEARCH_INTERVAL and CONFIG.SEARCH_INTERVAL < 360:
            logger.info("Search interval too low. Resetting to 6 hour minimum.")
            CONFIG.SEARCH_INTERVAL = 360

        # Initialize the database
        logger.info('Checking to see if the database has all tables....')
        try:
            dbcheck()
        except Exception as e:
            logger.error("Can't connect to the database: %s", e)

        # Get the currently installed version. Returns None, 'win32' or the git
        # hash.
        CURRENT_VERSION, CONFIG.GIT_BRANCH = versioncheck.getVersion()

        # Write current version to a file, so we know which version did work.
        # This allowes one to restore to that version. The idea is that if we
        # arrive here, most parts of Headphones seem to work.
        if CURRENT_VERSION:
            version_lock_file = os.path.join(DATA_DIR, "version.lock")

            try:
                with open(version_lock_file, "w") as fp:
                    fp.write(CURRENT_VERSION)
            except IOError as e:
                logger.error("Unable to write current version to file '%s': %s",
                             version_lock_file, e)

        # Check for new versions
        if CONFIG.CHECK_GITHUB and CONFIG.CHECK_GITHUB_ON_STARTUP:
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

        _INITIALIZED = True
        return True


def daemonize():
    if threading.activeCount() != 1:
        logger.warn(
            'There are %r active threads. Daemonizing may cause'
            ' strange behavior.',
            threading.enumerate())

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

    if CONFIG.ENABLE_HTTPS:
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
    except Exception as e:
        logger.error('Could not launch browser: %s', e)


def initialize_scheduler():
    """
    Start the scheduled background tasks. Re-schedule if interval settings changed.
    """

    from headphones import updater, searcher, librarysync, postprocessor, \
        torrentfinished

    with SCHED_LOCK:

        # Check if scheduler should be started
        start_jobs = not len(SCHED.get_jobs())

        # Regular jobs
        minutes = CONFIG.SEARCH_INTERVAL
        schedule_job(searcher.searchforalbum, 'Search for Wanted', hours=0, minutes=minutes)

        minutes = CONFIG.DOWNLOAD_SCAN_INTERVAL
        schedule_job(postprocessor.checkFolder, 'Download Scan', hours=0, minutes=minutes)

        hours = CONFIG.LIBRARYSCAN_INTERVAL
        schedule_job(librarysync.libraryScan, 'Library Scan', hours=hours, minutes=0)

        hours = CONFIG.UPDATE_DB_INTERVAL
        schedule_job(updater.dbUpdate, 'MusicBrainz Update', hours=hours, minutes=0)

        # Update check
        if CONFIG.CHECK_GITHUB:
            if CONFIG.CHECK_GITHUB_INTERVAL:
                minutes = CONFIG.CHECK_GITHUB_INTERVAL
            else:
                minutes = 0
            schedule_job(versioncheck.checkGithub, 'Check GitHub for updates', hours=0,
                         minutes=minutes)

        # Remove Torrent + data if Post Processed and finished Seeding
        minutes = CONFIG.TORRENT_REMOVAL_INTERVAL
        schedule_job(torrentfinished.checkTorrentFinished, 'Torrent removal check', hours=0,
                     minutes=minutes)

        # Start scheduler
        if start_jobs and len(SCHED.get_jobs()):
            try:
                SCHED.start()
            except Exception as e:
                logger.info(e)

                # Debug
                # SCHED.print_jobs()


def schedule_job(function, name, hours=0, minutes=0):
    """
    Start scheduled job if starting or restarting headphones.
    Reschedule job if Interval Settings have changed.
    Remove job if if Interval Settings changed to 0

    """

    job = SCHED.get_job(name)
    if job:
        if hours == 0 and minutes == 0:
            SCHED.remove_job(name)
            logger.info("Removed background task: %s", name)
        elif job.trigger.interval != datetime.timedelta(hours=hours, minutes=minutes):
            SCHED.reschedule_job(name, trigger=IntervalTrigger(
                hours=hours, minutes=minutes))
            logger.info("Re-scheduled background task: %s", name)
    elif hours > 0 or minutes > 0:
        SCHED.add_job(function, id=name, trigger=IntervalTrigger(
            hours=hours, minutes=minutes))
        logger.info("Scheduled background task: %s", name)


def start():
    global started

    if _INITIALIZED:
        initialize_scheduler()
        started = True


def sig_handler(signum=None, frame=None):
    if signum is not None:
        logger.info("Signal %i caught, saving and exiting...", signum)
        shutdown()


def dbcheck():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT, IncludeExtras INTEGER, LatestAlbum TEXT, ReleaseDate TEXT, AlbumID TEXT, HaveTracks INTEGER, TotalTracks INTEGER, LastUpdated TEXT, ArtworkURL TEXT, ThumbURL TEXT, Extras TEXT, Type TEXT, MetaCritic TEXT)')
    # ReleaseFormat here means CD,Digital,Vinyl, etc. If using the default
    # Headphones hybrid release, ReleaseID will equal AlbumID (AlbumID is
    # releasegroup id)
    c.execute(
        'CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT, Type TEXT, ArtworkURL TEXT, ThumbURL TEXT, ReleaseID TEXT, ReleaseCountry TEXT, ReleaseFormat TEXT, SearchTerm TEXT, CriticScore TEXT, UserScore TEXT)')
    # Format here means mp3, flac, etc.
    c.execute(
        'CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT, TrackNumber INTEGER, Location TEXT, BitRate INTEGER, CleanName TEXT, Format TEXT, ReleaseID TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS allalbums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, AlbumID TEXT, Type TEXT, ReleaseID TEXT, ReleaseCountry TEXT, ReleaseFormat TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS alltracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT, TrackNumber INTEGER, Location TEXT, BitRate INTEGER, CleanName TEXT, Format TEXT, ReleaseID TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS snatched (AlbumID TEXT, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT, FolderName TEXT, Kind TEXT)')
    # Matched is a temporary value used to see if there was a match found in
    # alltracks
    c.execute(
        'CREATE TABLE IF NOT EXISTS have (ArtistName TEXT, AlbumTitle TEXT, TrackNumber TEXT, TrackTitle TEXT, TrackLength TEXT, BitRate TEXT, Genre TEXT, Date TEXT, TrackID TEXT, Location TEXT, CleanName TEXT, Format TEXT, Matched TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS lastfmcloud (ArtistName TEXT, ArtistID TEXT, Count INTEGER)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS descriptions (ArtistID TEXT, ReleaseGroupID TEXT, ReleaseID TEXT, Summary TEXT, Content TEXT, LastUpdated TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (ArtistID TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS newartists (ArtistName TEXT UNIQUE)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS releases (ReleaseID TEXT, ReleaseGroupID TEXT, UNIQUE(ReleaseID, ReleaseGroupID))')
    c.execute(
        'CREATE INDEX IF NOT EXISTS tracks_albumid ON tracks(AlbumID ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS album_artistid_reldate ON albums(ArtistID ASC, ReleaseDate DESC)')
    # Below creates indices to speed up Active Artist updating
    c.execute(
        'CREATE INDEX IF NOT EXISTS alltracks_relid ON alltracks(ReleaseID ASC, TrackID ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS allalbums_relid ON allalbums(ReleaseID ASC)')
    c.execute('CREATE INDEX IF NOT EXISTS have_location ON have(Location ASC)')
    # Below creates indices to speed up library scanning & matching
    c.execute(
        'CREATE INDEX IF NOT EXISTS have_Metadata ON have(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS have_CleanName ON have(CleanName ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS tracks_Metadata ON tracks(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS tracks_CleanName ON tracks(CleanName ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS alltracks_Metadata ON alltracks(ArtistName ASC, AlbumTitle ASC, TrackTitle ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS alltracks_CleanName ON alltracks(CleanName ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS tracks_Location ON tracks(Location ASC)')
    c.execute(
        'CREATE INDEX IF NOT EXISTS alltracks_Location ON alltracks(Location ASC)')

    try:
        c.execute('SELECT IncludeExtras from artists')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE artists ADD COLUMN IncludeExtras INTEGER DEFAULT 0')

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
        c.execute(
            'ALTER TABLE artists ADD COLUMN HaveTracks INTEGER DEFAULT 0')

    try:
        c.execute('SELECT TotalTracks from artists')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE artists ADD COLUMN TotalTracks INTEGER DEFAULT 0')

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
        c.execute(
            'ALTER TABLE artists ADD COLUMN LastUpdated TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ArtworkURL from artists')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE artists ADD COLUMN ArtworkURL TEXT DEFAULT NULL')

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
        c.execute(
            'ALTER TABLE descriptions ADD COLUMN ArtistID TEXT DEFAULT NULL')

    try:
        c.execute('SELECT LastUpdated from descriptions')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE descriptions ADD COLUMN LastUpdated TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseID from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN ReleaseID TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseFormat from albums')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE albums ADD COLUMN ReleaseFormat TEXT DEFAULT NULL')

    try:
        c.execute('SELECT ReleaseCountry from albums')
    except sqlite3.OperationalError:
        c.execute(
            'ALTER TABLE albums ADD COLUMN ReleaseCountry TEXT DEFAULT NULL')

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
        # Need to update some stuff when people are upgrading and have 'include
        # extras' set globally/for an artist
        if CONFIG.INCLUDE_EXTRAS:
            CONFIG.EXTRAS = "1,2,3,4,5,6,7,8"
        logger.info("Copying over current artist IncludeExtras information")
        artists = c.execute(
            'SELECT ArtistID, IncludeExtras from artists').fetchall()
        for artist in artists:
            if artist[1]:
                c.execute(
                    'UPDATE artists SET Extras=? WHERE ArtistID=?', ("1,2,3,4,5,6,7,8", artist[0]))

    try:
        c.execute('SELECT Kind from snatched')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE snatched ADD COLUMN Kind TEXT DEFAULT NULL')

    try:
        c.execute('SELECT SearchTerm from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN SearchTerm TEXT DEFAULT NULL')

    try:
        c.execute('SELECT CriticScore from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN CriticScore TEXT DEFAULT NULL')

    try:
        c.execute('SELECT UserScore from albums')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE albums ADD COLUMN UserScore TEXT DEFAULT NULL')

    try:
        c.execute('SELECT Type from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN Type TEXT DEFAULT NULL')

    try:
        c.execute('SELECT MetaCritic from artists')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE artists ADD COLUMN MetaCritic TEXT DEFAULT NULL')

    conn.commit()
    c.close()


def shutdown(restart=False, update=False):
    cherrypy.engine.exit()
    SCHED.shutdown(wait=False)

    CONFIG.write()

    if not restart and not update:
        logger.info('Headphones is shutting down...')

    if update:
        logger.info('Headphones is updating...')
        try:
            versioncheck.update()
        except Exception as e:
            logger.warn('Headphones failed to update: %s. Restarting.', e)

    if CREATEPID:
        logger.info('Removing pidfile %s', PIDFILE)
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
