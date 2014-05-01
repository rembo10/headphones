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

import re
import time
import base64
import headphones

import simplejson as json

from headphones import logger, notifiers, request

# This is just a simple script to send torrents to transmission. The
# intention is to turn this into a class where we can check the state
# of the download, set the download dir, etc.
# TODO: Store the session id so we don't need to make 2 calls
#       Store torrent id so we can check up on it

def addTorrent(link):
    method = 'torrent-add'
    arguments = {'filename': link, 'download-dir': headphones.DOWNLOAD_TORRENT_DIR}

    response = torrentAction(method,arguments)

    if not response:
        return False

    if response['result'] == 'success':
        if 'torrent-added' in response['arguments']:
            name = response['arguments']['torrent-added']['name']
            retid = response['arguments']['torrent-added']['id']
        elif 'torrent-duplicate' in response['arguments']:
            name = response['arguments']['torrent-duplicate']['name']
            retid = response['arguments']['torrent-duplicate']['id']
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
    arguments = { 'ids': torrentid, 'fields': ['name','percentDone']}

    response = torrentAction(method, arguments)
    percentdone = response['arguments']['torrents'][0]['percentDone']
    torrent_folder_name = response['arguments']['torrents'][0]['name']

    tries = 1

    while percentdone == 0  and tries <10:
        tries+=1
        time.sleep(5)
        response = torrentAction(method, arguments)
        percentdone = response['arguments']['torrents'][0]['percentDone']

    torrent_folder_name = response['arguments']['torrents'][0]['name']

    return torrent_folder_name

def torrentAction(method, arguments):

    host = headphones.UTORRENT_HOST
    username = headphones.UTORRENT_USERNAME
    password = headphones.UTORRENT_PASSWORD
    token = ''

    if not host.startswith('http'):
        host = 'http://' + host

    if host.endswith('/'):
    	host = host[:-1]

    if host.endswith('/gui'):
    	host = host + '/'
    else:
    	host = host + '/gui/'

    # Retrieve session id
    auth = (username, password) if username and password else None
    token_request = request.request_response(host + 'token.html')
    token = re.findall('<div.*?>(.*?)</', request.read())[0]

    data = { 'method': method, 'arguments': arguments }

    response = request.request_json(host, method="post", data=json.dumps(data), headers=headers, auth=auth)

    if not response:
        logger.error("Error sending torrent to Transmission")
        return

    return response
