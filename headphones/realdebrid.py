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

import urllib
import json
import time
from collections import namedtuple
import urllib2
import urlparse
import cookielib
from pyunpack import Archive

import re
import os
import headphones
from headphones import logger


class realdebridclient(object):

    def __init__(self, base_url=None, username=None, password=None, ):

        host = "https://api.real-debrid.com/rest/1.0"

        self.base_url = host
        self.apikey = headphones.CONFIG.REALDEBRID_APIKEY
        self.opener = self._make_opener()

    def _make_opener(self):
        opener = urllib2.build_opener(urllib2.HTTPSHandler)
        return opener

    def list(self):
        params = '/torrents'
        return self._action(params)

    def add_url(self, url):
        # must be magnet
        params = '/torrents/addMagnet'
        data = {
            'magnet': url
        }

        data = urllib.urlencode(data)
        return self._action(params, data, 'application/x-www-form-urlencoded')

    def get_torrent(self, id):
        params = '/torrents/info/' + id
        return self._action(params)

    def select_files(self, id):
        params = '/torrents/selectFiles/' + id
        data = {
            'files': 'all'
        }

        data = urllib.urlencode(data)
        return self._action(params)

    def remove(self, id):
        params = '/torrents/delete/' + id
        return self._action(params, None, None, 'DELETE')

    def _unrestrict_link(self, url):
        params = '/unrestrict/link'
        data = {
            'link': url
        }

        data = urllib.urlencode(data)
        return self._action(params, data)

    def download_and_extract(self, url, id):
        """Need to get torrent, determine # of files, then download accordingly"""
        torrent = self.get_torrent(id)
        filename = id + '.rar'
        israr = true

        if len(torrent.files) == 1:
            filename = torrent.files[0].path[1:]
            israr = false

        try:
            urllib.urlretrieve(url, os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, filename))

            if israr:
                # Got rar file from real-debrid, so we'll unrar it first
                try:
                    Archive(
                        os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, filename)).extractall(
                            os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, torrent.original_filename))
                except Exception as err:
                    logger.debug('Extracting Real-Debrid rar failed: ' + str(err))

            return filename
        except urllib2.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('Real-Debrid raised the following error: ' + str(err))

    def _action(self, action, body=None, content_type=None, method=None):

        url = self.base_url + action + '?auth_token=' + urllib.urlencode(self.apikey)
        request = urllib2.Request(url)

        if body:
            request.add_data(body)
            request.add_header('Content-length', len(body))
        if content_type:
            request.add_header('Content-type', content_type)
        if method:
            request.get_method = lambda: method

        try:
            response = self.opener.open(request)
            return response.code, json.loads(response.read())
        except urllib2.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('Real-Debrid raised the following error: ' + str(err))


def removeTorrent(hash):
    RealDebridClient = realdebridclient()
    torrents = RealDebridClient.list()

    for torrent in torrents:
        if torrent.hash.upper() == hash.upper():
            status, data = RealDebridClient.remove(torrent.id)
            if status == 204:
                return True

    return False

def addTorrent(link):
    RealDebridClient = realdebridclient()
    RealDebridClient.add_url(link)

def getFolder(hash, check_progress=False):
    RealDebridClient = realdebridclient()
    status, torrents = RealDebridClient.list()

    if status != 200:
        return None

    for torrent in torrents:
        if torrent.hash.upper() == hash.upper():
            single = False
            if torrent.filename != "":
                single = True

            if check_progress and torrent.progress == 100:
                return RealDebridClient.download_and_extract(torrent.links[0], torrent.id), single

            status, torrent_info = RealDebridClient.get_torrent(torrent.id)
            if status != 200:
                return None

            return os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, torrent_info.original_filename), single

    return None
