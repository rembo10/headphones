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
# Author: echel0n <sickrage.tv@gmail.com>
# URL: http://www.github.com/sickragetv/sickrage/
#
# Adapted for Headphones by <noamgit@gmail.com>
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from headphones import logger, request

import time
import re
import os
import json
import base64
import urlparse
import headphones
import requests

from base64 import b64encode

delugeweb_auth = {}
delugeweb_url = ''

def add_torrent(link, data=None):
    try:
        result = {}
        retid = False
        if link.endswith('.torrent') or data: 
        # .torrent? for torcache links
        # or '.torrent?' in link 
            if data:
                metainfo = str(base64.b64encode(data))
            # before I found out HP handles the downloads
            #elif link.startswith('http://') or link.startswith('https://'):
            #    user_agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.1546.111 Safari/582.36'
            #    headers = { 'User-Agent': user_agent } 
            #    torrentfile = ''
            #    r = requests.get(link, headers=headers)
            #    if r.status_code == 200:
            #        for chunk in r.iter_content(chunk_size=1024): 
            #            if chunk: # filter out keep-alive new chunks
            #                torrent_file = torrentfile + chunk
            #    metainfo = str(base64.b64encode(torrentfile.decode('utf-8')))
            else:
                with open(link, 'rb') as f:
                    metainfo = str(base64.b64encode(f.read()))
            # Extract torrent name from .torrent
            name_length = int( re.findall( 'name([0-9]*)\:.*?\:', base64.b64encode(metainfo) )[0] )
            name = re.findall('name[0-9]*\:(.*?)\:', base64.b64encode(metainfo) )[0][:size]
            result = {
                'type'      : 'torrent',
                'name'      : name,
                'content'   : metainfo,
                }
            retid = add_torrent_file(result)

        elif link.startswith('magnet:'):
            result = {
                'type'  : 'magnet',
                'url'   : link,
                }
            retid = add_torrent_uri(result)
        else:
            logger.error('Deluge: Unknown file type - ' + str(link))

        if retid:
            logger.info(u"Torrent sent to Deluge successfully")
            return retid
        else:
            logger.info('Deluge returned status %s' % retid)
            return False

    except Exception, e:
        logger.error( str(e) )

def get_torrent_folder(result):

    if not any(delugeweb_auth):
        get_auth()

    post_data = json.dumps({
          "method": "web.get_torrent_status",
          "params": [
            result['hash'],
            [ "total_done" ]
          ],
          "id": 22
        })

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
    result['total_done'] = json.loads(response.text)['result']['total_done']

    tries = 0
    while result['total_done'] == 0 and tries < 10:
        tries += 1
        time.sleep(5)
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)
        result['total_done'] = json.loads(response.text)['result']['total_done']

    post_data = json.dumps({
          "method": "web.get_torrent_status",
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
          "id": 23
        })

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

    result['save_path'] = json.loads(response.text)['result']['save_path']
    result['name'] = json.loads(response.text)['result']['name']

    return json.loads(response.text)['result']['name']

def remove_torrent(torrentid, remove_data=False):
    '''
    todo
    '''
    return

def get_auth():

    global delugeweb_auth, delugeweb_url 
    delugeweb_auth = {}

    delugeweb_host = headphones.CONFIG.DELUGE_HOST
    delugeweb_username = headphones.CONFIG.DELUGE_USERNAME
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
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth )
        #                                  , verify=TORRENT_VERIFY_CERT)
    except Exception:
        return None

    auth = json.loads(response.text)["result"]
    delugeweb_auth = response.cookies

    post_data = json.dumps({"method": "web.connected",
                            "params": [],
                            "id": 10})
    try:
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth )
        #                                  , verify=TORRENT_VERIFY_CERT)
    except Exception:
        return None

    connected = json.loads(response.text)['result']

    if not connected:
        post_data = json.dumps({"method": "web.get_delugeweb_hosts",
                                "params": [],
                                "id": 11})
        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth )
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
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth )
            #                                  , verify=TORRENT_VERIFY_CERT)
        except Exception:
            return None

        post_data = json.dumps({"method": "web.connected",
                                "params": [],
                                "id": 10})

        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth )
            #                                  , verify=TORRENT_VERIFY_CERT)
        except Exception:
            return None

        connected = json.loads(response.text)['result']

        if not connected:
            logger.error('Deluge: WebUI could not connect to daemon')
            return None

    return auth

def add_torrent_uri(result):

    if not any(delugeweb_auth):
        get_auth()

    post_data = json.dumps({"method": "core.add_torrent_magnet",
                            "params": [result['url'], {}],
                            "id": 2})

    '''
    # This method doesn't return hash
    post_data = json.dumps({
          "method": "web.add_torrents",
          "params": [
            [
              {
                "path": result['url'],
                "options": {
                  "add_paused": headphones.CONFIG.DELUGE_PAUSED,
                  #"download_location": headphones.CONFIG.DOWNLOAD_TORRENT_DIR,
                  #"move_completed": true,
                  #"move_completed_path": headphones.CONFIG.DELUGE_DONE_DIRECTORY,
                }
              }
            ]
          ],
          "id": 2
        })
    '''

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

    result['hash'] = json.loads(response.text)['result']

    return json.loads(response.text)['result']

def add_torrent_file(result):

    if not any(delugeweb_auth):
        get_auth()

    post_data = json.dumps({"method": "core.add_torrent_file",
                            "params": [result['name'] + '.torrent', b64encode(result['content']), {}],
                            "id": 2})

    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

    result['hash'] = json.loads(response.text)['result']

    return json.loads(response.text)['result']

def set_torrent_label(result):

    label = headphones.CONFIG.DELUGE_LABEL

    if not any(delugeweb_auth):
        get_auth()

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

def set_torrent_ratio(result):

    if not any(delugeweb_auth):
        get_auth()

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

def set_torrent_path(result):

    if not any(delugeweb_auth):
        get_auth()

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

def set_torrent_pause(result):
    
    if not any(delugeweb_auth):
        get_auth()

    if headphones.CONFIG.DELUGE_PAUSED:
        post_data = json.dumps({"method": "core.pause_torrent",
                                "params": [[ result['hash'] ]],
                                "id": 9})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth)

        return not json.loads(response.text)['error']

    return True

