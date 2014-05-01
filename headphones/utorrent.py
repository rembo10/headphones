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
import os
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


def addTorrent(link, title):

    host = headphones.UTORRENT_HOST
    username = headphones.UTORRENT_USERNAME
    password = headphones.UTORRENT_PASSWORD
    label = headphones.UTORRENT_LABEL
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
    token_request = request.request_response(host + 'token.html', auth=auth)
    token = re.findall('<div.*?>(.*?)</', token_request.content)[0]
    guid = token_request.cookies['GUID']
    cookies = dict(GUID = guid)

    if link.startswith("magnet") or link.startswith("http") or link.endswith(".torrent"):
        params = {'action':'add-url', 's':link, 'token':token}
        response = request.request_json(host, params=params, auth=auth, cookies=cookies)
    else:    
        method = "post"
        params = {'action':'add-file', 'token':token}
        files = {'torrent_file':{'music.torrent', link}}
        response = request.request_json(host, method=method, params=params, files=files, auth=auth, cookies=cookies)
    if not response:
        logger.error("Error sending torrent to uTorrent")
        return

    # NOW WE WILL CHECK UTORRENT FOR THE FOLDER NAME & SET THE LABEL
    params = {'list':'1', 'token':token}

    response = request.request_json(host, params=params, auth=auth, cookies=cookies)
    if not response:
        logger.error("Error getting torrent information from uTorrent")
        return

    # Not really sure how to ID these? Title seems safest)
    # Also, not sure when the torrent will pop up in the list, so we'll make sure it exists and is 1% downloaded
    tries = 0
    while tries < 10:
        for torrent in response['torrents']:
            if torrent[2] == title and torrent[4] > 1:
                folder = os.path.basename(torrent[26])
                tor_hash = torrent[0]
                params = {'action':'setprops', 'hash':tor_hash,'s':'label', 'v':label, 'token':token}
                response = request.request_json(host, params=params, auth=auth, cookies=cookies)
                break
            else:
                time.sleep(5)
                tries += 1

    return folder


