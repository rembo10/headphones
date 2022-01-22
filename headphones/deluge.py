# -*- coding: utf-8 -*-

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

# Parts of this file are a part of SickRage.
# Author: Mr_Orange <mr_orange@hotmail.it>
# URL: http://code.google.com/p/sickbeard/
# Adapted for Headphones by <noamgit@gmail.com>
# URL: https://github.com/noam09
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.


from headphones import logger

import time
import re
import os
import json
import headphones
import requests
from base64 import b64encode
import traceback

delugeweb_auth = {}
delugeweb_url = ''
deluge_verify_cert = False
scrub_logs = True
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}


def _scrubber(text):
    if scrub_logs:
        try:
            # URL parameter values
            text = re.sub('=[0-9a-zA-Z]*', '=REMOVED', text)
            # Local host with port
            # text = re.sub('\:\/\/.*\:', '://REMOVED:', text) # just host
            text = re.sub('\:\/\/.*\:[0-9]*', '://REMOVED:', text)
            # Session cookie
            text = re.sub("_session_id'\: '.*'", "_session_id': 'REMOVED'", text)
            # Local Windows user path
            if text.lower().startswith('c:\\users\\'):
                k = text.split('\\')
                text = '\\'.join([k[0], k[1], '.....', k[-1]])
            # partial_link = re.sub('(auth.*?)=.*&','\g<1>=SECRETZ&', link)
            # partial_link = re.sub('(\w)=[0-9a-zA-Z]*&*','\g<1>=REMOVED&', link)
        except Exception as e:
            logger.debug('Deluge: Scrubber failed: %s' % str(e))
    return text


