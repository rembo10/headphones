# This file is modified to work with headphones by CurlyMo <curlymoo1@gmail.com> as a part of XBian - XBMC on the Raspberry Pi

# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import httplib
import datetime

import headphones

from base64 import standard_b64encode
import xmlrpclib

#from headphones.providers.generic import GenericProvider

from headphones import logger

def sendNZB(nzb):

    addToTop = False
    nzbgetXMLrpc = "%(username)s:%(password)s@%(host)s/xmlrpc"

    if headphones.NZBGET_HOST == None:
        logger.error(u"No NZBget host found in configuration. Please configure it.")
        return False

    if headphones.NZBGET_HOST.startswith('https://'):
        nzbgetXMLrpc = 'https://' + nzbgetXMLrpc
        headphones.NZBGET_HOST.replace('https://', '', 1)
    else:
        nzbgetXMLrpc = 'http://' + nzbgetXMLrpc
        headphones.NZBGET_HOST.replace('http://', '', 1)


    url = nzbgetXMLrpc % {"host": headphones.NZBGET_HOST, "username": headphones.NZBGET_USERNAME, "password": headphones.NZBGET_PASSWORD}

    nzbGetRPC = xmlrpclib.ServerProxy(url)
    try:
        if nzbGetRPC.writelog("INFO", "headphones connected to drop of %s any moment now." % (nzb.name + ".nzb")):
            logger.debug(u"Successfully connected to NZBget")
        else:
            logger.info(u"Successfully connected to NZBget, but unable to send a message" % (nzb.name + ".nzb"))

    except httplib.socket.error:
        logger.error(u"Please check your NZBget host and port (if it is running). NZBget is not responding to this combination")
        return False

    except xmlrpclib.ProtocolError, e:
        if (e.errmsg == "Unauthorized"):
            logger.error(u"NZBget password is incorrect.")
        else:
            logger.error(u"Protocol Error: " + e.errmsg)
        return False

    # if it's a normal result need to download the NZB content
    if nzb.resultType == "nzb":
        genProvider = GenericProvider("")
        data = genProvider.getURL(nzb.url)
        if (data == None):
            return False

    # if we get a raw data result thats even better
    elif nzb.resultType == "nzbdata":
        data = nzb.extraInfo[0]

    nzbcontent64 = standard_b64encode(data)

    logger.info(u"Sending NZB to NZBget")
    logger.debug(u"URL: " + url)

    if nzbGetRPC.append(nzb.name + ".nzb", headphones.NZBGET_CATEGORY, addToTop, nzbcontent64):
        logger.debug(u"NZB sent to NZBget successfully")
        return True
    else:
        logger.error(u"NZBget could not add %s to the queue" % (nzb.name + ".nzb"))
        return False
