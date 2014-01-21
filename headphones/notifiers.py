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

from headphones import logger
import base64
import cherrypy
import urllib
import urllib2
import headphones
from httplib import HTTPSConnection
from urllib import urlencode
import os.path
import subprocess
import lib.simplejson as simplejson

class PROWL:

    keys = []
    priority = []

    def __init__(self):
        self.enabled = headphones.PROWL_ENABLED
        self.keys = headphones.PROWL_KEYS
        self.priority = headphones.PROWL_PRIORITY   
        pass

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

        username = self.username
        password = self.password
        
        url_command = urllib.urlencode(command)
        
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command
            
        req = urllib2.Request(url)
            
        if password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)
                
        logger.info('XBMC url: %s' % url)
            
        try:
            handle = urllib2.urlopen(req)
        except Exception, e:
            logger.warn('Error opening XBMC url: %s' % e)
            return
    
        response = handle.read().decode(headphones.SYS_ENCODING)
            
        return response
    
    def _sendjson(self, host, method, params={}):
        data = [{'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        data = simplejson.JSONEncoder().encode(data)

        content = {'Content-Type': 'application/json', 'Content-Length': len(data)}

        req = urllib2.Request(host+'/jsonrpc', data, content)

        if self.username and self.password:
            base64string = base64.encodestring('%s:%s' % (self.username, self.password)).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)

        try:
            handle = urllib2.urlopen(req)
        except Exception, e:
            logger.warn('Error opening XBMC url: %s' % e)
            return

        response = simplejson.JSONDecoder().decode(handle.read())

        try:
            return response[0]['result']
        except:
            logger.warn('XBMC returned error: %s' % response[0]['error'])
            return

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

class NMA:

    def __init__(self):
    
        self.apikey = headphones.NMA_APIKEY
        self.priority = headphones.NMA_PRIORITY
        
    def _send(self, data):
        
        url_data = urllib.urlencode(data)
        url = 'https://www.notifymyandroid.com/publicapi/notify'
        
        req = urllib2.Request(url, url_data)

        try:
            handle = urllib2.urlopen(req)
        except Exception, e:
            logger.warn('Error opening NotifyMyAndroid url: ' % e)
            return

        response = handle.read().decode(headphones.SYS_ENCODING)
        
        return response     
        
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
        
