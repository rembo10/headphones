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

# Parts of this file are a part of SickRage.
# Author: Mr_Orange <mr_orange@hotmail.it>
# URL: http://code.google.com/p/sickbeard/
# Adapted for Headphones by <noamgit@gmail.com>
# URL: https://github.com/noam09
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from headphones import logger
#from headphones import request

import time
import re
import os
import json
import headphones
import requests
from base64 import b64encode
# remove later
import sys

delugeweb_auth = {}
delugeweb_url = ''

def addTorrent(link, data=None):
    try:
        result = {}
        retid = False
        if link.endswith('.torrent') or data:
            if data:
                logger.debug('Deluge: Getting .torrent data')
                torrentfile = data
            else:
                logger.debug('Deluge: Getting .torrent file')
                with open(link, 'rb') as f:
                    torrentfile = f.read()
            # Extract torrent name from .torrent
            try:
                logger.debug('Deluge: Getting torrent name length')
                name_length = int(re.findall('name([0-9]*)\:.*?\:', torrentfile)[0])
                logger.debug('Deluge: Getting torrent name')
                name = re.findall('name[0-9]*\:(.*?)\:', torrentfile)[0][:name_length]
            except:
                logger.debug('Deluge: Could not get torrent name, getting file name')
                # get last part of link/path (name only)
                name = link.split('\\')[-1].split('/')[-1]
                # remove '.torrent' suffix
                if name[-len('.torrent'):] == '.torrent':
                    name = name[:-len('.torrent')]
            logger.debug('Deluge: Sending Deluge torrent with name ' + name)
            result = {'type': 'torrent',
                        'name': name,
                        'content': torrentfile}
            retid = _add_torrent_file(result)

        elif link.startswith('http://') or link.startswith('https://'):
            logger.debug('Deluge: Got a URL: ' + link)
            user_agent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'
            headers = {'User-Agent': user_agent}
            torrentfile = ''
            logger.debug('Deluge: Trying to download (GET)')
            r = requests.get(link, headers=headers)
            if r.status_code == 200:
                logger.debug('Deluge: 200 OK')
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: # filter out keep-alive new chunks
                        torrentfile = torrentfile + chunk
            else:
                logger.debug('Deluge: Trying to GET ' + link + ' returned status ' + r.status_code)
                return False
            if 'announce' not in torrentfile[:40]:
                logger.debug('Deluge: Contents of ' + link + ' doesn\'t look like a torrent file')
                return False
            # Extract torrent name from .torrent
            try:
                logger.debug('Deluge: Getting torrent name length')
                name_length = int(re.findall('name([0-9]*)\:.*?\:', torrentfile)[0])
                logger.debug('Deluge: Getting torrent name')
                name = re.findall('name[0-9]*\:(.*?)\:', torrentfile)[0][:name_length]
            except:
                logger.debug('Deluge: Could not get torrent name, getting file name')
                # get last part of link/path (name only)
                name = link.split('\\')[-1].split('/')[-1]
                # remove '.torrent' suffix
                if name[-len('.torrent'):] == '.torrent':
                    name = name[:-len('.torrent')]
            logger.debug('Deluge: Sending Deluge torrent with name ' + name)
            result = {'type': 'torrent',
                        'name': name,
                        'content': torrentfile}
            retid = _add_torrent_file(result)

        elif link.startswith('magnet:'):
            logger.debug('Deluge: Got a magnet link: ' + link)
            result = {'type': 'magnet',
                        'url': link}
            retid = _add_torrent_uri(result)
        else:
            logger.error('Deluge: Unknown file type - ' + str(link))

        if retid:
            logger.info(u"Torrent sent to Deluge successfully")
            return retid
        else:
            logger.info('Deluge returned status %s' % retid)
            return False

    except Exception, e:
        # REMOVE LATER - FOR DEBUGGING
        super_debug = True
        if super_debug:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error('SUPER_DEBUG: ' + str(e) + ' -- ' + '; '.join([exc_type, fname, exc_tb.tb_lineno]))
        ######
        logger.error(str(e))

