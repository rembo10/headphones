from urllib.parse import urlencode, quote_plus
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import json
from email.mime.text import MIMEText
import smtplib
import email.utils
from http.client import HTTPSConnection
from urllib.parse import parse_qsl
import urllib.request
import urllib.error
import urllib.parse
import requests as requests

import os.path
from headphones import logger, helpers, common, request
from pynma import pynma
import cherrypy
import headphones
import gntp.notifier
#import oauth2 as oauth
import twitter


class GROWL(object):
    """
    Growl notifications, for OS X.
    """

    def __init__(self):
        self.enabled = headphones.CONFIG.GROWL_ENABLED
        self.host = headphones.CONFIG.GROWL_HOST
        self.password = headphones.CONFIG.GROWL_PASSWORD

    def conf(self, options):
        return cherrypy.config['config'].get('Growl', options)

    def notify(self, message, event):
        if not self.enabled:
            return

        # Split host and port
        if self.host == "":
            host, port = "localhost", 23053

        if ":" in self.host:
            host, port = self.host.split(':', 1)
            port = int(port)
        else:
            host, port = self.host, 23053

        # If password is empty, assume none
        if self.password == "":
            password = None
        else:
            password = self.password

        # Register notification
        growl = gntp.notifier.GrowlNotifier(
            applicationName='Headphones',
            notifications=['New Event'],
            defaultNotifications=['New Event'],
            hostname=host,
            port=port,
            password=password
        )

        try:
            growl.register()
        except gntp.notifier.errors.NetworkError:
            logger.warning('Growl notification failed: network error')
            return
        except gntp.notifier.errors.AuthError:
            logger.warning('Growl notification failed: authentication error')
            return

        # Fix message
        message = message.encode(headphones.SYS_ENCODING, "replace")

        # Send it, including an image
        image_file = os.path.join(str(headphones.PROG_DIR),
                                  "data/images/headphoneslogo.png")

        with open(image_file, 'rb') as f:
            image = f.read()

        try:
            growl.notify(
                noteType='New Event',
                title=event,
                description=message,
                icon=image
            )
        except gntp.notifier.errors.NetworkError:
            logger.warning('Growl notification failed: network error')
            return

        logger.info("Growl notifications sent.")

    def updateLibrary(self):
        # For uniformity reasons not removed
        return

    def test(self, host, password):
        self.enabled = True
        self.host = host
        self.password = password

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')


