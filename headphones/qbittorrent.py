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
import urllib2
import cookielib
import json
import os
import time

import headphones

from headphones import logger
from collections import namedtuple


class qbittorrentclient(object):

    TOKEN_REGEX = "<div id='token' style='display:none;'>([^<>]+)</div>"
    UTSetting = namedtuple("UTSetting", ["name", "int", "str", "access"])

    def __init__(self, base_url=None, username=None, password=None,):

        host = headphones.CONFIG.QBITTORRENT_HOST
        if not host.startswith('http'):
            host = 'http://' + host

        if host.endswith('/'):
            host = host[:-1]

        if host.endswith('/gui'):
            host = host[:-4]

        self.base_url = host
        self.username = headphones.CONFIG.QBITTORRENT_USERNAME
        self.password = headphones.CONFIG.QBITTORRENT_PASSWORD
        self.cookiejar = cookielib.CookieJar()
        self.opener = self._make_opener()
        self._get_sid(self.base_url, self.username, self.password)

    def _make_opener(self):
        # create opener with cookie handler to carry QBitTorrent SID cookie
        cookie_handler = urllib2.HTTPCookieProcessor(self.cookiejar)
        handlers = [cookie_handler]
        return urllib2.build_opener(*handlers)

    def _get_sid(self, base_url, username, password):
        # login so we can capture SID cookie
        login_data = urllib.urlencode({ 'username':username, 'password':password })
        try:
            self.opener.open(base_url+'/login',login_data)
        except urllib2.URLError as err:
            logger.debug('Error getting SID. qBittorrent responded with error: ' + str(err.reason))
            return
        for cookie in self.cookiejar:
                logger.debug('login cookie: ' + cookie.name + ', value: ' + cookie.value)
        return

    def _command(self, command, args=None, content_type=None, files=None):
        logger.debug('QBittorrent WebAPI Command: %s' % command)

        url = self.base_url + '/' + command

        data = None
        headers = dict()
        if files: #Use Multipart form
            data, headers = encode_multipart( args, files, '-------------------------acebdf13572468')
        else:
            if args:
                data = urllib.urlencode(args)
            if content_type:
                headers['Content-Type'] = content_type

        request = urllib2.Request(url,data,headers)
        try:
            response = self.opener.open(request)
            info = response.info()
            if info:
                if info.getheader('content-type'):
                    if info.getheader('content-type') == 'application/json':
                        resp = ''
                        for line in response:
                            resp = resp + line
                        return response.code, json.loads(resp)
            return response.code, None
        except urllib2.URLError as err:
            logger.debug('Failed URL: %s' % url)
            logger.debug('QBitTorrent webUI raised the following error: %s' % str(err))
            return None, None

    def _get_list(self, **args):
        return self._command('query/torrents', args)

    def _get_settings(self):
        status, value = self._command('query/preferences')
        logger.debug('get_settings() returned %d items' % len(value))
        return value

    def get_savepath(self, hash):
        logger.debug('qb.get_savepath(%s)' % hash)
        status, torrentList = self._get_list()
        for torrent in torrentList:
            if torrent['hash']:
                if torrent['hash'].upper() == hash.upper():
                    return torrent['save_path']
        return None

    def start(self, hash):
        logger.debug('qb.start(%s)' % hash)
        args = { 'hash':hash }
        return self._command('command/resume',args,'application/x-www-form-urlencoded')

    def pause(self, hash):
        logger.debug('qb.pause(%s)' % hash)
        args = { 'hash':hash }
        return self._command('command/pause',args,'application/x-www-form-urlencoded')

    def getfiles(self, hash):
        logger.debug('qb.getfiles(%s)' % hash)
        return self._command('query/propertiesFiles/'+hash)

    def getprops(self, hash):
        logger.debug('qb.getprops(%s)' % hash)
        return self._command('query/propertiesGeneral/'+hash)

    def setprio(self, hash, priority):
        logger.debug('qb.setprio(%s,%d)' % (hash, priority))
        args = { 'hash':hash, 'priority':priority }
        return self._command('command/setFilePrio', args,'application/x-www-form-urlencoded')

    def remove(self, hash, remove_data=False):
        logger.debug('qb.remove(%s,%s)' % (hash,remove_data))

        args = { 'hashes':hash }
        if remove_data:
            command = 'command/deletePerm'
        else:
            command = 'command/delete'
        return self._command(command, args, 'application/x-www-form-urlencoded')