def addTorrent(link, data=None, name=None):
    try:
        # Authenticate anyway
        logger.debug('Deluge: addTorrent Authentication')
        _get_auth()

        result = {}
        retid = False
        url_orpheus = ['https://orpheus.network/', 'http://orpheus.network/']
        url_waffles = ['https://waffles.ch/', 'http://waffles.ch/']

        if link.lower().startswith('magnet:'):
            logger.debug('Deluge: Got a magnet link: %s' % _scrubber(link))
            result = {'type': 'magnet',
                      'url': link}
            retid = _add_torrent_magnet(result)

        elif link.lower().startswith('http://') or link.lower().startswith('https://'):
            logger.debug('Deluge: Got a URL: %s' % _scrubber(link))
            if link.lower().startswith(tuple(url_waffles)):
                if 'rss=' not in link:
                    link = link + '&rss=1'
            if link.lower().startswith(tuple(url_orpheus)):
                logger.debug('Deluge: Using different User-Agent for this site')
                user_agent = 'Headphones'
                # This method will make Deluge download the file
                # logger.debug('Deluge: Letting Deluge download this')
                # local_torrent_path = _add_torrent_url({'url': link})
                # logger.debug('Deluge: Returned this local path: %s' % _scrubber(local_torrent_path))
                # return addTorrent(local_torrent_path)
            else:
                user_agent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'
            get_headers = {'User-Agent': user_agent}
            torrentfile = ''
            logger.debug('Deluge: Trying to download (GET)')
            try:
                r = requests.get(link, headers=get_headers)
                if r.status_code == 200:
                    logger.debug('Deluge: 200 OK')
                    # .text will ruin the encoding for some torrents
                    torrentfile = r.content
                else:
                    logger.debug('Deluge: Trying to GET %s returned status %d' % (_scrubber(link), r.status_code))
                    return False
            except Exception as e:
                logger.debug('Deluge: Download failed: %s' % str(e))
            if 'announce' not in str(torrentfile)[:40]:
                logger.debug('Deluge: Contents of %s doesn\'t look like a torrent file' % _scrubber(link))
                return False
            if not name:
                # Extract torrent name from .torrent
                try:
                    logger.debug('Deluge: Getting torrent name length')
                    name_length = int(re.findall('name([0-9]*)\:.*?\:', str(torrentfile))[0])
                    logger.debug('Deluge: Getting torrent name')
                    name = re.findall('name[0-9]*\:(.*?)\:', str(torrentfile))[0][:name_length]
                except Exception as e:
                    logger.debug('Deluge: Could not get torrent name, getting file name')
                    # get last part of link/path (name only)
                    name = link.split('\\')[-1].split('/')[-1]
                    # remove '.torrent' suffix
                    if name[-len('.torrent'):] == '.torrent':
                        name = name[:-len('.torrent')]
            try:
                logger.debug('Deluge: Sending Deluge torrent with name %s and content [%s...]' % (name, str(torrentfile)[:40]))
            except:
                logger.debug('Deluge: Sending Deluge torrent with problematic name and some content')
            result = {'type': 'torrent',
                      'name': name,
                      'content': torrentfile}
            retid = _add_torrent_file(result)

        # elif link.endswith('.torrent') or data:
        elif not (link.lower().startswith('http://') or link.lower().startswith('https://')):
            if data:
                logger.debug('Deluge: Getting .torrent data')
                torrentfile = data
            else:
                logger.debug('Deluge: Getting .torrent file')
                with open(link, 'rb') as f:
                    torrentfile = f.read()
            if not name:
                # Extract torrent name from .torrent
                try:
                    logger.debug('Deluge: Getting torrent name length')
                    name_length = int(re.findall('name([0-9]*)\:.*?\:', str(torrentfile))[0])
                    logger.debug('Deluge: Getting torrent name')
                    name = re.findall('name[0-9]*\:(.*?)\:', str(torrentfile))[0][:name_length]
                except Exception as e:
                    logger.debug('Deluge: Could not get torrent name, getting file name')
                    # get last part of link/path (name only)
                    name = link.split('\\')[-1].split('/')[-1]
                    # remove '.torrent' suffix
                    if name[-len('.torrent'):] == '.torrent':
                        name = name[:-len('.torrent')]
            try:
                logger.debug('Deluge: Sending Deluge torrent with name %s and content [%s...]' % (name, str(torrentfile)[:40]))
            except UnicodeDecodeError:
                logger.debug('Deluge: Sending Deluge torrent with name %s and content [%s...]' % (name.decode('utf-8'), str(torrentfile)[:40]))
            result = {'type': 'torrent',
                      'name': name,
                      'content': torrentfile}
            retid = _add_torrent_file(result)

        else:
            logger.error('Deluge: Unknown file type: %s' % link)

        if retid:
            logger.info('Deluge: Torrent sent to Deluge successfully  (%s)' % retid)
            return retid
        else:
            logger.info('Deluge: Returned status %s' % retid)
            return False

    except Exception as e:
        logger.error(str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))


def getTorrentFolder(result):
    logger.debug('Deluge: Get torrent folder name')
    if not any(delugeweb_auth):
        _get_auth()

    try:
        post_data = json.dumps({"method": "web.get_torrent_status",
                                "params": [
                                    result['hash'],
                                    ["total_done"]
                                ],
                                "id": 21})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
        result['total_done'] = json.loads(response.text)['result']['total_done']

        tries = 0
        while result['total_done'] == 0 and tries < 10:
            tries += 1
            time.sleep(5)
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
            result['total_done'] = json.loads(response.text)['result']['total_done']

        post_data = json.dumps({"method": "web.get_torrent_status",
                                "params": [
                                    result['hash'],
                                    [
                                        "name",
                                        "save_path",
                                        "total_size",
                                        "num_files",
                                        "message",
                                        "tracker",
                                        "comment"
                                    ]
                                ],
                                "id": 23})

        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)

        result['save_path'] = json.loads(response.text)['result']['save_path']
        result['name'] = json.loads(response.text)['result']['name']

        return json.loads(response.text)['result']['name']
    except Exception as e:
        logger.debug('Deluge: Could not get torrent folder name: %s' % str(e))


