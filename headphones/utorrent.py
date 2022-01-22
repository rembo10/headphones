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

import urllib.request
import urllib.parse
import urllib.error
import json
import time
from collections import namedtuple
import urllib.request
import urllib.error
import urllib.parse
import urllib.parse
import http.cookiejar

import re
import os
import headphones
from headphones import logger


class utorrentclient(object):
    TOKEN_REGEX = "<div id='token' style='display:none;'>([^<>]+)</div>"
    UTSetting = namedtuple("UTSetting", ["name", "int", "str", "access"])

    def __init__(self, base_url=None, username=None, password=None, ):

        host = headphones.CONFIG.UTORRENT_HOST
        if not host.startswith('http'):
            host = 'http://' + host

        if host.endswith('/'):
            host = host[:-1]

        if host.endswith('/gui'):
            host = host[:-4]

        self.base_url = host
        self.username = headphones.CONFIG.UTORRENT_USERNAME
        self.password = headphones.CONFIG.UTORRENT_PASSWORD
        self.opener = self._make_opener('uTorrent', self.base_url, self.username, self.password)
        self.token = self._get_token()
        # TODO refresh token, when necessary

    def _make_opener(self, realm, base_url, username, password):
        """uTorrent API need HTTP Basic Auth and cookie support for token verify."""
        auth = urllib.request.HTTPBasicAuthHandler()
        auth.add_password(realm=realm, uri=base_url, user=username, passwd=password)
        opener = urllib.request.build_opener(auth)
        urllib.request.install_opener(opener)

        cookie_jar = http.cookiejar.CookieJar()
        cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)

        handlers = [auth, cookie_handler]
        opener = urllib.request.build_opener(*handlers)
        return opener

    def _get_token(self):
        url = urllib.parse.urljoin(self.base_url, 'gui/token.html')
        try:
            response = self.opener.open(url)
        except urllib.error.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('Error getting Token. uTorrent responded with error: ' + str(err))
            return
        match = re.search(utorrentclient.TOKEN_REGEX, response.read())
        return match.group(1)

    def list(self, **kwargs):
        params = [('list', '1')]
        params += list(kwargs.items())
        return self._action(params)

    def add_url(self, url):
        # can receive magnet or normal .torrent link
        params = [('action', 'add-url'), ('s', url)]
        return self._action(params)

    def start(self, *hashes):
        params = [('action', 'start'), ]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)

    def stop(self, *hashes):
        params = [('action', 'stop'), ]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)

    def pause(self, *hashes):
        params = [('action', 'pause'), ]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)

    def forcestart(self, *hashes):
        params = [('action', 'forcestart'), ]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)

    def getfiles(self, hash):
        params = [('action', 'getfiles'), ('hash', hash)]
        return self._action(params)

    def getprops(self, hash):
        params = [('action', 'getprops'), ('hash', hash)]
        return self._action(params)

    def setprops(self, hash, s, v):
        params = [('action', 'setprops'), ('hash', hash), ("s", s), ("v", v)]
        return self._action(params)

    def setprio(self, hash, priority, *files):
        params = [('action', 'setprio'), ('hash', hash), ('p', str(priority))]
        for file_index in files:
            params.append(('f', str(file_index)))

        return self._action(params)

    def get_settings(self, key=None):
        params = [('action', 'getsettings'), ]
        status, value = self._action(params)
        settings = {}
        for args in value['settings']:
            settings[args[0]] = self.UTSetting(*args)
        if key:
            return settings[key]
        return settings

    def remove(self, hash, remove_data=False):
        if remove_data:
            params = [('action', 'removedata'), ('hash', hash)]
        else:
            params = [('action', 'remove'), ('hash', hash)]
        return self._action(params)

    def _action(self, params, body=None, content_type=None):

        if not self.token:
            return

        url = self.base_url + '/gui/' + '?token=' + self.token + '&' + urllib.parse.urlencode(params)
        request = urllib.request.Request(url)

        if body:
            request.add_data(body)
            request.add_header('Content-length', len(body))
        if content_type:
            request.add_header('Content-type', content_type)

        try:
            response = self.opener.open(request)
            return response.code, json.loads(response.read())
        except urllib.error.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('uTorrent webUI raised the following error: ' + str(err))


def labelTorrent(hash):
    label = headphones.CONFIG.UTORRENT_LABEL
    uTorrentClient = utorrentclient()
    if label:
        uTorrentClient.setprops(hash, 'label', label)


def removeTorrent(hash, remove_data=False):
    uTorrentClient = utorrentclient()
    status, torrentList = uTorrentClient.list()
    torrents = torrentList['torrents']
    for torrent in torrents:
        if torrent[0].upper() == hash.upper():
            if torrent[21] == 'Finished':
                logger.info('%s has finished seeding, removing torrent and data' % torrent[2])
                uTorrentClient.remove(hash, remove_data)
                return True
            else:
                logger.info(
                    '%s has not finished seeding yet, torrent will not be removed, will try again on next run' %
                    torrent[2])
                return False
    return False


def setSeedRatio(hash, ratio):
    uTorrentClient = utorrentclient()
    uTorrentClient.setprops(hash, 'seed_override', '1')
    if ratio != 0:
        uTorrentClient.setprops(hash, 'seed_ratio', ratio * 10)
    else:
        # TODO passing -1 should be unlimited
        uTorrentClient.setprops(hash, 'seed_ratio', -10)


def dirTorrent(hash, cacheid=None, return_name=None):
    uTorrentClient = utorrentclient()

    if not cacheid:
        status, torrentList = uTorrentClient.list()
    else:
        params = [('list', '1'), ('cid', cacheid)]
        status, torrentList = uTorrentClient._action(params)

    if 'torrentp' in torrentList:
        torrents = torrentList['torrentp']
    else:
        torrents = torrentList['torrents']

    cacheid = torrentList['torrentc']

    for torrent in torrents:
        if torrent[0].upper() == hash.upper():
            if not return_name:
                return torrent[26], cacheid
            else:
                return torrent[2], cacheid

    return None, None


def addTorrent(link):
    uTorrentClient = utorrentclient()
    uTorrentClient.add_url(link)


def getFolder(hash):

    # Get Active Directory from settings
    active_dir, completed_dir = getSettingsDirectories()

    if not active_dir:
        logger.error(
            'Could not get "Put new downloads in:" directory from uTorrent settings, please ensure it is set')
        return None

    # Get Torrent Folder Name
    torrent_folder, cacheid = dirTorrent(hash)

    # If there's no folder yet then it's probably a magnet, try until folder is populated
    if torrent_folder == active_dir or not torrent_folder:
        tries = 1
        while (torrent_folder == active_dir or torrent_folder is None) and tries <= 10:
            tries += 1
            time.sleep(6)
            torrent_folder, cacheid = dirTorrent(hash, cacheid)

    if torrent_folder == active_dir or not torrent_folder:
        torrent_folder, cacheid = dirTorrent(hash, cacheid, return_name=True)
        return torrent_folder
    else:
        if headphones.SYS_PLATFORM != "win32":
            torrent_folder = torrent_folder.replace('\\', '/')
        return os.path.basename(os.path.normpath(torrent_folder))


def getSettingsDirectories():
    uTorrentClient = utorrentclient()
    settings = uTorrentClient.get_settings()
    active = None
    completed = None
    if 'dir_active_download' in settings:
        active = settings['dir_active_download'][2]
    if 'dir_completed_download' in settings:
        completed = settings['dir_completed_download'][2]
    return active, completed
