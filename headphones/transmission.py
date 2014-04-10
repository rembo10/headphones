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
        if headphones.GROWL_ENABLED and headphones.GROWL_ONSNATCH:
            logger.info(u"Sending Growl notification")
            growl = notifiers.GROWL()
            growl.notify(name,"Download started")
        if headphones.PROWL_ENABLED and headphones.PROWL_ONSNATCH:
            logger.info(u"Sending Prowl notification")
            prowl = notifiers.PROWL()
            prowl.notify(name,"Download started")
        if headphones.PUSHOVER_ENABLED and headphones.PUSHOVER_ONSNATCH:
            logger.info(u"Sending Pushover notification")
            pushover = notifiers.PUSHOVER()
            pushover.notify(name,"Download started")
        if headphones.TWITTER_ENABLED and headphones.TWITTER_ONSNATCH:
            logger.info(u"Sending Twitter notification")
            twitter = notifiers.TwitterNotifier()
            twitter.notify_snatch(nzb.name)
        if headphones.NMA_ENABLED and headphones.NMA_ONSNATCH:
            logger.info(u"Sending NMA notification")
            nma = notifiers.NMA()
            nma.notify(snatched_nzb=name)
        if headphones.PUSHALOT_ENABLED and headphones.PUSHALOT_ONSNATCH:
            logger.info(u"Sending Pushalot notification")
            pushalot = notifiers.PUSHALOT()
            pushalot.notify(name,"Download started")

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

    host = headphones.TRANSMISSION_HOST
    username = headphones.TRANSMISSION_USERNAME
    password = headphones.TRANSMISSION_PASSWORD
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
    headers = { 'x-transmission-session-id': sessionid }
    data = { 'method': method, 'arguments': arguments }

    response = request.request_json(host, method="post", data=json.dumps(data), headers=headers, auth=auth)

    if not response:
        logger.error("Error sending torrent to Transmission")
        return

    return response
