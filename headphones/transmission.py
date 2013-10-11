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

import headphones
from headphones import logger, notifiers

import urllib2
import lib.simplejson as json
import base64
import time

# This is just a simple script to send torrents to transmission. The
# intention is to turn this into a class where we can check the state
# of the download, set the download dir, etc. 
# TODO: Store the session id so we don't need to make 2 calls
#       Store torrent id so we can check up on it

def addTorrent(link):
    method = 'torrent-add'
    arguments = {'filename': link, 'download-dir':headphones.DOWNLOAD_TORRENT_DIR}
    
    response = torrentAction(method,arguments)

    if not response:
        return False

    if response['result'] == 'success':
        try:
            name = response['arguments']['torrent-added']['name']
            logger.info(u"Torrent sent to Transmission successfully")
            if headphones.PROWL_ENABLED and headphones.PROWL_ONSNATCH:
                logger.info(u"Sending Prowl notification")
                prowl = notifiers.PROWL()
                prowl.notify(name,"Download started")
            if headphones.PUSHOVER_ENABLED and headphones.PUSHOVER_ONSNATCH:
                logger.info(u"Sending Pushover notification")
                prowl = notifiers.PUSHOVER()
                prowl.notify(name,"Download started")
            if headphones.NMA_ENABLED and headphones.NMA_ONSNATCH:
                logger.debug(u"Sending NMA notification")
                nma = notifiers.NMA()
                nma.notify(snatched_nzb=name)
            return response['arguments']['torrent-added']['hashString']
        except KeyError:
            logger.warn(u"Torrent was not sent to Transmission")
            return False
        
def getTorrentFolder(torrentid):
    method = 'torrent-get'
    arguments = { 'ids': torrentid, 'fields': ['name']}
    
    response = torrentAction(method, arguments)

    try:
        torrent_folder_name = response['arguments']['torrents'][0]['name']
        return torrent_folder_name
    except IndexError, e:
        return False

def torrentAction(method, arguments):
    
    host = headphones.TRANSMISSION_HOST
    username = headphones.TRANSMISSION_USERNAME
    password = headphones.TRANSMISSION_PASSWORD
    sessionid = None
    
    if not host.startswith('http'):
        host = 'http://' + host

    if host.endswith('/'):
        host = host[:-1]
	
    host = host + "/transmission/rpc"
    request = urllib2.Request(host)
    if username and password:
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
    opener = urllib2.build_opener()
    try:
        data = opener.open(request).read()
    except urllib2.HTTPError, e:
        if e.code == 409:
            sessionid = e.hdrs['x-transmission-session-id']
        else:
            logger.error('Could not connect to Transmission. Error: ' + str(e))
    except Exception, e:
        logger.error('Could not connect to Transmission. Error: ' + str(e))
    
    if not sessionid:
        logger.error("Error getting Session ID from Transmission")
        return
        
    request.add_header('x-transmission-session-id', sessionid)
        
    postdata = json.dumps({ 'method': method, 
                       'arguments': arguments })
                                      
    request.add_data(postdata)
                                      
    try:
        #logger.debug(u"Req: %s" % postdata)
        response = json.loads(opener.open(request).read())
        #logger.debug(u"Rsp: %s" % response)
    except Exception, e:
        logger.error("Error sending torrent to Transmission: " + str(e))
        return
        
    return response
