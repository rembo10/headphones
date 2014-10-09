import headphones.logger
import itertools
import os
import re
from configobj import ConfigObj

_config_definitions = {
    'CONFIG_VERSION': (str, 'General', '0'),
    'HTTP_PORT': (int, 'General', 8181),
    'HTTP_HOST': (str, 'General', '0.0.0.0'),
    'HTTP_USERNAME': (str, 'General', ''),
    'HTTP_PASSWORD': (str, 'General', ''),
    'HTTP_ROOT': (str, 'General', '/'),
    'HTTP_PROXY': (int, 'General', 0),
    'ENABLE_HTTPS': (int, 'General', 0),
    'LAUNCH_BROWSER': (int, 'General', 1),
    'API_ENABLED': (int, 'General', 0),
    'API_KEY': (str, 'General', ''),
    'GIT_PATH': (str, 'General', ''),
    'GIT_USER': (str, 'General', 'rembo10'),
    'GIT_BRANCH': (str, 'General', 'master'),
    'DO_NOT_OVERRIDE_GIT_BRANCH': (int, 'General', 0),
    'LOG_DIR': (str, 'General', ''),
    'CACHE_DIR': (str, 'General', ''),
    'CHECK_GITHUB': (int, 'General', 1),
    'CHECK_GITHUB_ON_STARTUP': (int, 'General', 1),
    'CHECK_GITHUB_INTERVAL': (int, 'General', 360),
    'MUSIC_DIR': (str, 'General', ''),
    'DESTINATION_DIR': (str, 'General',''),
    'LOSSLESS_DESTINATION_DIR': (str, 'General', ''),
    'PREFERRED_QUALITY': (int, 'General', 0),
    'PREFERRED_BITRATE': (str, 'General', ''),
    'PREFERRED_BITRATE_HIGH_BUFFER': (int, 'General', 0),
    'PREFERRED_BITRATE_LOW_BUFFER': (int, 'General', 0),
    'PREFERRED_BITRATE_ALLOW_LOSSLESS': (int, 'General', 0),
    'DETECT_BITRATE': (int, 'General', 0),
    'LOSSLESS_BITRATE_FROM': (int, 'General', 0),
    'LOSSLESS_BITRATE_TO': (int, 'General', 0),
    'AUTO_ADD_ARTISTS': (int, 'General', 1),
    'CORRECT_METADATA': (int, 'General', 0),
    'FREEZE_DB': (int, 'General', 0),
    'MOVE_FILES': (int, 'General', 0),
    'RENAME_FILES': (int, 'General', 0),
    'FOLDER_FORMAT': (str, 'General', 'Artist/Album [Year]'),
    'FILE_FORMAT': (str, 'General', 'Track Artist - Album [Year] - Title'),
    'FILE_UNDERSCORES': (int, 'General', 0),
    'CLEANUP_FILES': (int, 'General', 0),
    'KEEP_NFO': (int, 'General', 0),
    'ADD_ALBUM_ART': (int, 'General', 0),
    'ALBUM_ART_FORMAT': (str, 'General', 'folder'),
    'EMBED_ALBUM_ART': (int, 'General', 0),
    'EMBED_LYRICS': (int, 'General', 0),
    'REPLACE_EXISTING_FOLDERS': (int, 'General', 0),
    'NZB_DOWNLOADER': (int, 'General', 0),  # 0: sabnzbd, 1: nzbget, 2: blackhole
    'TORRENT_DOWNLOADER': (int, 'General', 0),  # 0: blackhole, 1: transmission, 2: utorrent
    'DOWNLOAD_DIR': (str, 'General', ''),
    'BLACKHOLE': (int, 'General', 0),
    'BLACKHOLE_DIR': (str, 'General', ''),
    'USENET_RETENTION': (int, 'General', '1500'),
    'INCLUDE_EXTRAS': (int, 'General', 0),
    'EXTRAS': (str, 'General', ''),
    'AUTOWANT_UPCOMING': (int, 'General', 1),
    'AUTOWANT_ALL': (int, 'General', 0),
    'AUTOWANT_MANUALLY_ADDED': (int, 'General', 1),
    'KEEP_TORRENT_FILES': (int, 'General', 0),
    'PREFER_TORRENTS': (int, 'General', 0),

    'OPEN_MAGNET_LINKS': (int, 'General', 0),
    'SEARCH_INTERVAL': (int, 'General', 1440),
    'LIBRARYSCAN': (int, 'General', 1),
    'LIBRARYSCAN_INTERVAL': (int, 'General', 300),
    'DOWNLOAD_SCAN_INTERVAL': (int, 'General', 5),
    'UPDATE_DB_INTERVAL': (int, 'General', 24),
    'MB_IGNORE_AGE': (int, 'General', 365),
    'TORRENT_REMOVAL_INTERVAL': (int, 'General', 720),
    'TORRENTBLACKHOLE_DIR': (str, 'General', ''),
    'NUMBEROFSEEDERS': (str, 'General', '10'),
    'DOWNLOAD_TORRENT_DIR': (str, 'General', ''),
    'KAT': (int, 'Kat', 0),
    'KAT_PROXY_URL': (str, 'Kat', ''),
    'KAT_RATIO': (str, 'Kat', ''),
    'PIRATEBAY': (int, 'Piratebay', 0),
    'PIRATEBAY_PROXY_URL': (str, 'Piratebay', ''),
    'PIRATEBAY_RATIO': (str, 'Piratebay', ''),
    'MININOVA': (int, 'Mininova', 0),
    'MININOVA_RATIO': (str, 'Mininova', ''),
    'WAFFLES': (int, 'Waffles', 0),
    'WAFFLES_UID': (str, 'Waffles', ''),
    'WAFFLES_PASSKEY': (str, 'Waffles', ''),
    'WAFFLES_RATIO': (str, 'Waffles', ''),
    'RUTRACKER': (int, 'Rutracker', 0),
    'RUTRACKER_USER': (str, 'Rutracker', ''),
    'RUTRACKER_PASSWORD': (str, 'Rutracker', ''),
    'RUTRACKER_RATIO': (str, 'Rutracker', ''),
    'WHATCD': (int, 'What.cd', 0),
    'WHATCD_USERNAME': (str, 'What.cd', ''),
    'WHATCD_PASSWORD': (str, 'What.cd', ''),
    'WHATCD_RATIO': (str, 'What.cd', ''),
    'SAB_HOST': (str, 'SABnzbd', ''),
    'SAB_USERNAME': (str, 'SABnzbd', ''),
    'SAB_PASSWORD': (str, 'SABnzbd', ''),
    'SAB_APIKEY': (str, 'SABnzbd', ''),
    'SAB_CATEGORY': (str, 'SABnzbd', ''),
    'NZBGET_USERNAME': (str, 'NZBget', 'nzbget_username', 'nzbget'),
    'NZBGET_PASSWORD': (str, 'NZBget', 'nzbget_password', ''),
    'NZBGET_CATEGORY': (str, 'NZBget', 'nzbget_category', ''),
    'NZBGET_HOST': (str, 'NZBget', 'nzbget_host', ''),
    'NZBGET_PRIORITY': (int, 'NZBget', 'nzbget_priority', 0),
    'TRANSMISSION_HOST': (str,  'Transmission', 'transmission_host', ''),
    'TRANSMISSION_USERNAME': (str,  'Transmission', 'transmission_username', ''),
    'TRANSMISSION_PASSWORD': (str,  'Transmission', 'transmission_password', ''),
    'UTORRENT_HOST': (str,  'uTorrent', 'utorrent_host', ''),
    'UTORRENT_USERNAME': (str,  'uTorrent', 'utorrent_username', ''),
    'UTORRENT_PASSWORD': (str,  'uTorrent', 'utorrent_password', ''),
    'UTORRENT_LABEL': (str,  'uTorrent', 'utorrent_label', ''),
    'NEWZNAB': (int, 'Newznab', 'newznab', 0),
    'NEWZNAB_HOST': (str,  'Newznab', 'newznab_host', ''),
    'NEWZNAB_APIKEY': (str,  'Newznab', 'newznab_apikey', ''),
    'NEWZNAB_ENABLED': (int, 'Newznab', 'newznab_enabled', 1),
    'NZBSORG': (int, 'NZBsorg', 'nzbsorg', 0),
    'NZBSORG_UID': (str, 'NZBsorg', 'nzbsorg_uid', ''),
    'NZBSORG_HASH': (str, 'NZBsorg', 'nzbsorg_hash', ''),
    'OMGWTFNZBS': (int, 'omgwtfnzbs', 'omgwtfnzbs', 0),
    'OMGWTFNZBS_UID': (str, 'omgwtfnzbs', 'omgwtfnzbs_uid', ''),
    'OMGWTFNZBS_APIKEY': (str, 'omgwtfnzbs', 'omgwtfnzbs_apikey', ''),
    'PREFERRED_WORDS': (str, 'General', 'preferred_words', ''),
    'IGNORED_WORDS': (str, 'General', 'ignored_words', ''),
    'REQUIRED_WORDS': (str, 'General', 'required_words', ''),
    'LASTFM_USERNAME': (str, 'General', 'lastfm_username', ''),
    'INTERFACE': (str, 'General', 'interface', 'default'),
    'FOLDER_PERMISSIONS': (str, 'General', 'folder_permissions', '0755'),
    'FILE_PERMISSIONS': (str, 'General', 'file_permissions', '0644'),
    'ENCODERFOLDER': (str, 'General', 'encoderfolder', ''),
    'ENCODER_PATH': (str, 'General', 'encoder_path', ''),
    'ENCODER': (str, 'General', 'encoder', 'ffmpeg'),
    'XLDPROFILE': (str, 'General', 'xldprofile', ''),
    'BITRATE': (int, 'General', 'bitrate', 192),
    'SAMPLINGFREQUENCY': (int, 'General', 'samplingfrequency', 44100),
    'MUSIC_ENCODER': (int, 'General', 'music_encoder', 0),
    'ADVANCEDENCODER': (str, 'General', 'advancedencoder', ''),
    'ENCODEROUTPUTFORMAT': (str, 'General', 'encoderoutputformat', 'mp3'),
    'ENCODERQUALITY': (int, 'General', 'encoderquality', 2),
    'ENCODERVBRCBR': (str, 'General', 'encodervbrcbr', 'cbr'),
    'ENCODERLOSSLESS': (int, 'General', 'encoderlossless', 1),
    'ENCODER_MULTICORE': (int, 'General', 'encoder_multicore', 0),
    'DELETE_LOSSLESS_FILES': (int, 'General', 'delete_lossless_files', 1),
    'GROWL_ENABLED': (int, 'Growl', 'growl_enabled', 0),
    'GROWL_HOST': (str, 'Growl', 'growl_host', ''),
    'GROWL_PASSWORD': (str, 'Growl', 'growl_password', ''),
    'GROWL_ONSNATCH': (int, 'Growl', 'growl_onsnatch', 0),
    'PROWL_ENABLED': (int, 'Prowl', 'prowl_enabled', 0),
    'PROWL_KEYS': (str, 'Prowl', 'prowl_keys', ''),
    'PROWL_ONSNATCH': (int, 'Prowl', 'prowl_onsnatch', 0),
    'PROWL_PRIORITY': (int, 'Prowl', 'prowl_priority', 0),
    'XBMC_ENABLED': (int, 'XBMC', 'xbmc_enabled', 0),
    'XBMC_HOST': (str, 'XBMC', 'xbmc_host', ''),
    'XBMC_USERNAME': (str, 'XBMC', 'xbmc_username', ''),
    'XBMC_PASSWORD': (str, 'XBMC', 'xbmc_password', ''),
    'XBMC_UPDATE': (int, 'XBMC', 'xbmc_update', 0),
    'XBMC_NOTIFY': (int, 'XBMC', 'xbmc_notify', 0),
    'LMS_ENABLED': (int, 'LMS', 'lms_enabled', 0),
    'LMS_HOST': (str, 'LMS', 'lms_host', ''),
    'PLEX_ENABLED': (int, 'Plex', 'plex_enabled', 0),
    'PLEX_SERVER_HOST': (str, 'Plex', 'plex_server_host', ''),
    'PLEX_CLIENT_HOST': (str, 'Plex', 'plex_client_host', ''),
    'PLEX_USERNAME': (str, 'Plex', 'plex_username', ''),
    'PLEX_PASSWORD': (str, 'Plex', 'plex_password', ''),
    'PLEX_UPDATE': (int, 'Plex', 'plex_update', 0),
    'PLEX_NOTIFY': (int, 'Plex', 'plex_notify', 0),
    'NMA_ENABLED': (int, 'NMA', 'nma_enabled', 0),
    'NMA_APIKEY': (str, 'NMA', 'nma_apikey', ''),
    'NMA_PRIORITY': (int, 'NMA', 'nma_priority', 0),
    'NMA_ONSNATCH': (int, 'NMA', 'nma_onsnatch', 0),
    'PUSHALOT_ENABLED': (int, 'Pushalot', 'pushalot_enabled', 0),
    'PUSHALOT_APIKEY': (str, 'Pushalot', 'pushalot_apikey', ''),
    'PUSHALOT_ONSNATCH': (int, 'Pushalot', 'pushalot_onsnatch', 0),
    'SYNOINDEX_ENABLED': (int, 'Synoindex', 'synoindex_enabled', 0),
    'PUSHOVER_ENABLED': (int, 'Pushover', 'pushover_enabled', 0),
    'PUSHOVER_KEYS': (str, 'Pushover', 'pushover_keys', ''),
    'PUSHOVER_ONSNATCH': (int, 'Pushover', 'pushover_onsnatch', 0),
    'PUSHOVER_PRIORITY': (int, 'Pushover', 'pushover_priority', 0),
    'PUSHOVER_APITOKEN': (str, 'Pushover', 'pushover_apitoken', ''),
    'PUSHBULLET_ENABLED': (int, 'PushBullet', 'pushbullet_enabled', 0),
    'PUSHBULLET_APIKEY': (str, 'PushBullet', 'pushbullet_apikey', ''),
    'PUSHBULLET_DEVICEID': (str, 'PushBullet', 'pushbullet_deviceid', ''),
    'PUSHBULLET_ONSNATCH': (int, 'PushBullet', 'pushbullet_onsnatch', 0),
    'TWITTER_ENABLED': (int, 'Twitter', 'twitter_enabled', 0),
    'TWITTER_ONSNATCH': (int, 'Twitter', 'twitter_onsnatch', 0),
    'TWITTER_USERNAME': (str, 'Twitter', 'twitter_username', ''),
    'TWITTER_PASSWORD': (str, 'Twitter', 'twitter_password', ''),
    'TWITTER_PREFIX': (str, 'Twitter', 'twitter_prefix', 'Headphones'),
    'OSX_NOTIFY_ENABLED': (int, 'OSX_Notify', 'osx_notify_enabled', 0),
    'OSX_NOTIFY_ONSNATCH': (int, 'OSX_Notify', 'osx_notify_onsnatch', 0),
    'OSX_NOTIFY_APP': (str, 'OSX_Notify', 'osx_notify_app', '/Applications/Headphones'),
    'BOXCAR_ENABLED': (int, 'Boxcar', 'boxcar_enabled', 0),
    'BOXCAR_ONSNATCH': (int, 'Boxcar', 'boxcar_onsnatch', 0),
    'BOXCAR_TOKEN': (str, 'Boxcar', 'boxcar_token', ''),
    'SUBSONIC_ENABLED': (int, 'Subsonic', 'subsonic_enabled', 0),
    'SUBSONIC_HOST': (str, 'Subsonic', 'subsonic_host', ''),
    'SUBSONIC_USERNAME': (str, 'Subsonic', 'subsonic_username', ''),
    'SUBSONIC_PASSWORD': (str, 'Subsonic', 'subsonic_password', ''),
    'SONGKICK_ENABLED': (int, 'Songkick', 'songkick_enabled', 1),
    'SONGKICK_APIKEY': (str, 'Songkick', 'songkick_apikey', 'nd1We7dFW2RqxPw8'),
    'SONGKICK_LOCATION': (str, 'Songkick', 'songkick_location', ''),
    'SONGKICK_FILTER_ENABLED': (int, 'Songkick', 'songkick_filter_enabled', 0),
    'MIRROR': (str, 'General', 'mirror', 'musicbrainz.org'),
    'CUSTOMHOST': (str, 'General', 'customhost', 'localhost'),
    'CUSTOMPORT': (int, 'General', 'customport', 5000),
    'CUSTOMSLEEP': (int, 'General', 'customsleep', 1),
    'HPUSER': (str, 'General', 'hpuser', ''),
    'HPPASS': (str, 'General', 'hppass', ''),
    'CACHE_SIZEMB': (int, 'Advanced', 'cache_sizemb', 32),
    'JOURNAL_MODE': (str, 'Advanced', 'journal_mode', 'wal'),
    'ALBUM_COMPLETION_PCT': (int, 'Advanced', 'album_completion_pct', 80),  # This is used in importer.py to determine how complete an album needs to be - to be considered "downloaded". Percentage from 0-100
    'VERIFY_SSL_CERT': (bool, 'Advanced', 'verify_ssl_cert', 1),
    'HTTPS_CERT': (str, 'General', 'https_cert', ''),
    'HTTPS_KEY': (str, 'General', 'https_key', ''),
    'ENCODER_MULTICORE_COUNT': (int, 'General', 'encoder_multicore_count', 0),
    'EXTRA_NEWZNABS': (list, 'Newznab', 'extra_newznabs', ''),
    'MPC_ENABLED': (bool, 'MPC', 'mpc_enabled', False),
    'HEADPHONES_INDEXER': (bool, 'General', 'headphones_indexer', False)
}


class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file):
        """ Initialize the config with values from a file """
        self._config_file = config_file
        self._config = ConfigObj(self._config_file, encoding='utf-8')
        for key in _config_definitions.keys():
            self.check_setting(key)
        self.ENCODER_MULTICORE_COUNT = max(0, self.ENCODER_MULTICORE_COUNT)
        self._upgrade()

    def _define(self, name):
        key = name.upper()
        ini_key = name.lower()
        definition = _config_definitions[key]
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

        for key in _config_definitions.keys():
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
        for item in newznab:
            self.EXTRA_NEWZNABS.append(item)

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
                'Track':        '$Track',
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
