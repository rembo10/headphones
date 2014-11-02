import headphones.logger
import itertools
import os
import re
from configobj import ConfigObj


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, basestring):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))

_CONFIG_DEFINITIONS = {
    'ADD_ALBUM_ART': (int, 'General', 0),
    'ADVANCEDENCODER': (str, 'General', ''),
    'ALBUM_ART_FORMAT': (str, 'General', 'folder'),
    # This is used in importer.py to determine how complete an album needs to
    # be - to be considered "downloaded". Percentage from 0-100
    'ALBUM_COMPLETION_PCT': (int, 'Advanced', 80),
    'API_ENABLED': (int, 'General', 0),
    'API_KEY': (str, 'General', ''),
    'AUTOWANT_ALL': (int, 'General', 0),
    'AUTOWANT_MANUALLY_ADDED': (int, 'General', 1),
    'AUTOWANT_UPCOMING': (int, 'General', 1),
    'AUTO_ADD_ARTISTS': (int, 'General', 1),
    'BITRATE': (int, 'General', 192),
    'BLACKHOLE': (int, 'General', 0),
    'BLACKHOLE_DIR': (str, 'General', ''),
    'BOXCAR_ENABLED': (int, 'Boxcar', 0),
    'BOXCAR_ONSNATCH': (int, 'Boxcar', 0),
    'BOXCAR_TOKEN': (str, 'Boxcar', ''),
    'CACHE_DIR': (str, 'General', ''),
    'CACHE_SIZEMB': (int, 'Advanced', 32),
    'CHECK_GITHUB': (int, 'General', 1),
    'CHECK_GITHUB_INTERVAL': (int, 'General', 360),
    'CHECK_GITHUB_ON_STARTUP': (int, 'General', 1),
    'CLEANUP_FILES': (int, 'General', 0),
    'CONFIG_VERSION': (str, 'General', '0'),
    'CORRECT_METADATA': (int, 'General', 0),
    'CUSTOMHOST': (str, 'General', 'localhost'),
    'CUSTOMPORT': (int, 'General', 5000),
    'CUSTOMSLEEP': (int, 'General', 1),
    'DELETE_LOSSLESS_FILES': (int, 'General', 1),
    'DESTINATION_DIR': (str, 'General', ''),
    'DETECT_BITRATE': (int, 'General', 0),
    'DOWNLOAD_DIR': (str, 'General', ''),
    'DOWNLOAD_SCAN_INTERVAL': (int, 'General', 5),
    'DOWNLOAD_TORRENT_DIR': (str, 'General', ''),
    'DO_NOT_OVERRIDE_GIT_BRANCH': (int, 'General', 0),
    'EMBED_ALBUM_ART': (int, 'General', 0),
    'EMBED_LYRICS': (int, 'General', 0),
    'ENABLE_HTTPS': (int, 'General', 0),
    'ENCODER': (str, 'General', 'ffmpeg'),
    'ENCODERFOLDER': (str, 'General', ''),
    'ENCODERLOSSLESS': (int, 'General', 1),
    'ENCODEROUTPUTFORMAT': (str, 'General', 'mp3'),
    'ENCODERQUALITY': (int, 'General', 2),
    'ENCODERVBRCBR': (str, 'General', 'cbr'),
    'ENCODER_MULTICORE': (int, 'General', 0),
    'ENCODER_MULTICORE_COUNT': (int, 'General', 0),
    'ENCODER_PATH': (str, 'General', ''),
    'EXTRAS': (str, 'General', ''),
    'EXTRA_NEWZNABS': (list, 'Newznab', ''),
    'FILE_FORMAT': (str, 'General', 'Track Artist - Album [Year] - Title'),
    'FILE_PERMISSIONS': (str, 'General', '0644'),
    'FILE_UNDERSCORES': (int, 'General', 0),
    'FOLDER_FORMAT': (str, 'General', 'Artist/Album [Year]'),
    'FOLDER_PERMISSIONS': (str, 'General', '0755'),
    'FREEZE_DB': (int, 'General', 0),
    'GIT_BRANCH': (str, 'General', 'master'),
    'GIT_PATH': (str, 'General', ''),
    'GIT_USER': (str, 'General', 'rembo10'),
    'GROWL_ENABLED': (int, 'Growl', 0),
    'GROWL_HOST': (str, 'Growl', ''),
    'GROWL_ONSNATCH': (int, 'Growl', 0),
    'GROWL_PASSWORD': (str, 'Growl', ''),
    'HEADPHONES_INDEXER': (bool_int, 'General', False),
    'HPPASS': (str, 'General', ''),
    'HPUSER': (str, 'General', ''),
    'HTTPS_CERT': (str, 'General', ''),
    'HTTPS_KEY': (str, 'General', ''),
    'HTTP_HOST': (str, 'General', '0.0.0.0'),
    'HTTP_PASSWORD': (str, 'General', ''),
    'HTTP_PORT': (int, 'General', 8181),
    'HTTP_PROXY': (int, 'General', 0),
    'HTTP_ROOT': (str, 'General', '/'),
    'HTTP_USERNAME': (str, 'General', ''),
    'IGNORED_WORDS': (str, 'General', ''),
    'INCLUDE_EXTRAS': (int, 'General', 0),
    'INTERFACE': (str, 'General', 'default'),
    'JOURNAL_MODE': (str, 'Advanced', 'wal'),
    'KAT': (int, 'Kat', 0),
    'KAT_PROXY_URL': (str, 'Kat', ''),
    'KAT_RATIO': (str, 'Kat', ''),
    'KEEP_NFO': (int, 'General', 0),
    'KEEP_TORRENT_FILES': (int, 'General', 0),
    'LASTFM_USERNAME': (str, 'General', ''),
    'LAUNCH_BROWSER': (int, 'General', 1),
    'LIBRARYSCAN': (int, 'General', 1),
    'LIBRARYSCAN_INTERVAL': (int, 'General', 300),
    'LMS_ENABLED': (int, 'LMS', 0),
    'LMS_HOST': (str, 'LMS', ''),
    'LOG_DIR': (str, 'General', ''),
    'LOSSLESS_BITRATE_FROM': (int, 'General', 0),
    'LOSSLESS_BITRATE_TO': (int, 'General', 0),
    'LOSSLESS_DESTINATION_DIR': (str, 'General', ''),
    'MB_IGNORE_AGE': (int, 'General', 365),
    'MININOVA': (int, 'Mininova', 0),
    'MININOVA_RATIO': (str, 'Mininova', ''),
    'MIRROR': (str, 'General', 'musicbrainz.org'),
    'MOVE_FILES': (int, 'General', 0),
    'MPC_ENABLED': (bool_int, 'MPC', False),
    'MUSIC_DIR': (str, 'General', ''),
    'MUSIC_ENCODER': (int, 'General', 0),
    'NEWZNAB': (int, 'Newznab', 0),
    'NEWZNAB_APIKEY': (str, 'Newznab', ''),
    'NEWZNAB_ENABLED': (int, 'Newznab', 1),
    'NEWZNAB_HOST': (str, 'Newznab', ''),
    'NMA_APIKEY': (str, 'NMA', ''),
    'NMA_ENABLED': (int, 'NMA', 0),
    'NMA_ONSNATCH': (int, 'NMA', 0),
    'NMA_PRIORITY': (int, 'NMA', 0),
    'NUMBEROFSEEDERS': (str, 'General', '10'),
    'NZBGET_CATEGORY': (str, 'NZBget', ''),
    'NZBGET_HOST': (str, 'NZBget', ''),
    'NZBGET_PASSWORD': (str, 'NZBget', ''),
    'NZBGET_PRIORITY': (int, 'NZBget', 0),
    'NZBGET_USERNAME': (str, 'NZBget', 'nzbget'),
    'NZBSORG': (int, 'NZBsorg', 0),
    'NZBSORG_HASH': (str, 'NZBsorg', ''),
    'NZBSORG_UID': (str, 'NZBsorg', ''),
    'NZB_DOWNLOADER': (int, 'General', 0),
    'OMGWTFNZBS': (int, 'omgwtfnzbs', 0),
    'OMGWTFNZBS_APIKEY': (str, 'omgwtfnzbs', ''),
    'OMGWTFNZBS_UID': (str, 'omgwtfnzbs', ''),
    'OPEN_MAGNET_LINKS': (int, 'General', 0),  # 0: Ignore, 1: Open, 2: Convert
    'MAGNET_LINKS': (int, 'General', 0),
    'OSX_NOTIFY_APP': (str, 'OSX_Notify', '/Applications/Headphones'),
    'OSX_NOTIFY_ENABLED': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ONSNATCH': (int, 'OSX_Notify', 0),
    'PIRATEBAY': (int, 'Piratebay', 0),
    'PIRATEBAY_PROXY_URL': (str, 'Piratebay', ''),
    'PIRATEBAY_RATIO': (str, 'Piratebay', ''),
    'PLEX_CLIENT_HOST': (str, 'Plex', ''),
    'PLEX_ENABLED': (int, 'Plex', 0),
    'PLEX_NOTIFY': (int, 'Plex', 0),
    'PLEX_PASSWORD': (str, 'Plex', ''),
    'PLEX_SERVER_HOST': (str, 'Plex', ''),
    'PLEX_UPDATE': (int, 'Plex', 0),
    'PLEX_USERNAME': (str, 'Plex', ''),
    'PREFERRED_BITRATE': (str, 'General', ''),
    'PREFERRED_BITRATE_ALLOW_LOSSLESS': (int, 'General', 0),
    'PREFERRED_BITRATE_HIGH_BUFFER': (int, 'General', 0),
    'PREFERRED_BITRATE_LOW_BUFFER': (int, 'General', 0),
    'PREFERRED_QUALITY': (int, 'General', 0),
    'PREFERRED_WORDS': (str, 'General', ''),
    'PREFER_TORRENTS': (int, 'General', 0),
    'PROWL_ENABLED': (int, 'Prowl', 0),
    'PROWL_KEYS': (str, 'Prowl', ''),
    'PROWL_ONSNATCH': (int, 'Prowl', 0),
    'PROWL_PRIORITY': (int, 'Prowl', 0),
    'PUSHALOT_APIKEY': (str, 'Pushalot', ''),
    'PUSHALOT_ENABLED': (int, 'Pushalot', 0),
    'PUSHALOT_ONSNATCH': (int, 'Pushalot', 0),
    'PUSHBULLET_APIKEY': (str, 'PushBullet', ''),
    'PUSHBULLET_DEVICEID': (str, 'PushBullet', ''),
    'PUSHBULLET_ENABLED': (int, 'PushBullet', 0),
    'PUSHBULLET_ONSNATCH': (int, 'PushBullet', 0),
    'PUSHOVER_APITOKEN': (str, 'Pushover', ''),
    'PUSHOVER_ENABLED': (int, 'Pushover', 0),
    'PUSHOVER_KEYS': (str, 'Pushover', ''),
    'PUSHOVER_ONSNATCH': (int, 'Pushover', 0),
    'PUSHOVER_PRIORITY': (int, 'Pushover', 0),
    'RENAME_FILES': (int, 'General', 0),
    'REPLACE_EXISTING_FOLDERS': (int, 'General', 0),
    'REQUIRED_WORDS': (str, 'General', ''),
    'RUTRACKER': (int, 'Rutracker', 0),
    'RUTRACKER_PASSWORD': (str, 'Rutracker', ''),
    'RUTRACKER_RATIO': (str, 'Rutracker', ''),
    'RUTRACKER_USER': (str, 'Rutracker', ''),
    'SAB_APIKEY': (str, 'SABnzbd', ''),
    'SAB_CATEGORY': (str, 'SABnzbd', ''),
    'SAB_HOST': (str, 'SABnzbd', ''),
    'SAB_PASSWORD': (str, 'SABnzbd', ''),
    'SAB_USERNAME': (str, 'SABnzbd', ''),
    'SAMPLINGFREQUENCY': (int, 'General', 44100),
    'SEARCH_INTERVAL': (int, 'General', 1440),
    'SONGKICK_APIKEY': (str, 'Songkick', 'nd1We7dFW2RqxPw8'),
    'SONGKICK_ENABLED': (int, 'Songkick', 1),
    'SONGKICK_FILTER_ENABLED': (int, 'Songkick', 0),
    'SONGKICK_LOCATION': (str, 'Songkick', ''),
    'SUBSONIC_ENABLED': (int, 'Subsonic', 0),
    'SUBSONIC_HOST': (str, 'Subsonic', ''),
    'SUBSONIC_PASSWORD': (str, 'Subsonic', ''),
    'SUBSONIC_USERNAME': (str, 'Subsonic', ''),
    'SYNOINDEX_ENABLED': (int, 'Synoindex', 0),
    'TORRENTBLACKHOLE_DIR': (str, 'General', ''),
    'TORRENT_DOWNLOADER': (int, 'General', 0),
    'TORRENT_REMOVAL_INTERVAL': (int, 'General', 720),
    'TRANSMISSION_HOST': (str, 'Transmission', ''),
    'TRANSMISSION_PASSWORD': (str, 'Transmission', ''),
    'TRANSMISSION_USERNAME': (str, 'Transmission', ''),
    'TWITTER_ENABLED': (int, 'Twitter', 0),
    'TWITTER_ONSNATCH': (int, 'Twitter', 0),
    'TWITTER_PASSWORD': (str, 'Twitter', ''),
    'TWITTER_PREFIX': (str, 'Twitter', 'Headphones'),
    'TWITTER_USERNAME': (str, 'Twitter', ''),
    'UPDATE_DB_INTERVAL': (int, 'General', 24),
    'USENET_RETENTION': (int, 'General', '1500'),
    'UTORRENT_HOST': (str, 'uTorrent', ''),
    'UTORRENT_LABEL': (str, 'uTorrent', ''),
    'UTORRENT_PASSWORD': (str, 'uTorrent', ''),
    'UTORRENT_USERNAME': (str, 'uTorrent', ''),
    'VERIFY_SSL_CERT': (bool_int, 'Advanced', 1),
    'WAFFLES': (int, 'Waffles', 0),
    'WAFFLES_PASSKEY': (str, 'Waffles', ''),
    'WAFFLES_RATIO': (str, 'Waffles', ''),
    'WAFFLES_UID': (str, 'Waffles', ''),
    'WHATCD': (int, 'What.cd', 0),
    'WHATCD_PASSWORD': (str, 'What.cd', ''),
    'WHATCD_RATIO': (str, 'What.cd', ''),
    'WHATCD_USERNAME': (str, 'What.cd', ''),
    'XBMC_ENABLED': (int, 'XBMC', 0),
    'XBMC_HOST': (str, 'XBMC', ''),
    'XBMC_NOTIFY': (int, 'XBMC', 0),
    'XBMC_PASSWORD': (str, 'XBMC', ''),
    'XBMC_UPDATE': (int, 'XBMC', 0),
    'XBMC_USERNAME': (str, 'XBMC', ''),
    'XLDPROFILE': (str, 'General', '')
}

