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

import base64
import cherrypy
import urllib
import urllib2
import headphones
import simplejson
import os.path
import subprocess
import gntp.notifier
import time

from xml.dom import minidom
from httplib import HTTPSConnection
from urllib import urlencode

import lib.oauth2 as oauth
import lib.pythontwitter as twitter

from headphones import logger, helpers, common, request
from headphones.exceptions import ex

try:
    from urlparse import parse_qsl
except:
    from cgi import parse_qsl

class GROWL:

    def __init__(self):
        self.enabled = headphones.GROWL_ENABLED
        self.host = headphones.GROWL_HOST
        self.password = headphones.GROWL_PASSWORD

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
            logger.info(u'Growl notification failed: network error')
            return
        except gntp.notifier.errors.AuthError:
            logger.info(u'Growl notification failed: authentication error')
            return

        # Send it, including an image
        image_file = os.path.join(str(headphones.PROG_DIR), 'data/images/headphoneslogo.png')
        image = open(image_file, 'rb').read()

        try:
            growl.notify(
                noteType='New Event',
                title=event,
                description=message,
                icon=image
            )
        except gntp.notifier.errors.NetworkError:
            logger.info(u'Growl notification failed: network error')
            return

        logger.info(u"Growl notifications sent.")

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, host, password):
        self.enabled = True
        self.host = host
        self.password = password

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')