def removeTorrent(hash, remove_data=False):
    logger.debug('removeTorrent(%s,%s)' % (hash,remove_data))

    qbclient = qbittorrentclient()
    status, torrentList = qbclient._get_list()
    for torrent in torrentList:
        if torrent['hash'].upper() == hash.upper():
            if torrent['state'] == 'uploading' or torrent['state'] == 'stalledUP':
                logger.info('%s has finished seeding, removing torrent and data' % torrent['name'])
                qbclient.remove(hash, remove_data)
                return True
            else:
                logger.info('%s has not finished seeding yet, torrent will not be removed, will try again on next run' % torrent['name'])
                return False
    return False

def addTorrent(link):
    logger.debug('addTorrent(%s)' % link)

    qbclient = qbittorrentclient()
    args = { 'urls':link, 'savepath':headphones.CONFIG.DOWNLOAD_TORRENT_DIR }
    if headphones.CONFIG.QBITTORRENT_LABEL:
        args['label'] = headphones.CONFIG.QBITTORRENT_LABEL
    return qbclient._command('command/download', args, 'application/x-www-form-urlencoded' )

def addFile(data):
    logger.debug('addFile(data)')

    qbclient = qbittorrentclient()
    files = {'torrents': { 'filename':'', 'content':data}}
    return qbclient._command('command/upload',filelist=files)

def getFolder(hash):
    logger.debug('getFolder(%s)' % hash)

    qbclient = qbittorrentclient()

    # Get Active Directory from settings
    settings = qbclient._get_settings()
    active_dir = settings['temp_path']

    if not active_dir:
        logger.error('Could not get "Keep incomplete torrents in:" directory from QBitTorrent settings, please ensure it is set')
        return None

    # Get Torrent Folder Name
    torrent_folder = qbclient.get_savepath(hash)

    # If there's no folder yet then it's probably a magnet, try until folder is populated
    if torrent_folder == active_dir or not torrent_folder:
        tries = 1
        while (torrent_folder == active_dir or torrent_folder is None) and tries <= 10:
            tries += 1
            time.sleep(6)
            torrent_folder = qbclient.get_savepath(hash)

    if torrent_folder == active_dir or not torrent_folder:
        torrent_folder = qbclient.get_savepath(hash)
        return torrent_folder
    else:
        if headphones.SYS_PLATFORM != "win32":
            torrent_folder = torrent_folder.replace('\\', '/')
        return os.path.basename(os.path.normpath(torrent_folder))

import mimetypes
import random
import string

_BOUNDARY_CHARS = string.digits + string.ascii_letters

def encode_multipart(fields, files, boundary=None):
    r"""Encode dict of form fields and dict of files as multipart/form-data.
    Return tuple of (body_string, headers_dict). Each value in files is a dict
    with required keys 'filename' and 'content', and optional 'mimetype' (if
    not specified, tries to guess mime type or uses 'application/octet-stream').

    >>> body, headers = encode_multipart({'FIELD': 'VALUE'},
    ...                                  {'FILE': {'filename': 'F.TXT', 'content': 'CONTENT'}},
    ...                                  boundary='BOUNDARY')
    >>> print('\n'.join(repr(l) for l in body.split('\r\n')))
    '--BOUNDARY'
    'Content-Disposition: form-data; name="FIELD"'
    ''
    'VALUE'
    '--BOUNDARY'
    'Content-Disposition: form-data; name="FILE"; filename="F.TXT"'
    'Content-Type: text/plain'
    ''
    'CONTENT'
    '--BOUNDARY--'
    ''
    >>> print(sorted(headers.items()))
    [('Content-Length', '193'), ('Content-Type', 'multipart/form-data; boundary=BOUNDARY')]
    >>> len(body)
    193
    """
    def escape_quote(s):
        return s.replace('"', '\\"')

    if boundary is None:
        boundary = ''.join(random.choice(_BOUNDARY_CHARS) for i in range(30))
    lines = []

    for name, value in fields.items():
        lines.extend((
            '--{0}'.format(boundary),
            'Content-Disposition: form-data; name="{0}"'.format(escape_quote(name)),
            '',
            str(value),
        ))

    for name, value in files.items():
        filename = value['filename']
        if 'mimetype' in value:
            mimetype = value['mimetype']
        else:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        lines.extend((
            '--{0}'.format(boundary),
            'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(
                    escape_quote(name), escape_quote(filename)),
            'Content-Type: {0}'.format(mimetype),
            '',
            value['content'],
        ))

    lines.extend((
        '--{0}--'.format(boundary),
        '',
    ))
    body = '\r\n'.join(lines)

    headers = {
        'Content-Type': 'multipart/form-data; boundary={0}'.format(boundary),
        'Content-Length': str(len(body)),
    }

    return (body, headers)

