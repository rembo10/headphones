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

import os
import urllib
import json
import urllib2
import cookielib
import patoolib

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
        return self._action(params, data)

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
        status, torrent = self.get_torrent(id)

        if status != 200:
            raise ValueError('Http error occured when getting torrent: ' + status)

        try:
            status, unrestricted_link = self._unrestrict_link(url)

            if status != 200:
                raise ValueError('Http error occured when unrestricting real-debrid link: ' + status)

            download_url = unrestricted_link['download']

            filename = torrent['original_filename']
            if unrestricted_link['mimeType'] == 'application/x-rar-compressed':
                filename += '.rar'

            logger.info('Downloading file from real-debrid: ' + download_url)
            urllib.urlretrieve(download_url, os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, filename))
            logger.info('Real-Debrid download complete!')

            if len(torrent['files']) == 1:
                filename = torrent['filename']
                return filename

            # Got rar file from real-debrid, so we'll unrar it first
            try:
                archivename = os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, filename)
                foldername = os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, torrent['original_filename'])
                logger.info('Extracting rar: ' + archivename)
                patoolib.extract_archive(archivename, outdir=foldername)
                os.remove(archivename)
                logger.info('Extract complete!')
                return foldername
            except Exception as err:
                logger.error('Extracting Real-Debrid rar failed: ' + str(err))
                raise ValueError('Could not extract rar file, do you have patool set up properly?')

        except urllib2.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('Real-Debrid raised the following error: ' + str(err))

    def _action(self, action, body=None, content_type=None, method=None):

        url = self.base_url + action + '?auth_token=' + self.apikey
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

            if response.code == 201 or response.code == 204:
                return response.code, None

            return response.code, json.loads(response.read())
        except urllib2.HTTPError as err:
            logger.debug('URL: ' + str(url))
            logger.debug('Real-Debrid raised the following error: ' + str(err))


def removeTorrent(hash):
    RealDebridClient = realdebridclient()
    status, torrents = RealDebridClient.list()

    for torrent in torrents:
        if torrent['hash'].upper() == hash.upper():
            status, data = RealDebridClient.remove(torrent['id'])
            if status == 204:
                return True

    return False


def addTorrent(link):
    RealDebridClient = realdebridclient()
    status, data = RealDebridClient.add_url(link)

    if status != 201:
        raise ValueError('Http error occured when adding magnet: ' + status)


def selectFiles(hash):
    RealDebridClient = realdebridclient()
    status, torrents = RealDebridClient.list()

    if status != 200:
        raise ValueError('Http error occured when getting torrents: ' + status)

    for torrent in torrents:
        if torrent['hash'].upper() == hash.upper():
            status, data = RealDebridClient.select_files(torrent['id'])

            if status != 204:
                raise ValueError('Http error occured when selecting files: ' + status)


def getFolder(hash):
    RealDebridClient = realdebridclient()
    status, torrents = RealDebridClient.list()

    if status != 200:
        raise ValueError('Http error occured when getting folder: ' + status)

    for torrent in torrents:
        if torrent['hash'].upper() == hash.upper():

            status, torrent_info = RealDebridClient.get_torrent(torrent['id'])
            if status != 200:
                return None

            if torrent_info['filename'] != "" or len(torrent_info['files']) == 1:
                return headphones.CONFIG.DOWNLOAD_TORRENT_DIR

            directory = os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, torrent_info['original_filename'])
            if not os.path.exists(directory):
                os.makedirs(directory)

            return torrent_info['original_filename']

    return None


def checkStatus(hash):
    RealDebridClient = realdebridclient()
    status, torrents = RealDebridClient.list()

    if status != 200:
        raise ValueError('Http error occured when getting folder: ' + status)

    for torrent in torrents:
        if torrent['hash'].upper() == hash.upper():
            if torrent['progress'] == 100:
                RealDebridClient.download_and_extract(torrent['links'][0], torrent['id'])
                return True
            elif torrent['status'] == "waiting_files_selection":
                RealDebridClient.select_files(torrent['id'])
                return False
            elif torrent['status'] == "error":
                logger.error('Torrent status is error, removing...')
                foldername = getFolder(hash)
                directory = os.path.join(headphones.CONFIG.DOWNLOAD_TORRENT_DIR, foldername)
                if os.path.exists(directory):
                    os.removedirs(directory)
                RealDebridClient.remove(torrent['id'])
                raise LookupError()
            else:
                return False

    logger.info('Hash ' + hash.upper() + ' not found on Real-Debrid')
    raise LookupError()
