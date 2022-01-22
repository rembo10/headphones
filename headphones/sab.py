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

###################################
# Stolen from Sick-Beard's sab.py #
###################################

import http.cookiejar

import headphones
from headphones.common import USER_AGENT
from headphones import logger, helpers, request


def sab_api_call(request_type=None, params={}, **kwargs):
    if not headphones.CONFIG.SAB_HOST.startswith('http'):
        headphones.CONFIG.SAB_HOST = 'http://' + headphones.CONFIG.SAB_HOST

    if headphones.CONFIG.SAB_HOST.endswith('/'):
        headphones.CONFIG.SAB_HOST = headphones.CONFIG.SAB_HOST[
            0:len(headphones.CONFIG.SAB_HOST) - 1]

    url = headphones.CONFIG.SAB_HOST + "/" + "api?"

    if headphones.CONFIG.SAB_USERNAME:
        params['ma_username'] = headphones.CONFIG.SAB_USERNAME
    if headphones.CONFIG.SAB_PASSWORD:
        params['ma_password'] = headphones.CONFIG.SAB_PASSWORD
    if headphones.CONFIG.SAB_APIKEY:
        params['apikey'] = headphones.CONFIG.SAB_APIKEY

    if request_type == 'send_nzb' and headphones.CONFIG.SAB_CATEGORY:
        params['cat'] = headphones.CONFIG.SAB_CATEGORY

    params['output'] = 'json'

    response = request.request_json(url, params=params, **kwargs)

    if not response:
        logger.error("Error connecting to SABnzbd on url: %s" % headphones.CONFIG.SAB_HOST)
        return False
    else:
        logger.debug("Successfully connected to SABnzbd on url: %s" % headphones.CONFIG.SAB_HOST)
        return response


def sendNZB(nzb):
    params = {}
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
        nzbdata = nzb.extraInfo[0]
        params['mode'] = 'addfile'
        files = {"nzbfile": (nzb.name + ".nzb", nzbdata)}
        headers = {'User-Agent': USER_AGENT}

    logger.info("Attempting to connect to SABnzbd on url: %s" % headphones.CONFIG.SAB_HOST)
    if nzb.resultType == "nzb":
        response = sab_api_call('send_nzb', params=params)
    elif nzb.resultType == "nzbdata":
        cookies = http.cookiejar.CookieJar()
        response = sab_api_call('send_nzb', params=params, method="post", files=files,
                                cookies=cookies, headers=headers)

    if not response:
        logger.info("No data returned from SABnzbd, NZB not sent")
        return False

    if response['status']:
        logger.info("NZB sent to SABnzbd successfully")
        return True
    else:
        logger.error("Error sending NZB to SABnzbd: %s" % response['error'])
        return False


def checkConfig():
    params = {'mode': 'get_config',
              'section': 'misc',
              }

    config_options = sab_api_call(params=params)

    if not config_options:
        logger.warn(
            "Unable to read SABnzbd config file - cannot determine renaming options (might affect auto & forced post processing)")
        return (0, 0)

    replace_spaces = config_options['config']['misc']['replace_spaces']
    replace_dots = config_options['config']['misc']['replace_dots']

    return (replace_spaces, replace_dots)
