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


def addTorrent(link):

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
        params = {'action':'add-file', 'token':token}
        files = {'torrent_file':{'music.torrent' : link}}
        response = request.request_json(host, method="post", params=params, files=files, auth=auth, cookies=cookies)
    if not response:
        logger.error("Error sending torrent to uTorrent")
        return

    if link.startswith('magnet'):
        tor_hash = re.findall('urn:btih:([\w]{32,40})', link)[0]
        if len(tor_hash) == 32:
            tor_hash = b16encode(b32decode(tor_hash)).lower()
    else:
        info = bdecode(link.content)["info"]
        tor_hash = sha1(bencode(info)).hexdigest()
	    
    params = {'action':'setprops', 'hash':tor_hash,'s':'label', 'v':label, 'token':token}
    response = request.request_json(host, params=params, auth=auth, cookies=cookies)
    if not response:
        logger.error("Error setting torrent label in uTorrent")
        return

	# folder info can probably be cleaned up with getprops
	folder = None    

    params = {'list':'1', 'token':token}
    response = request.request_json(host, params=params, auth=auth, cookies=cookies)
    if not response:
        logger.error("Error getting torrent information from uTorrent")
        return

        for torrent in response['torrents']:
			folder = os.path.basename(torrent[26])

    return folder