def getTorrentFolder(result):

    if not any(delugeweb_auth):
        _get_auth()

    post_data = json.dumps({"method": "web.get_torrent_status",
                            "params": [
                                result['hash'],
                                ["total_done"]
                            ],
                            "id": 22})

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
    result['total_done'] = json.loads(response.text)['result']['total_done']

    tries = 0
    while result['total_done'] == 0 and tries < 10:
        tries += 1
        time.sleep(5)
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        result['total_done'] = json.loads(response.text)['result']['total_done']

    post_data = json.dumps({"method": "web.get_torrent_status",
                            "params": [
                                result['hash'],
                                [
                                    "name",
                                    "save_path",
                                    "total_size",
                                    "num_files",
                                    "message",
                                    "tracker",
                                    "comment"
                                ]
                            ],
                            "id": 23})

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

    result['save_path'] = json.loads(response.text)['result']['save_path']
    result['name'] = json.loads(response.text)['result']['name']

    return json.loads(response.text)['result']['name']

def removeTorrent(torrentid, remove_data=False):

    if not any(delugeweb_auth):
        _get_auth()

    result = False
    post_data = json.dumps({"method": "core.remove_torrent",
                            "params": [
                                torrentid,
                                remove_data
                                ],
                            "id": 25})
    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
    result = json.loads(response.text)['result']

    return result

def _get_auth():
    logger.debug('Deluge: Authenticating...')
    global delugeweb_auth, delugeweb_url
    delugeweb_auth = {}

    delugeweb_host = headphones.CONFIG.DELUGE_HOST
    # delugeweb_username = headphones.CONFIG.DELUGE_USERNAME
    delugeweb_password = headphones.CONFIG.DELUGE_PASSWORD

    if not delugeweb_host.startswith('http'):
        delugeweb_host = 'http://' + delugeweb_host

    if delugeweb_host.endswith('/'):
        delugeweb_host = delugeweb_host[:-1]

    delugeweb_url = delugeweb_host + '/json'

    post_data = json.dumps({"method": "auth.login",
                            "params": [delugeweb_password],
                            "id": 1})
    try:
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        #                                  , verify=TORRENT_VERIFY_CERT)
    except Exception:
        return None

    auth = json.loads(response.text)["result"]
    delugeweb_auth = response.cookies

    post_data = json.dumps({"method": "web.connected",
                            "params": [],
                            "id": 10})
    try:
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        #                                  , verify=TORRENT_VERIFY_CERT)
    except Exception:
        return None

    connected = json.loads(response.text)['result']

    if not connected:
        post_data = json.dumps({"method": "web.get_hosts",
                                "params": [],
                                "id": 11})
        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
            #                                  , verify=TORRENT_VERIFY_CERT)
        except Exception:
            return None

        delugeweb_hosts = json.loads(response.text)['result']
        if len(delugeweb_hosts) == 0:
            logger.error('Deluge: WebUI does not contain daemons')
            return None

        post_data = json.dumps({"method": "web.connect",
                                "params": [delugeweb_hosts[0][0]],
                                "id": 11})

        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
            #                                  , verify=TORRENT_VERIFY_CERT)
        except Exception:
            return None

        post_data = json.dumps({"method": "web.connected",
                                "params": [],
                                "id": 10})

        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
            #                                  , verify=TORRENT_VERIFY_CERT)
        except Exception:
            return None

        connected = json.loads(response.text)['result']

        if not connected:
            logger.error('Deluge: WebUI could not connect to daemon')
            return None

    return auth

def _add_torrent_uri(result):
    logger.debug('Deluge: Adding URI')
    if not any(delugeweb_auth):
        _get_auth()

    post_data = json.dumps({"method": "core.add_torrent_magnet",
                            "params": [result['url'], {}],
                            "id": 2})
    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
    result['hash'] = json.loads(response.text)['result']
    logger.debug('Deluge: Response was ' + json.loads(response.text)['result'])
    return json.loads(response.text)['result']