def removeTorrent(torrentid, remove_data=False):
    logger.debug('Deluge: Remove torrent %s' % torrentid)
    if not any(delugeweb_auth):
        _get_auth()

    try:
        logger.debug('Deluge: Checking if torrent %s finished seeding' % str(torrentid))
        post_data = json.dumps({"method": "web.get_torrent_status",
                                "params": [
                                    torrentid,
                                    [
                                        "name",
                                        "ratio",
                                        "state"
                                    ]
                                ],
                                "id": 26})

        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)

        try:
            state = json.loads(response.text)['result']['state']
        except KeyError as e:
            logger.debug('Deluge: "state" KeyError when trying to remove torrent %s' % str(torrentid))
            return False

        not_finished = ["queued", "seeding", "downloading", "checking", "error"]
        result = False
        if state.lower() in not_finished:
            logger.debug('Deluge: Torrent %s is either queued or seeding, not removing yet' % str(torrentid))
            return False
        else:
            logger.debug('Deluge: Removing torrent %s' % str(torrentid))
            post_data = json.dumps({"method": "core.remove_torrent",
                                    "params": [
                                        torrentid,
                                        remove_data
                                    ],
                                    "id": 25})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
            result = json.loads(response.text)['result']

            return result
    except Exception as e:
        logger.error('Deluge: Removing torrent failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None


def _get_auth():
    logger.debug('Deluge: Authenticating...')
    global delugeweb_auth, delugeweb_url, deluge_verify_cert
    delugeweb_auth = {}

    delugeweb_host = headphones.CONFIG.DELUGE_HOST
    delugeweb_cert = headphones.CONFIG.DELUGE_CERT
    delugeweb_password = headphones.CONFIG.DELUGE_PASSWORD
    if len(delugeweb_password) > 0:
        logger.debug('Deluge: Using password %s******%s' % (delugeweb_password[0], delugeweb_password[-1]))

    if not delugeweb_host.startswith('http'):
        delugeweb_host = 'http://%s' % delugeweb_host

    if delugeweb_cert is None or delugeweb_cert.strip() == '':
        deluge_verify_cert = False
        logger.debug('Deluge: FYI no SSL certificate configured')
    else:
        deluge_verify_cert = delugeweb_cert
        delugeweb_host = delugeweb_host.replace('http:', 'https:')
        logger.debug('Deluge: Using certificate %s, host is now %s' % (_scrubber(deluge_verify_cert), _scrubber(delugeweb_host)))

    if delugeweb_host.endswith('/'):
        delugeweb_host = delugeweb_host[:-1]

    delugeweb_url = delugeweb_host + '/json'

    post_data = json.dumps({"method": "auth.login",
                            "params": [delugeweb_password],
                            "id": 1})
    try:
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
    except requests.ConnectionError:
        try:
            logger.debug('Deluge: Connection failed, let\'s try HTTPS just in case')
            response = requests.post(delugeweb_url.replace('http:', 'https:'), data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
            # If the previous line didn't fail, change delugeweb_url for the rest of this session
            logger.error('Deluge: Switching to HTTPS, but certificate won\'t be verified because NO CERTIFICATE WAS CONFIGURED!')
            delugeweb_url = delugeweb_url.replace('http:', 'https:')
        except Exception as e:
            logger.error('Deluge: Authentication failed: %s' % str(e))
            formatted_lines = traceback.format_exc().splitlines()
            logger.error('; '.join(formatted_lines))
            return None
    except Exception as e:
        logger.error('Deluge: Authentication failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None

    auth = json.loads(response.text)["result"]
    auth_error = json.loads(response.text)["error"]
    logger.debug('Deluge: Authentication result: %s, Error: %s' % (auth, auth_error))
    delugeweb_auth = response.cookies
    logger.debug('Deluge: Authentication cookies: %s' % _scrubber(str(delugeweb_auth.get_dict())))
    post_data = json.dumps({"method": "web.connected",
                            "params": [],
                            "id": 10})
    try:
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
    except Exception as e:
        logger.error('Deluge: Authentication failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None

    connected = json.loads(response.text)['result']
    connected_error = json.loads(response.text)['error']
    logger.debug('Deluge: Connection result: %s, Error: %s' % (connected, connected_error))

    if not connected:
        post_data = json.dumps({"method": "web.get_hosts",
                                "params": [],
                                "id": 11})
        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
        except Exception as e:
            logger.error('Deluge: Authentication failed: %s' % str(e))
            formatted_lines = traceback.format_exc().splitlines()
            logger.error('; '.join(formatted_lines))
            return None

        delugeweb_hosts = json.loads(response.text)['result']
        # Check if delugeweb_hosts is None before checking its length
        if not delugeweb_hosts or len(delugeweb_hosts) == 0:
            logger.error('Deluge: WebUI does not contain daemons')
            return None

        post_data = json.dumps({"method": "web.connect",
                                "params": [delugeweb_hosts[0][0]],
                                "id": 11})

        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
        except Exception as e:
            logger.error('Deluge: Authentication failed: %s' % str(e))
            formatted_lines = traceback.format_exc().splitlines()
            logger.error('; '.join(formatted_lines))
            return None

        post_data = json.dumps({"method": "web.connected",
                                "params": [],
                                "id": 10})

        try:
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
        except Exception as e:
            logger.error('Deluge: Authentication failed: %s' % str(e))
            formatted_lines = traceback.format_exc().splitlines()
            logger.error('; '.join(formatted_lines))
            return None

        connected = json.loads(response.text)['result']

        if not connected:
            logger.error('Deluge: WebUI could not connect to daemon')
            return None

    return auth


def _add_torrent_magnet(result):
    logger.debug('Deluge: Adding magnet')
    if not any(delugeweb_auth):
        _get_auth()
    try:
        post_data = json.dumps({"method": "core.add_torrent_magnet",
                                "params": [result['url'], {}],
                                "id": 2})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
        result['hash'] = json.loads(response.text)['result']
        logger.debug('Deluge: Response was %s' % str(json.loads(response.text)))
        return json.loads(response.text)['result']
    except Exception as e:
        logger.error('Deluge: Adding torrent magnet failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return False


def _add_torrent_url(result):
    logger.debug('Deluge: Adding URL')
    if not any(delugeweb_auth):
        _get_auth()
    try:
        post_data = json.dumps({"method": "web.download_torrent_from_url",
                                "params": [result['url'], {}],
                                "id": 32})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
        result['location'] = json.loads(response.text)['result']
        logger.debug('Deluge: Response was %s' % str(json.loads(response.text)))
        return json.loads(response.text)['result']
    except Exception as e:
        logger.error('Deluge: Adding torrent URL failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return False


def _add_torrent_file(result):
    logger.debug('Deluge: Adding file')
    if not any(delugeweb_auth):
        _get_auth()
    try:
        # content is torrent file contents that needs to be encoded to base64
        post_data = json.dumps({"method": "core.add_torrent_file",
                                "params": [result['name'] + '.torrent',
                                           b64encode(result['content']).decode(), {}],
                                "id": 2})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
        result['hash'] = json.loads(response.text)['result']
        logger.debug('Deluge: Response was %s' % str(json.loads(response.text)))
        return json.loads(response.text)['result']
    except Exception as e:
        logger.error('Deluge: Adding torrent file failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return False


def setTorrentLabel(result):
    logger.debug('Deluge: Setting label')
    label = headphones.CONFIG.DELUGE_LABEL

    if not any(delugeweb_auth):
        _get_auth()

    if ' ' in label:
        logger.error('Deluge: Invalid label. Label can\'t contain spaces - replacing with underscores')
        label = label.replace(' ', '_')
    if label:
        # check if label already exists and create it if not
        post_data = json.dumps({"method": 'label.get_labels',
                                "params": [],
                                "id": 3})
        response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                 verify=deluge_verify_cert, headers=headers)
        labels = json.loads(response.text)['result']

        if labels is not None:
            if label not in labels:
                try:
                    logger.debug('Deluge: %s label doesn\'t exist in Deluge, let\'s add it' % label)
                    post_data = json.dumps({"method": 'label.add',
                                            "params": [label],
                                            "id": 4})
                    response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                             verify=deluge_verify_cert, headers=headers)
                    logger.debug('Deluge: %s label added to Deluge' % label)
                except Exception as e:
                    logger.error('Deluge: Setting label failed: %s' % str(e))
                    formatted_lines = traceback.format_exc().splitlines()
                    logger.error('; '.join(formatted_lines))

            # add label to torrent
            post_data = json.dumps({"method": 'label.set_torrent',
                                    "params": [result['hash'], label],
                                    "id": 5})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
            logger.debug('Deluge: %s label added to torrent' % label)
        else:
            logger.debug('Deluge: Label plugin not detected')
            return False

    return not json.loads(response.text)['error']


def setSeedRatio(result):
    logger.debug('Deluge: Setting seed ratio')
    if not any(delugeweb_auth):
        _get_auth()

    ratio = None
    if result['ratio']:
        ratio = result['ratio']

    try:
        if ratio:
            post_data = json.dumps({"method": "core.set_torrent_stop_at_ratio",
                                    "params": [result['hash'], True],
                                    "id": 5})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)
            post_data = json.dumps({"method": "core.set_torrent_stop_ratio",
                                    "params": [result['hash'], float(ratio)],
                                    "id": 6})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)

            return not json.loads(response.text)['error']

        return True
    except Exception as e:
        logger.error('Deluge: Setting seed ratio failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None


def setTorrentPath(result):
    logger.debug('Deluge: Setting download path')
    if not any(delugeweb_auth):
        _get_auth()

    try:
        if headphones.CONFIG.DELUGE_DONE_DIRECTORY or headphones.CONFIG.DOWNLOAD_TORRENT_DIR:
            post_data = json.dumps({"method": "core.set_torrent_move_completed",
                                    "params": [result['hash'], True],
                                    "id": 7})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)

            if headphones.CONFIG.DELUGE_DONE_DIRECTORY:
                move_to = headphones.CONFIG.DELUGE_DONE_DIRECTORY
            else:
                move_to = headphones.CONFIG.DOWNLOAD_TORRENT_DIR

            if not os.path.exists(move_to):
                logger.debug('Deluge: %s directory doesn\'t exist, let\'s create it' % move_to)
                os.makedirs(move_to)
            post_data = json.dumps({"method": "core.set_torrent_move_completed_path",
                                    "params": [result['hash'], move_to],
                                    "id": 8})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)

            return not json.loads(response.text)['error']

        return True
    except Exception as e:
        logger.error('Deluge: Setting torrent move-to directory failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None


def setTorrentPause(result):
    logger.debug('Deluge: Pausing torrent')
    if not any(delugeweb_auth):
        _get_auth()

    try:
        if headphones.CONFIG.DELUGE_PAUSED:
            post_data = json.dumps({"method": "core.pause_torrent",
                                    "params": [[result['hash']]],
                                    "id": 9})
            response = requests.post(delugeweb_url, data=post_data.encode('utf-8'), cookies=delugeweb_auth,
                                     verify=deluge_verify_cert, headers=headers)

            return not json.loads(response.text)['error']

        return True
    except Exception as e:
        logger.error('Deluge: Setting torrent paused failed: %s' % str(e))
        formatted_lines = traceback.format_exc().splitlines()
        logger.error('; '.join(formatted_lines))
        return None