# pylint:disable=R0902
# it might be nice to refactor for fewer instance variables
class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file):
        """ Initialize the config with values from a file """
        self._config_file = config_file
        self._config = ConfigObj(self._config_file, encoding='utf-8')
        for key in _CONFIG_DEFINITIONS.keys():
            self.check_setting(key)
        self.ENCODER_MULTICORE_COUNT = max(0, self.ENCODER_MULTICORE_COUNT)
        self._upgrade()

    def _define(self, name):
        key = name.upper()
        ini_key = name.lower()
        definition = _CONFIG_DEFINITIONS[key]
        if len(definition) == 3:
            definition_type, section, default = definition
        else:
            definition_type, section, _, default = definition
        return key, definition_type, section, ini_key, default

    def check_section(self, section):
        """ Check if INI section exists, if not create it """
        if section not in self._config:
            self._config[section] = {}
            return True
        else:
            return False

    def check_setting(self, key):
        """ Cast any value in the config to the right type or use the default """
        key, definition_type, section, ini_key, default = self._define(key)
        self.check_section(section)
        try:
            my_val = definition_type(self._config[section][ini_key])
        except Exception:
            my_val = definition_type(default)
            self._config[section][ini_key] = my_val
        return my_val

    def write(self):
        """ Make a copy of the stored config and write it to the configured file """
        new_config = ConfigObj(encoding="UTF-8")
        new_config.filename = self._config_file

        # first copy over everything from the old config, even if it is not
        # correctly defined to keep from losing data
        for key, subkeys in self._config.items():
            if key not in new_config:
                new_config[key] = {}
            for subkey, value in subkeys.items():
                new_config[key][subkey] = value

        # next make sure that everything we expect to have defined is so
        for key in _CONFIG_DEFINITIONS.keys():
            key, definition_type, section, ini_key, default = self._define(key)
            self.check_setting(key)
            if section not in new_config:
                new_config[section] = {}
            new_config[section][ini_key] = self._config[section][ini_key]

        # Write it to file
        headphones.logger.info("Writing configuration to file")

        try:
            new_config.write()
        except IOError as e:
            headphones.logger.error("Error writing configuration file: %s", e)

    def get_extra_newznabs(self):
        """ Return the extra newznab tuples """
        extra_newznabs = list(
            itertools.izip(*[itertools.islice(self.EXTRA_NEWZNABS, i, None, 3)
            for i in range(3)])
        )
        return extra_newznabs

    def clear_extra_newznabs(self):
        """ Forget about the configured extra newznabs """
        self.EXTRA_NEWZNABS = []

    def add_extra_newznab(self, newznab):
        """ Add a new extra newznab """
        extra_newznabs = self.EXTRA_NEWZNABS
        for item in newznab:
            extra_newznabs.append(item)
        self.EXTRA_NEWZNABS = extra_newznabs

    def __getattr__(self, name):
        """
        Returns something from the ini unless it is a real property
        of the configuration object or is not all caps.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__getattr__(name)
        else:
            return self.check_setting(name)

    def __setattr__(self, name, value):
        """
        Maps all-caps properties to ini values unless they exist on the
        configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            super(Config, self).__setattr__(name, value)
            return value
        else:
            key, definition_type, section, ini_key, default = self._define(name)
            self._config[section][ini_key] = definition_type(value)
            return self._config[section][ini_key]

    def process_kwargs(self, kwargs):
        """
        Given a big bunch of key value pairs, apply them to the ini.
        """
        for name, value in kwargs.items():
            key, definition_type, section, ini_key, default = self._define(name)
            self._config[section][ini_key] = definition_type(value)

    def _upgrade(self):
        """ Update folder formats in the config & bump up config version """
        if self.CONFIG_VERSION == '0':
            from headphones.helpers import replace_all
            file_values = {
                'tracknumber': 'Track',
                'title': 'Title',
                'artist': 'Artist',
                'album': 'Album',
                'year': 'Year'
            }
            folder_values = {
                'artist': 'Artist',
                'album': 'Album',
                'year': 'Year',
                'releasetype': 'Type',
                'first': 'First',
                'lowerfirst': 'first'
            }
            self.FILE_FORMAT = replace_all(self.FILE_FORMAT, file_values)
            self.FOLDER_FORMAT = replace_all(self.FOLDER_FORMAT, folder_values)

            self.CONFIG_VERSION = '1'

        if self.CONFIG_VERSION == '1':
            from headphones.helpers import replace_all
            file_values = {
                'Track': '$Track',
                'Title': '$Title',
                'Artist': '$Artist',
                'Album': '$Album',
                'Year': '$Year',
                'track': '$track',
                'title': '$title',
                'artist': '$artist',
                'album': '$album',
                'year': '$year'
            }
            folder_values = {
                'Artist': '$Artist',
                'Album': '$Album',
                'Year': '$Year',
                'Type': '$Type',
                'First': '$First',
                'artist': '$artist',
                'album': '$album',
                'year': '$year',
                'type': '$type',
                'first': '$first'
            }
            self.FILE_FORMAT = replace_all(self.FILE_FORMAT, file_values)
            self.FOLDER_FORMAT = replace_all(self.FOLDER_FORMAT, folder_values)
            self.CONFIG_VERSION = '2'

        if self.CONFIG_VERSION == '2':
            # Update the config to use direct path to the encoder rather than the encoder folder
            if self.ENCODERFOLDER:
                self.ENCODER_PATH = os.path.join(self.ENCODERFOLDER, self.ENCODER)
            self.CONFIG_VERSION = '3'

        if self.CONFIG_VERSION == '3':
            # Update the BLACKHOLE option to the NZB_DOWNLOADER format
            if self.BLACKHOLE:
                self.NZB_DOWNLOADER = 2
            self.CONFIG_VERSION = '4'

        # Enable Headphones Indexer if they have a VIP account
        if self.CONFIG_VERSION == '4':
            if self.HPUSER and self.HPPASS:
                self.HEADPHONES_INDEXER = True
            self.CONFIG_VERSION = '5'

        if self.CONFIG_VERSION == '5':
            if self.OPEN_MAGNET_LINKS:
                self.MAGNET_LINKS = 2
            self.CONFIG_VERSION = '5'