def _add_torrent_file(result):
    logger.debug('Deluge: Adding file')
    if not any(delugeweb_auth):
        _get_auth()

    # content is torrent file contents that needs to be encoded to base64
    post_data = json.dumps({"method": "core.add_torrent_file",
                            "params": [result['name'] + '.torrent', b64encode(result['content']), {}],
                            "id": 2})
    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
    result['hash'] = json.loads(response.text)['result']
    logger.debug('Deluge: Response was ' + json.loads(response.text)['result'])
    return json.loads(response.text)['result']

def setTorrentLabel(result):
    logger.debug('Deluge: Setting label')
    label = headphones.CONFIG.DELUGE_LABEL

    if not any(delugeweb_auth):
        _get_auth()

    if ' ' in label:
        logger.error('Deluge: Invalid label. Label must not contain a space - replacing with underscores')
        label = label.replace(' ', '_')
    if label:
        # check if label already exists and create it if not
        post_data = json.dumps({"method": 'label.get_labels',
                                "params": [],
                                "id": 3})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        labels = json.loads(response.text)['result']

        if labels is not None:
            if label not in labels:
                logger.debug('Deluge: ' + label + " label does not exist in Deluge we must add it")
                post_data = json.dumps({"method": 'label.add',
                                        "params": [label],
                                        "id": 4})
                response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
                logger.debug('Deluge: ' + label + " label added to Deluge")

            # add label to torrent
            post_data = json.dumps({"method": 'label.set_torrent',
                                    "params": [result['hash'], label],
                                    "id": 5})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
            logger.debug('Deluge: ' + label + " label added to torrent")
        else:
            logger.debug('Deluge: ' + "label plugin not detected")
            return False

    return not json.loads(response.text)['error']

def setSeedRatio(result):
    logger.debug('Deluge: Setting seed ratio')
    if not any(delugeweb_auth):
        _get_auth()

    ratio = None
    if result['ratio']:
        ratio = result['ratio']

    if ratio:
        post_data = json.dumps({"method": "core.set_torrent_stop_at_ratio",
                                "params": [result['hash'], True],
                                "id": 5})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        post_data = json.dumps({"method": "core.set_torrent_stop_ratio",
                                "params": [result['hash'], float(ratio)],
                                "id": 6})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

        return not json.loads(response.text)['error']

    return True

def setTorrentPath(result):
    logger.debug('Deluge: Setting download path')
    if not any(delugeweb_auth):
        _get_auth()

    if headphones.CONFIG.DELUGE_DONE_DIRECTORY or headphones.CONFIG.DOWNLOAD_TORRENT_DIR:
        post_data = json.dumps({"method": "core.set_torrent_move_completed",
                                "params": [result['hash'], True],
                                "id": 7})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

        if headphones.CONFIG.DELUGE_DONE_DIRECTORY:
            move_to = headphones.CONFIG.DELUGE_DONE_DIRECTORY
        else:
            move_to = headphones.CONFIG.DOWNLOAD_TORRENT_DIR

        if not os.path.exists(move_to):
            logger.debug("Deluge: " + move_to + " directory doesn't exist, let's create it")
            os.makedirs(move_to)
        post_data = json.dumps({"method": "core.set_torrent_move_completed_path",
                                "params": [result['hash'], move_to],
                                "id": 8})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

        return not json.loads(response.text)['error']

    return True

def setTorrentPause(result):
    logger.debug('Deluge: Pausing torrent')
    if not any(delugeweb_auth):
        _get_auth()

    if headphones.CONFIG.DELUGE_PAUSED:
        post_data = json.dumps({"method": "core.pause_torrent",
                                "params": [[result['hash']]],
                                "id": 9})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

        return not json.loads(response.text)['error']

    return True
