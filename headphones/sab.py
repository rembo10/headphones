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

import MultipartPostHandler
import headphones
import cookielib
import urllib2
import httplib
import urllib
import ast

from headphones.common import USER_AGENT
from headphones import logger
from headphones import helpers


def sendNZB(nzb):

    params = {}

    if headphones.CONFIG.SAB_USERNAME:
        params['ma_username'] = headphones.CONFIG.SAB_USERNAME
    if headphones.CONFIG.SAB_PASSWORD:
        params['ma_password'] = headphones.CONFIG.SAB_PASSWORD
    if headphones.CONFIG.SAB_APIKEY:
        params['apikey'] = headphones.CONFIG.SAB_APIKEY
    if headphones.CONFIG.SAB_CATEGORY:
        params['cat'] = headphones.CONFIG.SAB_CATEGORY

    # if it's a normal result we just pass SAB the URL
    if nzb.resultType == "nzb":
        # for newzbin results send the ID to sab specifically
        if nzb.provider.getID() == 'newzbin':
            id = nzb.provider.getIDFromURL(nzb.url)
            if not id:
                logger.info("Unable to send NZB to sab, can't find ID in URL " + str(nzb.url))
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
        multiPartParams = {"nzbfile": (helpers.latinToAscii(nzb.name) + ".nzb", nzbdata)}

    if not headphones.CONFIG.SAB_HOST.startswith('http'):
        headphones.CONFIG.SAB_HOST = 'http://' + headphones.CONFIG.SAB_HOST

    if headphones.CONFIG.SAB_HOST.endswith('/'):
        headphones.CONFIG.SAB_HOST = headphones.CONFIG.SAB_HOST[0:len(headphones.CONFIG.SAB_HOST) - 1]

    url = headphones.CONFIG.SAB_HOST + "/" + "api?" + urllib.urlencode(params)

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

    except (EOFError, IOError) as e:
        logger.error(u"Unable to connect to SAB with URL: %s" % url)
        return False

    except httplib.InvalidURL as e:
        logger.error(u"Invalid SAB host, check your config. Current host: %s" % headphones.CONFIG.SAB_HOST)
        return False

    except Exception as e:
        logger.error(u"Error: " + str(e))
        return False

    if f is None:
        logger.info(u"No data returned from SABnzbd, NZB not sent")
        return False

    try:
        result = f.readlines()
    except Exception as e:
        logger.info(u"Error trying to get result from SAB, NZB not sent: ")
        return False

    if len(result) == 0:
        logger.info(u"No data returned from SABnzbd, NZB not sent")
        return False

    sabText = result[0].strip()

    logger.info(u"Result text from SAB: " + sabText)

    if sabText == "ok":
        logger.info(u"NZB sent to SAB successfully")
        return True
    elif sabText == "Missing authentication":
        logger.info(u"Incorrect username/password sent to SAB, NZB not sent")
        return False
    else:
        logger.info(u"Unknown failure sending NZB to sab. Return text is: " + sabText)
        return False


def checkConfig():

    params = {'mode': 'get_config',
               'section': 'misc'
               }

    if headphones.CONFIG.SAB_USERNAME:
        params['ma_username'] = headphones.CONFIG.SAB_USERNAME
    if headphones.CONFIG.SAB_PASSWORD:
        params['ma_password'] = headphones.CONFIG.SAB_PASSWORD
    if headphones.CONFIG.SAB_APIKEY:
        params['apikey'] = headphones.CONFIG.SAB_APIKEY

    if not headphones.CONFIG.SAB_HOST.startswith('http'):
        headphones.CONFIG.SAB_HOST = 'http://' + headphones.CONFIG.SAB_HOST

    if headphones.CONFIG.SAB_HOST.endswith('/'):
        headphones.CONFIG.SAB_HOST = headphones.CONFIG.SAB_HOST[0:len(headphones.CONFIG.SAB_HOST) - 1]

    url = headphones.CONFIG.SAB_HOST + "/" + "api?" + urllib.urlencode(params)

    try:
        f = urllib.urlopen(url).read()
    except Exception:
        logger.warn("Unable to read SABnzbd config file - cannot determine renaming options (might affect auto & forced post processing)")
        return (0, 0)

    config_options = ast.literal_eval(f)

    replace_spaces = config_options['misc']['replace_spaces']
    replace_dots = config_options['misc']['replace_dots']

    return (replace_spaces, replace_dots)