class PROWL:

    keys = []
    priority = []

    def __init__(self):
        self.enabled = headphones.PROWL_ENABLED
        self.keys = headphones.PROWL_KEYS
        self.priority = headphones.PROWL_PRIORITY   

    def conf(self, options):
        return cherrypy.config['config'].get('Prowl', options)

    def notify(self, message, event):
        if not headphones.PROWL_ENABLED:
            return

        http_handler = HTTPSConnection("api.prowlapp.com")
                                                
        data = {'apikey': headphones.PROWL_KEYS,
                'application': 'Headphones',
                'event': event,
                'description': message.encode("utf-8"),
                'priority': headphones.PROWL_PRIORITY }

        http_handler.request("POST",
                                "/publicapi/add",
                                headers = {'Content-type': "application/x-www-form-urlencoded"},
                                body = urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.info(u"Prowl notifications sent.")
                return True
        elif request_status == 401: 
                logger.info(u"Prowl auth failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Prowl notification failed.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, keys, priority):

        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')
        
class XBMC:

    def __init__(self):

        self.hosts = headphones.XBMC_HOST
        self.username = headphones.XBMC_USERNAME
        self.password = headphones.XBMC_PASSWORD

    def _sendhttp(self, host, command):
        url_command = urllib.urlencode(command)
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        if self.password:
            return request.request_content(url, auth=(self.username, self.password))
        else:
            return request.request_content(url)

    def _sendjson(self, host, method, params={}):
        data = [{'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.password:
            response = request.request_json(url, method="POST", data=simplejson.dumps(data), headers=headers, auth=(self.username, self.password))
        else:
            response = request.request_json(url, method="POST", data=simplejson.dumps(data), headers=headers)

        if response:
            return response[0]['result']

    def update(self):
        # From what I read you can't update the music library on a per directory or per path basis
        # so need to update the whole thing

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library update command to XBMC @ '+host)
            request = self._sendjson(host, 'AudioLibrary.Scan')
            
            if not request:
                logger.warn('Error sending update request to XBMC')
            
    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.hosts.split(',')]

        header = "Headphones"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to XMBC @ '+host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12: #Eden
                    notification = header + "," + message + "," + time + "," + albumartpath
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification('+notification+')'}
                    request = self._sendhttp(host, notifycommand)

                else: #Frodo
                    params = {'title':header, 'message': message, 'displaytime': int(time), 'image': albumartpath}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception

            except:
                logger.warn('Error sending notification request to XBMC')
class LMS:

#Class for updating a Logitech Media Server

    def __init__(self):
    
        self.hosts = headphones.LMS_HOST
    
    def _sendjson(self, host):
        data = {'id': 1, 'method': 'slim.request', 'params': ["",["rescan"]]} #Had a lot of trouble with simplejson, but this works.
        data = simplejson.JSONEncoder().encode(data)

        content = {'Content-Type': 'application/json', 'Content-Length': len(data)}

        req = urllib2.Request(host+'/jsonrpc.js', data, content)

        try:
            handle = urllib2.urlopen(req)
        except Exception, e:
            logger.warn('Error opening LMS url: %s' % e)
            return

        response = simplejson.JSONDecoder().decode(handle.read())
        server_result = simplejson.dumps(response)
        
        try:
            return response[0]['result']
        except:
            logger.warn('LMS returned error: %s' % response[0]['error'])
            return

    def update(self):
                    
		#Send the ["rescan"] command to an LMS server.
		#Note that the command must be prefixed with the 'player' that the command is aimed at,
		#But with this being a request for the server to update its library, the player is blank, so ""

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library rescan command to LMS @ '+host)
            request = self._sendjson(host)
            
            if not request:
                logger.warn('Error sending rescan request to LMS')

class Plex:

    def __init__(self):
    
        self.server_hosts = headphones.PLEX_SERVER_HOST
        self.client_hosts = headphones.PLEX_CLIENT_HOST
        self.username = headphones.PLEX_USERNAME
        self.password = headphones.PLEX_PASSWORD

    def _sendhttp(self, host, command):

        username = self.username
        password = self.password
        
        url_command = urllib.urlencode(command)
        
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command
            
        req = urllib2.Request(url)
            
        if password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)
                
        logger.info('Plex url: %s' % url)
            
        try:
            handle = urllib2.urlopen(req)
        except Exception, e:
            logger.warn('Error opening Plex url: %s' % e)
            return
    
        response = handle.read().decode(headphones.SYS_ENCODING)
            
        return response
    
    def update(self):
                    
        # From what I read you can't update the music library on a per directory or per path basis
        # so need to update the whole thing

        hosts = [x.strip() for x in self.server_hosts.split(',')]

        for host in hosts:
            logger.info('Sending library update command to Plex Media Server@ '+host)
            url = "%s/library/sections" % host
            try:
                xml_sections = minidom.parse(urllib.urlopen(url))
            except IOError, e:
                logger.warn("Error while trying to contact Plex Media Server: %s" % e)
                return False

            sections = xml_sections.getElementsByTagName('Directory')
            if not sections:
                logger.info(u"Plex Media Server not running on: " + host)
                return False

            for s in sections:
                if s.getAttribute('type') == "artist":
                    url = "%s/library/sections/%s/refresh" % (host, s.getAttribute('key'))
                    try:
                        urllib.urlopen(url)
                    except Exception, e:
                        logger.warn("Error updating library section for Plex Media Server: %s" % e)
                        return False
            
    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.client_hosts.split(',')]

        header = "Headphones"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to Plex Media Server @ '+host)
            try:
		notification = header + "," + message + "," + time + "," + albumartpath
		notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification('+notification+')'}
		request = self._sendhttp(host, notifycommand)

		if not request:
			raise Exception

            except:
                logger.warn('Error sending notification request to Plex Media Server')

class NMA:

    def __init__(self):
    
        self.apikey = headphones.NMA_APIKEY
        self.priority = headphones.NMA_PRIORITY
        
    def _send(self, data):
        return request.request_content('https://www.notifymyandroid.com/publicapi/notify', data=data)
        
    def notify(self, artist=None, album=None, snatched_nzb=None):
    
        apikey = self.apikey
        priority = self.priority
        
        if snatched_nzb:
            event = snatched_nzb + " snatched!"
            description = "Headphones has snatched: " + snatched_nzb + " and has sent it to SABnzbd+"
        else:
            event = artist + ' - ' + album + ' complete!'
            description = "Headphones has downloaded and postprocessed: " + artist + ' [' + album + ']'
    
        data = { 'apikey': apikey, 'application':'Headphones', 'event': event, 'description': description, 'priority': priority}

        logger.info('Sending notification request to NotifyMyAndroid')
        request = self._send(data)
        
        if not request:
            logger.warn('Error sending notification request to NotifyMyAndroid')        

class PUSHBULLET:

    def __init__(self):
        self.apikey = headphones.PUSHBULLET_APIKEY
        self.deviceid = headphones.PUSHBULLET_DEVICEID

    def conf(self, options):
        return cherrypy.config['config'].get('PUSHBULLET', options)

    def notify(self, message, event):
        if not headphones.PUSHBULLET_ENABLED:
            return

        http_handler = HTTPSConnection("api.pushbullet.com")
                                                
        data = {'device_iden': headphones.PUSHBULLET_DEVICEID,
                'type': "note",
                'title': "Headphones",
                'body': message.encode("utf-8") }

        http_handler.request("POST",
                                "/api/pushes",
                                headers = {'Content-type': "application/x-www-form-urlencoded",
                                            'Authorization' : 'Basic %s' % base64.b64encode(headphones.PUSHBULLET_APIKEY + ":") },
                                body = urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status
        logger.debug(u"PushBullet response status: %r" % request_status)
        logger.debug(u"PushBullet response headers: %r" % response.getheaders())
        logger.debug(u"PushBullet response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"PushBullet notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500: 
                logger.info(u"PushBullet request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"PushBullet notification failed serverside.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, apikey, deviceid):

        self.enabled = True
        self.apikey = apikey
        self.deviceid = deviceid

        self.notify('Main Screen Activate', 'Test Message')

        
class PUSHALOT:

    def notify(self, message, event):
        if not headphones.PUSHALOT_ENABLED:
            return

	pushalot_authorizationtoken = headphones.PUSHALOT_APIKEY

	logger.debug(u"Pushalot event: " + event)
	logger.debug(u"Pushalot message: " + message)
	logger.debug(u"Pushalot api: " + pushalot_authorizationtoken)

        http_handler = HTTPSConnection("pushalot.com")
                                                
        data = {'AuthorizationToken': pushalot_authorizationtoken, 
                'Title': event.encode('utf-8'),
                'Body': message.encode("utf-8") }

        http_handler.request("POST",
                                "/api/sendmessage",
                                headers = {'Content-type': "application/x-www-form-urlencoded"},
                                body = urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        logger.debug(u"Pushalot response status: %r" % request_status)
        logger.debug(u"Pushalot response headers: %r" % response.getheaders())
        logger.debug(u"Pushalot response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"Pushalot notifications sent.")
                return True
        elif request_status == 410: 
                logger.info(u"Pushalot auth failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Pushalot notification failed.")
                return False

class Synoindex:
    def __init__(self, util_loc='/usr/syno/bin/synoindex'):
        self.util_loc = util_loc

    def util_exists(self):
        return os.path.exists(self.util_loc)

    def notify(self, path):
        path = os.path.abspath(path)

        if not self.util_exists():
            logger.warn("Error sending notification: synoindex utility not found at %s" % self.util_loc)
            return

        if os.path.isfile(path):
            cmd_arg = '-a'
        elif os.path.isdir(path):
            cmd_arg = '-A'
        else:
            logger.warn("Error sending notification: Path passed to synoindex was not a file or folder.")
            return

        cmd = [self.util_loc, cmd_arg, path]
        logger.info("Calling synoindex command: %s" % str(cmd))
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=headphones.PROG_DIR)
            out, error = p.communicate()
            #synoindex never returns any codes other than '0', highly irritating
        except OSError, e:
            logger.warn("Error sending notification: %s" % str(e))

    def notify_multiple(self, path_list):
        if isinstance(path_list, list):
            for path in path_list:
                self.notify(path)
class PUSHOVER:

    application_token = "LdPCoy0dqC21ktsbEyAVCcwvQiVlsz"
    keys = []
    priority = []

    def __init__(self):
        self.enabled = headphones.PUSHOVER_ENABLED
        self.keys = headphones.PUSHOVER_KEYS
        self.priority = headphones.PUSHOVER_PRIORITY   
        if headphones.PUSHOVER_APITOKEN:
            self.application_token = headphones.PUSHOVER_APITOKEN
        pass

    def conf(self, options):
        return cherrypy.config['config'].get('Pushover', options)

    def notify(self, message, event):
        if not headphones.PUSHOVER_ENABLED:
            return

        http_handler = HTTPSConnection("api.pushover.net")
                                                
        data = {'token': self.application_token, 
                'user': headphones.PUSHOVER_KEYS,
                'title': event,
                'message': message.encode("utf-8"),
                'priority': headphones.PUSHOVER_PRIORITY }

        http_handler.request("POST",
                                "/1/messages.json",
                                headers = {'Content-type': "application/x-www-form-urlencoded"},
                                body = urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status
        logger.debug(u"Pushover response status: %r" % request_status)
        logger.debug(u"Pushover response headers: %r" % response.getheaders())
        logger.debug(u"Pushover response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"Pushover notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500: 
                logger.info(u"Pushover request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Pushover notification failed.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, keys, priority):

        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('Main Screen Activate', 'Test Message')
        
class TwitterNotifier:

    consumer_key = "oYKnp2ddX5gbARjqX8ZAAg"
    consumer_secret = "A4Xkw9i5SjHbTk7XT8zzOPqivhj9MmRDR9Qn95YA9sk"
    
    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'
    
    def notify_snatch(self, title):
        if headphones.TWITTER_ONSNATCH:
            self._notifyTwitter(common.notifyStrings[common.NOTIFY_SNATCH]+': '+title+' at '+helpers.now())

    def notify_download(self, title):
        if headphones.TWITTER_ENABLED:
            self._notifyTwitter(common.notifyStrings[common.NOTIFY_DOWNLOAD]+': '+title+' at '+helpers.now())

    def test_notify(self):
        return self._notifyTwitter("This is a test notification from Headphones at "+helpers.now(), force=True)

    def _get_authorization(self):
    
        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1() #@UnusedVariable
        oauth_consumer             = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client               = oauth.Client(oauth_consumer)
    
        logger.info('Requesting temp token from Twitter')
    
        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')
    
        if resp['status'] != '200':
            logger.info('Invalid respond from Twitter requesting temp token: %s' % resp['status'])
        else:
            request_token = dict(parse_qsl(content))
    
            headphones.TWITTER_USERNAME = request_token['oauth_token']
            headphones.TWITTER_PASSWORD = request_token['oauth_token_secret']
    
            return self.AUTHORIZATION_URL+"?oauth_token="+ request_token['oauth_token']
    
    def _get_credentials(self, key):
        request_token = {}
    
        request_token['oauth_token'] = headphones.TWITTER_USERNAME
        request_token['oauth_token_secret'] = headphones.TWITTER_PASSWORD
        request_token['oauth_callback_confirmed'] = 'true'
    
        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)
    
        logger.info('Generating and signing request for an access token using key '+key)
    
        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1() #@UnusedVariable
        oauth_consumer             = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        logger.info('oauth_consumer: '+str(oauth_consumer))
        oauth_client  = oauth.Client(oauth_consumer, token)
        logger.info('oauth_client: '+str(oauth_client))
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        logger.info('resp, content: '+str(resp)+','+str(content))
    
        access_token  = dict(parse_qsl(content))
        logger.info('access_token: '+str(access_token))
    
        logger.info('resp[status] = '+str(resp['status']))
        if resp['status'] != '200':
            logger.info('The request for a token with did not succeed: '+str(resp['status']), logger.ERROR)
            return False
        else:
            logger.info('Your Twitter Access Token key: %s' % access_token['oauth_token'])
            logger.info('Access Token secret: %s' % access_token['oauth_token_secret'])
            headphones.TWITTER_USERNAME = access_token['oauth_token']
            headphones.TWITTER_PASSWORD = access_token['oauth_token_secret']
            return True
    
    
    def _send_tweet(self, message=None):
    
        username=self.consumer_key
        password=self.consumer_secret
        access_token_key=headphones.TWITTER_USERNAME
        access_token_secret=headphones.TWITTER_PASSWORD
    
        logger.info(u"Sending tweet: "+message)
    
        api = twitter.Api(username, password, access_token_key, access_token_secret)
    
        try:
            api.PostUpdate(message)
        except Exception, e:
            logger.info(u"Error Sending Tweet: %s" % e)
            return False
    
        return True
    
    def _notifyTwitter(self, message='', force=False):
        prefix = headphones.TWITTER_PREFIX
    
        if not headphones.TWITTER_ENABLED and not force:
            return False
    
        return self._send_tweet(prefix+": "+message)

notifier = TwitterNotifier

API_URL = "https://boxcar.io/devices/providers/WqbewHpV8ZATnawpCsr4/notifications"

class BOXCAR:

    def test_notify(self, email, title="Test"):
        return self._sendBoxcar("This is a test notification from Headphones", title, email)

    def _sendBoxcar(self, msg, title, email, subscribe=False):
        """
	Sends a boxcar notification to the address provided

	msg: The message to send (unicode)
	title: The title of the message
	email: The email address to send the message to (or to subscribe with)
	subscribe: If true then instead of sending a message this function will send a subscription notificat$

	returns: True if the message succeeded, False otherwise
	"""

        # build up the URL and parameters
        msg = msg.strip()
        curUrl = API_URL
        # if this is a subscription notification then act accordingly
        if subscribe:
            data = urllib.urlencode({'email': email})
            curUrl = curUrl + "/subscribe"
        # for normal requests we need all these parameters
        else:
            data = urllib.urlencode({
                'email': email,
                'notification[from_screen_name]': title,
                'notification[message]': msg.encode('utf-8'),
                'notification[from_remote_service_id]': int(time.time())
                })

	logger.info(data)
        # send the request to boxcar
        try:
            req = urllib2.Request(curUrl)
            handle = urllib2.urlopen(req, data)
            handle.close()

        except urllib2.URLError, e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.error("Boxcar notification failed." + ex(e))
                return False
            else:
                logger.error("Boxcar notification failed. Error code: " + str(e.code))

            # HTTP status 404 if the provided email address isn't a Boxcar user.
            if e.code == 404:
                logger.error("Username is wrong/not a boxcar email. Boxcar will send an email to it")
                return False

            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added$
            elif e.code == 401:

                # If the user has already added your service, we'll return an HTTP status code of 401.
                if subscribe:
                    logger.error("Already subscribed to service")
                    # i dont know if this is true or false ... its neither but i also dont know how we got here in the first $
                    return False

                #HTTP status 401 if the user doesn't have the service added
                else:
                    subscribeNote = self._sendBoxcar(msg, title, email, True)
                    if subscribeNote:
                        logger.info("Subscription send")
                        return True
                    else:
                        logger.info("Subscription could not be send")
                        return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.info("Wrong data sent to boxcar")
                logger.info('data:' + data)
                return False

        logger.fdebug("Boxcar notification successful.")
        return True

    def notify(self, artist=None, album=None, snatched_nzb=None, username=None, force=False):
        """
	Sends a boxcar notification based on the provided info or SB config

	title: The title of the notification to send
	message: The message string to send
	username: The username to send the notification to (optional, defaults to the username in the config)
	force: If True then the notification will be sent even if Boxcar is disabled in the config
	"""
        if not headphones.BOXCAR_ENABLED and not force:
            logger.fdebug("Notification for Boxcar not enabled, skipping this notification")
            return False

        # if no username was given then use the one from the config
        if not username:
            username = headphones.BOXCAR_USERNAME

        if snatched_nzb:
            title = "Headphones. Sucessfully Snatched!"
            message = u"Headphones has snatched: " + snatched_nzb + " and has sent it to SABnzbd+"
        else:
            title = "Headphones. Successfully Downloaded & Post-Processed!"
            message = u"Headphones has downloaded and postprocessed: " + artist + ' [' + album + ']'

        logger.info("Sending notification to Boxcar")

        self._sendBoxcar(message, title, username)
        return True