class PROWL(object):
    """
    Prowl notifications.
    """

    def __init__(self):
        self.enabled = headphones.CONFIG.PROWL_ENABLED
        self.keys = headphones.CONFIG.PROWL_KEYS
        self.priority = headphones.CONFIG.PROWL_PRIORITY

    def conf(self, options):
        return cherrypy.config['config'].get('Prowl', options)

    def notify(self, message, event):
        if not headphones.CONFIG.PROWL_ENABLED:
            return

        http_handler = HTTPSConnection("api.prowlapp.com")

        data = {'apikey': headphones.CONFIG.PROWL_KEYS,
                'application': 'Headphones',
                'event': event,
                'description': message.encode("utf-8"),
                'priority': headphones.CONFIG.PROWL_PRIORITY}

        http_handler.request("POST",
                             "/publicapi/add",
                             headers={
                                 'Content-type':
                                     "application/x-www-form-urlencoded"},
                             body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            logger.info("Prowl notifications sent.")
            return True
        elif request_status == 401:
            logger.info("Prowl auth failed: %s" % response.reason)
            return False
        else:
            logger.info("Prowl notification failed.")
            return False

    def updateLibrary(self):
        # For uniformity reasons not removed
        return

    def test(self, keys, priority):
        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')


class MPC(object):
    """
    MPC library update
    """

    def __init__(self):
        pass

    def notify(self):
        subprocess.call(["mpc", "update"])


class XBMC(object):
    """
    XBMC notifications
    """

    def __init__(self):

        self.hosts = headphones.CONFIG.XBMC_HOST
        self.username = headphones.CONFIG.XBMC_USERNAME
        self.password = headphones.CONFIG.XBMC_PASSWORD

    def _sendhttp(self, host, command):
        url_command = urllib.parse.urlencode(command)
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        if self.password:
            return request.request_content(url,
                                           auth=(self.username, self.password))
        else:
            return request.request_content(url)

    def _sendjson(self, host, method, params={}):
        data = [
            {'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.password:
            response = request.request_json(
                url, method="post",
                data=json.dumps(data),
                headers=headers, auth=(
                    self.username, self.password))
        else:
            response = request.request_json(url, method="post",
                                            data=json.dumps(data),
                                            headers=headers)

        if response:
            return response[0]['result']

    def update(self):
        # From what I read you can't update the music library on a per
        # directory or per path basis so need to update the whole thing

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library update command to XBMC @ ' + host)
            request = self._sendjson(host, 'AudioLibrary.Scan')

            if not request:
                logger.warn('Error sending update request to XBMC')

    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.hosts.split(',')]

        header = "Headphones"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000"  # in ms

        for host in hosts:
            logger.info('Sending notification command to XMBC @ ' + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties',
                                         {'properties': ['version']})[
                    'version']['major']

                if version < 12:  # Eden
                    notification = header + "," + message + "," + time + \
                        "," + albumartpath
                    notifycommand = {'command': 'ExecBuiltIn',
                                     'parameter': 'Notification(' +
                                                  notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': header, 'message': message,
                              'displaytime': int(time),
                              'image': albumartpath}
                    request = self._sendjson(host, 'GUI.ShowNotification',
                                             params)

                if not request:
                    raise Exception

            except Exception:
                logger.error('Error sending notification request to XBMC')


class LMS(object):
    """
    Class for updating a Logitech Media Server
    """

    def __init__(self):
        self.hosts = headphones.CONFIG.LMS_HOST

    def _sendjson(self, host):
        data = {'id': 1, 'method': 'slim.request', 'params': ["", ["rescan"]]}
        data = json.JSONEncoder().encode(data)

        content = {'Content-Type': 'application/json'}

        req = urllib.request.Request(host + '/jsonrpc.js', data, content)

        try:
            handle = urllib.request.urlopen(req)
        except Exception as e:
            logger.warn('Error opening LMS url: %s' % e)
            return

        response = json.JSONDecoder().decode(handle.read())

        try:
            return response['result']
        except:
            logger.warn('LMS returned error: %s' % response['error'])
            return response['error']

    def update(self):

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library rescan command to LMS @ ' + host)
            request = self._sendjson(host)

            if request:
                logger.warn('Error sending rescan request to LMS')


class Plex(object):
    def __init__(self):

        self.server_hosts = headphones.CONFIG.PLEX_SERVER_HOST
        self.client_hosts = headphones.CONFIG.PLEX_CLIENT_HOST
        self.username = headphones.CONFIG.PLEX_USERNAME
        self.password = headphones.CONFIG.PLEX_PASSWORD
        self.token = headphones.CONFIG.PLEX_TOKEN

    def _sendhttp(self, host, command):

        url = host + '/xbmcCmds/xbmcHttp/?' + command

        if self.password:
            response = request.request_response(url, auth=(
                self.username, self.password))
        else:
            response = request.request_response(url)

        return response

    def _sendjson(self, host, method, params={}):
        data = [
            {'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.password:
            response = request.request_json(
                url, method="post",
                data=json.dumps(data),
                headers=headers, auth=(
                    self.username, self.password))
        else:
            response = request.request_json(url, method="post",
                                            data=json.dumps(data),
                                            headers=headers)

        if response:
            return response[0]['result']

    def update(self):

        # Get token from user credentials
        if not self.token:
            loginpage = 'https://plex.tv/users/sign_in.json'
            post_params = {
                'user[login]': self.username,
                'user[password]': self.password
            }
            headers = {
                'X-Plex-Device-Name': 'Headphones',
                'X-Plex-Product': 'Headphones',
                'X-Plex-Client-Identifier': common.USER_AGENT,
                'X-Plex-Version': ''
            }

            logger.info("Getting plex.tv credentials for user %s", self.username)

            try:
                r = requests.post(loginpage, data=post_params, headers=headers)
                r.raise_for_status()
            except requests.RequestException as e:
                logger.error("Error getting plex.tv credentials, check settings: %s", e)
                return False

            try:
                data = r.json()
            except ValueError as e:
                logger.error("Error getting plex.tv credentials: %s", e)
                return False

            try:
                self.token = data['user']['authentication_token']
            except KeyError as e:
                logger.error("Error getting plex.tv credentials: %s", e)
                return False

        # From what I read you can't update the music library on a per
        # directory or per path basis so need to update the whole thing

        hosts = [x.strip() for x in self.server_hosts.split(',')]

        for host in hosts:
            logger.info(
                'Sending library update command to Plex Media Server@ ' + host)
            url = "%s/library/sections" % host
            if self.token:
                params = {'X-Plex-Token': self.token}
            else:
                params = False

            try:
                r = request.request_minidom(url, params=params)
                if not r:
                    logger.warn("Error getting Plex Media Server details, check settings (possibly incorrect token)")
                    return False

                sections = r.getElementsByTagName('Directory')

                if not sections:
                    logger.info("Plex Media Server not running on: " + host)
                    return False

                for s in sections:
                    if s.getAttribute('type') == "artist":
                        url = "%s/library/sections/%s/refresh" % (
                            host, s.getAttribute('key'))
                        request.request_response(url, params=params)

            except Exception as e:
                logger.error("Error getting Plex Media Server details: %s" % e)
                return False

    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.client_hosts.split(',')]

        header = "Headphones"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000"  # in ms

        for host in hosts:
            logger.info(
                'Sending notification command to Plex client @ ' + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties',
                                         {'properties': ['version']})[
                    'version']['major']

                if version < 12:  # Eden
                    notification = header + "," + message + "," + time + \
                        "," + albumartpath
                    notifycommand = {'command': 'ExecBuiltIn',
                                     'parameter': 'Notification(' +
                                                  notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': header, 'message': message,
                              'displaytime': int(time),
                              'image': albumartpath}
                    request = self._sendjson(host, 'GUI.ShowNotification',
                                             params)

                if not request:
                    raise Exception

            except Exception:
                logger.error(
                    'Error sending notification request to Plex client @ ' +
                    host)


class NMA(object):
    def notify(self, artist=None, album=None, snatched=None):
        title = 'Headphones'
        api = headphones.CONFIG.NMA_APIKEY
        nma_priority = headphones.CONFIG.NMA_PRIORITY

        logger.debug("NMA title: " + title)
        logger.debug("NMA API: " + api)
        logger.debug("NMA Priority: " + str(nma_priority))

        if snatched:
            event = snatched + " snatched!"
            message = "Headphones has snatched: " + snatched
        else:
            event = artist + ' - ' + album + ' complete!'
            message = "Headphones has downloaded and postprocessed: " + \
                      artist + ' [' + album + ']'

        logger.debug("NMA event: " + event)
        logger.debug("NMA message: " + message)

        batch = False

        p = pynma.PyNMA()
        keys = api.split(',')
        p.addkey(keys)

        if len(keys) > 1:
            batch = True

        response = p.push(title, event, message, priority=nma_priority,
                          batch_mode=batch)

        if not response[api]['code'] == '200':
            logger.error('Could not send notification to NotifyMyAndroid')
            return False
        else:
            return True


class PUSHBULLET(object):
    def __init__(self):
        self.apikey = headphones.CONFIG.PUSHBULLET_APIKEY
        self.deviceid = headphones.CONFIG.PUSHBULLET_DEVICEID

    def notify(self, message, status):
        if not headphones.CONFIG.PUSHBULLET_ENABLED:
            return

        url = "https://api.pushbullet.com/v2/pushes"

        data = {'type': "note",
                'title': "Headphones",
                'body': message + ': ' + status}

        if self.deviceid:
            data['device_iden'] = self.deviceid

        headers = {'Content-type': "application/json",
                   'Authorization': 'Bearer ' +
                                    headphones.CONFIG.PUSHBULLET_APIKEY}

        response = request.request_json(url, method="post", headers=headers,
                                        data=json.dumps(data))

        if response:
            logger.info("PushBullet notifications sent.")
            return True
        else:
            logger.info("PushBullet notification failed.")
            return False


class PUSHALOT(object):
    def notify(self, message, event):
        if not headphones.CONFIG.PUSHALOT_ENABLED:
            return

        pushalot_authorizationtoken = headphones.CONFIG.PUSHALOT_APIKEY

        logger.debug("Pushalot event: " + event)
        logger.debug("Pushalot message: " + message)
        logger.debug("Pushalot api: " + pushalot_authorizationtoken)

        http_handler = HTTPSConnection("pushalot.com")

        data = {'AuthorizationToken': pushalot_authorizationtoken,
                'Title': event.encode('utf-8'),
                'Body': message.encode("utf-8")}

        http_handler.request("POST",
                             "/api/sendmessage",
                             headers={
                                 'Content-type':
                                     "application/x-www-form-urlencoded"},
                             body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        logger.debug("Pushalot response status: %r" % request_status)
        logger.debug("Pushalot response headers: %r" % response.getheaders())
        logger.debug("Pushalot response body: %r" % response.read())

        if request_status == 200:
            logger.info("Pushalot notifications sent.")
            return True
        elif request_status == 410:
            logger.info("Pushalot auth failed: %s" % response.reason)
            return False
        else:
            logger.info("Pushalot notification failed.")
            return False


class JOIN(object):
    def __init__(self):

        self.enabled = headphones.CONFIG.JOIN_ENABLED
        self.apikey = headphones.CONFIG.JOIN_APIKEY
        self.deviceid = headphones.CONFIG.JOIN_DEVICEID
        self.url = 'https://joinjoaomgcd.appspot.com/_ah/' \
                   'api/messaging/v1/sendPush?apikey={apikey}' \
                   '&title={title}&text={text}' \
                   '&icon={icon}'

    def notify(self, message, event):
        if not headphones.CONFIG.JOIN_ENABLED or \
                not headphones.CONFIG.JOIN_APIKEY:
            return

        icon = "https://cdn.rawgit.com/Headphones/" \
               "headphones/develop/data/images/headphoneslogo.png"

        if not self.deviceid:
            self.deviceid = "group.all"
        l = [x.strip() for x in self.deviceid.split(',')]
        if len(l) > 1:
            self.url += '&deviceIds={deviceid}'
        else:
            self.url += '&deviceId={deviceid}'

        response = urllib.request.urlopen(self.url.format(apikey=self.apikey,
                                                          title=quote_plus(event),
                                                          text=quote_plus(
                                                              message.encode(
                                                                  "utf-8")),
                                                          icon=icon,
                                                          deviceid=self.deviceid))

        if response:
            logger.info("Join notifications sent.")
            return True
        else:
            logger.error("Join notification failed.")
            return False


class Synoindex(object):
    def __init__(self, util_loc='/usr/syno/bin/synoindex'):
        self.util_loc = util_loc

    def util_exists(self):
        return os.path.exists(self.util_loc)

    def notify(self, path):
        path = os.path.abspath(path)

        if not self.util_exists():
            logger.warn(
                "Error sending notification: synoindex utility "
                "not found at %s" % self.util_loc)
            return

        if os.path.isfile(path):
            cmd_arg = '-a'
        elif os.path.isdir(path):
            cmd_arg = '-A'
        else:
            logger.warn(
                "Error sending notification: Path passed to synoindex "
                "was not a file or folder.")
            return

        cmd = [self.util_loc, cmd_arg, path]
        logger.info("Calling synoindex command: %s" % str(cmd))
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 cwd=headphones.PROG_DIR)
            out, error = p.communicate()
            # synoindex never returns any codes other than '0',
            #  highly irritating
        except OSError as e:
            logger.warn("Error sending notification: %s" % str(e))

    def notify_multiple(self, path_list):
        if isinstance(path_list, list):
            for path in path_list:
                self.notify(path)


class PUSHOVER(object):
    def __init__(self):
        self.enabled = headphones.CONFIG.PUSHOVER_ENABLED
        self.keys = headphones.CONFIG.PUSHOVER_KEYS
        self.priority = headphones.CONFIG.PUSHOVER_PRIORITY

        if headphones.CONFIG.PUSHOVER_APITOKEN:
            self.application_token = headphones.CONFIG.PUSHOVER_APITOKEN
        else:
            self.application_token = "LdPCoy0dqC21ktsbEyAVCcwvQiVlsz"

    def conf(self, options):
        return cherrypy.config['config'].get('Pushover', options)

    def notify(self, message, event):
        if not headphones.CONFIG.PUSHOVER_ENABLED:
            return

        url = "https://api.pushover.net/1/messages.json"

        data = {'token': self.application_token,
                'user': headphones.CONFIG.PUSHOVER_KEYS,
                'title': event,
                'message': message.encode("utf-8"),
                'priority': headphones.CONFIG.PUSHOVER_PRIORITY}

        headers = {'Content-type': "application/x-www-form-urlencoded"}

        response = request.request_response(url, method="POST",
                                            headers=headers, data=data)

        if response:
            logger.info("Pushover notifications sent.")
            return True
        else:
            logger.error("Pushover notification failed.")
            return False

    def updateLibrary(self):
        # For uniformity reasons not removed
        return

    def test(self, keys, priority):
        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('Main Screen Activate', 'Test Message')


class TwitterNotifier(object):
    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'

    def __init__(self):
        self.consumer_key = "oYKnp2ddX5gbARjqX8ZAAg"
        self.consumer_secret = "A4Xkw9i5SjHbTk7XT8zzOPqivhj9MmRDR9Qn95YA9sk"

    def notify_snatch(self, title):
        if headphones.CONFIG.TWITTER_ONSNATCH:
            self._notifyTwitter(
                common.notifyStrings[
                    common.NOTIFY_SNATCH] + ': ' + title + ' at ' +
                helpers.now())

    def notify_download(self, title):
        if headphones.CONFIG.TWITTER_ENABLED:
            self._notifyTwitter(common.notifyStrings[
                common.NOTIFY_DOWNLOAD] + ': ' +
                title + ' at ' + helpers.now())

    def test_notify(self):
        return self._notifyTwitter(
            "This is a test notification from Headphones at " + helpers.now(),
            force=True)

    def _get_authorization(self):

        oauth_consumer = oauth.Consumer(key=self.consumer_key,
                                        secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        logger.info('Requesting temp token from Twitter')

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            logger.info(
                'Invalid respond from Twitter requesting temp token: %s' %
                resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            headphones.CONFIG.TWITTER_USERNAME = request_token['oauth_token']
            headphones.CONFIG.TWITTER_PASSWORD = request_token[
                'oauth_token_secret']

            return self.AUTHORIZATION_URL + "?oauth_token=" + request_token[
                'oauth_token']

    def _get_credentials(self, key):
        request_token = {}

        request_token['oauth_token'] = headphones.CONFIG.TWITTER_USERNAME
        request_token[
            'oauth_token_secret'] = headphones.CONFIG.TWITTER_PASSWORD
        request_token['oauth_callback_confirmed'] = 'true'

        token = oauth.Token(request_token['oauth_token'],
                            request_token['oauth_token_secret'])
        token.set_verifier(key)

        logger.info(
            'Generating and signing request for an access token using key ' +
            key)

        oauth_consumer = oauth.Consumer(key=self.consumer_key,
                                        secret=self.consumer_secret)
        logger.info('oauth_consumer: ' + str(oauth_consumer))
        oauth_client = oauth.Client(oauth_consumer, token)
        logger.info('oauth_client: ' + str(oauth_client))
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL,
                                             method='POST',
                                             body='oauth_verifier=%s' % key)
        logger.info('resp, content: ' + str(resp) + ',' + str(content))

        access_token = dict(parse_qsl(content))
        logger.info('access_token: ' + str(access_token))

        logger.info('resp[status] = ' + str(resp['status']))
        if resp['status'] != '200':
            logger.info('The request for a token with did not succeed: ' + str(
                resp['status']),
                logger.ERROR)
            return False
        else:
            logger.info('Your Twitter Access Token key: %s' % access_token[
                'oauth_token'])
            logger.info(
                'Access Token secret: %s' % access_token['oauth_token_secret'])
            headphones.CONFIG.TWITTER_USERNAME = access_token['oauth_token']
            headphones.CONFIG.TWITTER_PASSWORD = access_token[
                'oauth_token_secret']
            return True

    def _send_tweet(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        access_token_key = headphones.CONFIG.TWITTER_USERNAME
        access_token_secret = headphones.CONFIG.TWITTER_PASSWORD

        logger.info("Sending tweet: " + message)

        api = twitter.Api(username, password, access_token_key,
                          access_token_secret)

        try:
            api.PostUpdate(message)
        except Exception as e:
            logger.info("Error Sending Tweet: %s" % e)
            return False

        return True

    def _notifyTwitter(self, message='', force=False):
        prefix = headphones.CONFIG.TWITTER_PREFIX

        if not headphones.CONFIG.TWITTER_ENABLED and not force:
            return False

        return self._send_tweet(prefix + ": " + message)


class OSX_NOTIFY(object):
    def __init__(self):
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
        except:
            logger.warn('OS X Notification: Cannot import objc or AppKit')
            pass

    def swizzle(self, cls, SEL, func):
        old_IMP = getattr(cls, SEL, None)
        if old_IMP is None:
            old_IMP = cls.instanceMethodForSelector_(SEL)

        def wrapper(self, *args, **kwargs):
            return func(self, old_IMP, *args, **kwargs)

        new_IMP = self.objc.selector(
            wrapper,
            selector=old_IMP.selector,
            signature=old_IMP.signature
        )
        self.objc.classAddMethod(cls, SEL.encode(), new_IMP)

    def notify(self, title, subtitle=None, text=None, sound=True, image=None):

        try:
            self.swizzle(
                self.objc.lookUpClass('NSBundle'),
                'bundleIdentifier',
                self.swizzled_bundleIdentifier
            )

            NSUserNotification = self.objc.lookUpClass('NSUserNotification')
            NSUserNotificationCenter = self.objc.lookUpClass(
                'NSUserNotificationCenter')
            NSAutoreleasePool = self.objc.lookUpClass('NSAutoreleasePool')

            if not NSUserNotification or not NSUserNotificationCenter:
                return False

            pool = NSAutoreleasePool.alloc().init()

            notification = NSUserNotification.alloc().init()
            notification.setTitle_(title)
            if subtitle:
                notification.setSubtitle_(subtitle)
            if text:
                notification.setInformativeText_(text)
            if sound:
                notification.setSoundName_(
                    "NSUserNotificationDefaultSoundName")
            if image:
                source_img = self.AppKit.NSImage.alloc().\
                    initByReferencingFile_(image)
                notification.setContentImage_(source_img)
                # notification.set_identityImage_(source_img)
            notification.setHasActionButton_(False)

            notification_center = NSUserNotificationCenter.\
                defaultUserNotificationCenter()
            notification_center.deliverNotification_(notification)

            del pool
            return True

        except Exception as e:
            logger.warn('Error sending OS X Notification: %s' % e)
            return False

    def swizzled_bundleIdentifier(self, original, swizzled):
        return 'ade.headphones.osxnotify'


class BOXCAR(object):
    def __init__(self):
        self.url = 'https://new.boxcar.io/api/notifications'

    def notify(self, title, message, rgid=None):
        try:
            if rgid:
                message += '<br></br><a href="https://musicbrainz.org/' \
                           'release-group/%s">MusicBrainz</a>' % rgid

            data = urllib.parse.urlencode({
                'user_credentials': headphones.CONFIG.BOXCAR_TOKEN,
                'notification[title]': title.encode('utf-8'),
                'notification[long_message]': message.encode('utf-8'),
                'notification[sound]': "done",
                'notification[icon_url]': "https://raw.githubusercontent.com/rembo10/headphones/master/data/images"
                                          "/headphoneslogo.png"
            })

            req = urllib.request.Request(self.url)
            handle = urllib.request.urlopen(req, data)
            handle.close()
            return True

        except urllib.error.URLError as e:
            logger.warn('Error sending Boxcar2 Notification: %s' % e)
            return False


class SubSonicNotifier(object):
    def __init__(self):
        self.host = headphones.CONFIG.SUBSONIC_HOST
        self.username = headphones.CONFIG.SUBSONIC_USERNAME
        self.password = headphones.CONFIG.SUBSONIC_PASSWORD

    def notify(self, albumpaths):
        # Correct URL
        if not self.host.lower().startswith("http"):
            self.host = "http://" + self.host

        if not self.host.lower().endswith("/"):
            self.host = self.host + "/"

        # Invoke request
        request.request_response(
            self.host + "musicFolderSettings.view?scanNow",
            auth=(self.username, self.password))


class Email(object):
    def notify(self, subject, message):

        message = MIMEText(message, 'plain', "utf-8")
        message['Subject'] = subject
        message['From'] = email.utils.formataddr(
            ('Headphones', headphones.CONFIG.EMAIL_FROM))
        message['To'] = headphones.CONFIG.EMAIL_TO
        message['Date'] = email.utils.formatdate(localtime=True)

        try:
            if headphones.CONFIG.EMAIL_SSL:
                mailserver = smtplib.SMTP_SSL(
                    headphones.CONFIG.EMAIL_SMTP_SERVER,
                    headphones.CONFIG.EMAIL_SMTP_PORT)
            else:
                mailserver = smtplib.SMTP(headphones.CONFIG.EMAIL_SMTP_SERVER,
                                          headphones.CONFIG.EMAIL_SMTP_PORT)

            if headphones.CONFIG.EMAIL_TLS:
                mailserver.starttls()

            mailserver.ehlo()

            if headphones.CONFIG.EMAIL_SMTP_USER:
                mailserver.login(headphones.CONFIG.EMAIL_SMTP_USER,
                                 headphones.CONFIG.EMAIL_SMTP_PASSWORD)

            mailserver.sendmail(headphones.CONFIG.EMAIL_FROM,
                                headphones.CONFIG.EMAIL_TO,
                                message.as_string())
            mailserver.quit()
            return True

        except Exception as e:
            logger.warn('Error sending Email: %s' % e)
            return False


class TELEGRAM(object):
    def notify(self, message, status, rgid=None, image=None):
        if not headphones.CONFIG.TELEGRAM_ENABLED:
            return

        import requests

        TELEGRAM_API = "https://api.telegram.org/bot%s/%s"

        # Get configuration data
        token = headphones.CONFIG.TELEGRAM_TOKEN
        userid = headphones.CONFIG.TELEGRAM_USERID

        # Construct message
        message = '\n\n' + message

        # MusicBrainz link
        if rgid:
            message += '\n\n <a href="https://musicbrainz.org/' \
                'release-group/%s">MusicBrainz</a>' % rgid

        # Send image
        response = None
        if image:
            image_file = {'photo': (image, open(image, "rb"))}
            payload = {'chat_id': userid, 'parse_mode': "HTML", 'caption': status + message}
            try:
                response = requests.post(TELEGRAM_API % (token, "sendPhoto"), data=payload, files=image_file)
            except Exception as e:
                logger.info('Telegram notify failed: ' + str(e))
        # Sent text
        else:
            payload = {'chat_id': userid, 'parse_mode': "HTML", 'text': status + message}
            try:
                response = requests.post(TELEGRAM_API % (token, "sendMessage"), data=payload)
            except Exception as e:
                logger.info('Telegram notify failed: ' + str(e))

        # Error logging
        sent_successfuly = True
        if response and not response.status_code == 200:
            logger.info("Could not send notification to TelegramBot (token=%s). Response: [%s]", token, response.text)
            sent_successfuly = False

        logger.info("Telegram notifications sent.")
        return sent_successfuly


class SLACK(object):
    def notify(self, message, status):
        if not headphones.CONFIG.SLACK_ENABLED:
            return

        import requests

        SLACK_URL = headphones.CONFIG.SLACK_URL
        channel = headphones.CONFIG.SLACK_CHANNEL
        emoji = headphones.CONFIG.SLACK_EMOJI

        payload = {'channel': channel, 'text': status + ': ' + message,
                   'icon_emoji': emoji}

        try:
            response = requests.post(SLACK_URL, json=payload)
        except Exception as e:
            logger.info('Slack notify failed: ' + str(e))

        sent_successfuly = True
        if not response.status_code == 200:
            logger.info(
                'Could not send notification to Slack. Response: [%s]',
                (response.text))
            sent_successfuly = False

        logger.info("Slack notifications sent.")
        return sent_successfuly
