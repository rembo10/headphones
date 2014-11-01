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

from headphones import logger, notifiers, request

import re
import time
import json
import base64
import headphones

# This is just a simple script to send torrents to transmission. The
# intention is to turn this into a class where we can check the state
# of the download, set the download dir, etc.
# TODO: Store the session id so we don't need to make 2 calls
#       Store torrent id so we can check up on it


def addTorrent(link):
    method = 'torrent-add'

    if link.endswith('.torrent'):
        with open(link, 'rb') as f:
            metainfo = str(base64.b64encode(f.read()))
        arguments = {'metainfo': metainfo, 'download-dir': headphones.CONFIG.DOWNLOAD_TORRENT_DIR}
    else:
        arguments = {'filename': link, 'download-dir': headphones.CONFIG.DOWNLOAD_TORRENT_DIR}

    response = torrentAction(method, arguments)

    if not response:
        return False

    if response['result'] == 'success':
        if 'torrent-added' in response['arguments']:
            name = response['arguments']['torrent-added']['name']
            retid = response['arguments']['torrent-added']['hashString']
        elif 'torrent-duplicate' in response['arguments']:
            name = response['arguments']['torrent-duplicate']['name']
            retid = response['arguments']['torrent-duplicate']['hashString']
        else:
            name = link
            retid = False

        logger.info(u"Torrent sent to Transmission successfully")
        return retid

    else:
        logger.info('Transmission returned status %s' % response['result'])
        return False


def getTorrentFolder(torrentid):
    method = 'torrent-get'
    arguments = {'ids': torrentid, 'fields': ['name', 'percentDone']}

    response = torrentAction(method, arguments)
    percentdone = response['arguments']['torrents'][0]['percentDone']
    torrent_folder_name = response['arguments']['torrents'][0]['name']

    tries = 1

    while percentdone == 0 and tries < 10:
        tries += 1
        time.sleep(5)
        response = torrentAction(method, arguments)
        percentdone = response['arguments']['torrents'][0]['percentDone']

    torrent_folder_name = response['arguments']['torrents'][0]['name']

    return torrent_folder_name


def setSeedRatio(torrentid, ratio):
    method = 'torrent-set'
    if ratio != 0:
        arguments = {'seedRatioLimit': ratio, 'seedRatioMode': 1, 'ids': torrentid}
    else:
        arguments = {'seedRatioMode': 2, 'ids': torrentid}

    response = torrentAction(method, arguments)
    if not response:
        return False


def removeTorrent(torrentid, remove_data=False):

    method = 'torrent-get'
    arguments = {'ids': torrentid, 'fields': ['isFinished', 'name']}

    response = torrentAction(method, arguments)
    if not response:
        return False

    try:
        finished = response['arguments']['torrents'][0]['isFinished']
        name = response['arguments']['torrents'][0]['name']

        if finished:
            logger.info('%s has finished seeding, removing torrent and data' % name)
            method = 'torrent-remove'
            if remove_data:
                arguments = {'delete-local-data': True, 'ids': torrentid}
            else:
                arguments = {'ids': torrentid}
            response = torrentAction(method, arguments)
            return True
        else:
            logger.info('%s has not finished seeding yet, torrent will not be removed, will try again on next run' % name)
    except:
        return False

    return False


def torrentAction(method, arguments):

    host = headphones.CONFIG.TRANSMISSION_HOST
    username = headphones.CONFIG.TRANSMISSION_USERNAME
    password = headphones.CONFIG.TRANSMISSION_PASSWORD
    sessionid = None

    if not host.startswith('http'):
        host = 'http://' + host

    if host.endswith('/'):
        host = host[:-1]

    # Either the host ends with a port, or some directory, or rpc
    # If it ends with /rpc we don't have to do anything
    # If it ends with a port we add /transmission/rpc
    # anything else we just add rpc
    if not host.endswith('/rpc'):
        # Check if it ends in a port number
        i = host.rfind(':')
        if i >= 0:
            possible_port = host[i+1:]
            try:
                port = int(possible_port)
                host = host + "/transmission/rpc"
            except ValueError:
                host = host + "/rpc"
        else:
            logger.error('Transmission port missing')
            return

    # Retrieve session id
    auth = (username, password) if username and password else None

    response = request.request_response(host, auth=auth, whitelist_status_code=[401, 409])

    if response is None:
        logger.error("Error gettings Transmission session ID")
        return

    # Parse response
    if response.status_code == 401:
        if auth:
            logger.error("Username and/or password not accepted by Transmission")
        else:
            logger.error("Transmission authorization required")

        return
    elif response.status_code == 409:
        sessionid = response.headers['x-transmission-session-id']

    if not sessionid:
        logger.error("Error getting Session ID from Transmission")
        return

    # Prepare next request
    headers = {'x-transmission-session-id': sessionid}
    data = {'method': method, 'arguments': arguments}

    response = request.request_json(host, method="post", data=json.dumps(data), headers=headers, auth=auth)

    if not response:
        logger.error("Error sending torrent to Transmission")
        return

    return response
