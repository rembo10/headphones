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

#####################################
## Stolen from Sick-Beard's sab.py ##
#####################################

import urllib, httplib
import datetime

import headphones

from lib import MultipartPostHandler
import urllib2, cookielib

from headphones.common import USER_AGENT
from headphones import logger
from headphones import notifiers, helpers

def sendNZB(nzb):

    params = {}

    if headphones.SAB_USERNAME:
        params['ma_username'] = headphones.SAB_USERNAME
    if headphones.SAB_PASSWORD:
        params['ma_password'] = headphones.SAB_PASSWORD
    if headphones.SAB_APIKEY:
        params['apikey'] = headphones.SAB_APIKEY
    if headphones.SAB_CATEGORY:
        params['cat'] = headphones.SAB_CATEGORY


#    # if released recently make it high priority
#    for curEp in nzb.episodes:
#        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
#            params['priority'] = 1

    # if it's a normal result we just pass SAB the URL
    if nzb.resultType == "nzb":
        # for newzbin results send the ID to sab specifically
        if nzb.provider.getID() == 'newzbin':
            id = nzb.provider.getIDFromURL(nzb.url)
            if not id:
                logger.info("Unable to send NZB to sab, can't find ID in URL "+str(nzb.url))
                return False
            params['mode'] = 'addid'
            params['name'] = id
        else:
            params['mode'] = 'addurl'
            params['name'] = nzb.url

    # if we get a raw data result we want to upload it to SAB
    elif nzb.resultType == "nzbdata":
        # Sanitize the file a bit, since we can only use ascii chars with MultiPartPostHandler
        nzbdata = helpers.latinToAscii(nzb.extraInfo[0])
        params['mode'] = 'addfile'
        multiPartParams = {"nzbfile": (nzb.name+".nzb", nzbdata)}

    if not headphones.SAB_HOST.startswith('http'):
        headphones.SAB_HOST = 'http://' + headphones.SAB_HOST

    if headphones.SAB_HOST.endswith('/'):
        headphones.SAB_HOST = headphones.SAB_HOST[0:len(headphones.SAB_HOST)-1]
    
    url = headphones.SAB_HOST + "/" + "api?" + urllib.urlencode(params)

    try:

        if nzb.resultType == "nzb":
            f = urllib.urlopen(url)
        elif nzb.resultType == "nzbdata":
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                          MultipartPostHandler.MultipartPostHandler)

            req = urllib2.Request(url,
                                  multiPartParams,
                                  headers={'User-Agent': USER_AGENT})

            f = opener.open(req)

    except (EOFError, IOError), e:
        logger.error(u"Unable to connect to SAB with URL: %s" % url)
        return False

    except httplib.InvalidURL, e:
        logger.error(u"Invalid SAB host, check your config. Current host: %s" % headphones.SAB_HOST)
        return False
        
    except Exception, e:
        logger.error(u"Error: " + str(e))
        return False
        
    if f == None:
        logger.info(u"No data returned from SABnzbd, NZB not sent")
        return False

    try:
        result = f.readlines()
    except Exception, e:
        logger.info(u"Error trying to get result from SAB, NZB not sent: ")
        return False

    if len(result) == 0:
        logger.info(u"No data returned from SABnzbd, NZB not sent")
        return False

    sabText = result[0].strip()

    logger.info(u"Result text from SAB: " + sabText)

    if sabText == "ok":
        logger.info(u"NZB sent to SAB successfully")
        if headphones.PROWL_ENABLED and headphones.PROWL_ONSNATCH:
            logger.info(u"Sending Prowl notification")
            prowl = notifiers.PROWL()
            prowl.notify(nzb.name,"Download started")
        if headphones.NMA_ENABLED and headphones.NMA_ONSNATCH:
            logger.debug(u"Sending NMA notification")
            nma = notifiers.NMA()
            nma.notify(snatched_nzb=nzb.name)

        return True
    elif sabText == "Missing authentication":
        logger.info(u"Incorrect username/password sent to SAB, NZB not sent")
        return False
    else:
        logger.info(u"Unknown failure sending NZB to sab. Return text is: " + sabText)
        return False
