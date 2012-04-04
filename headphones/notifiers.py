from headphones import logger
import base64
import cherrypy
import urllib
import urllib2
import headphones
from httplib import HTTPSConnection
from urllib import urlencode

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
		
	def _send(self, command):
		
		hosts = [x.strip() for x in self.hosts.split(',')]
		username = self.username
		password = self.password
		
		url_command = urllib.urlencode(command)
		
		for host in hosts:
		
			url = host + '/xbmcCmds/xbmcHttp/?' + url_command
			
			req = urllib2.Request(url)
			
			if password:
				base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
				req.add_header("Authorization", "Basic %s" % base64string)
				
			logger.info('XBMC url: %s' % url)
			
			try:
				handle = urllib2.urlopen(req)
			except Exception, e:
				logger.warn('Error opening XBMC url: ' % e)
				return
	
			response = handle.read().decode(headphones.SYS_ENCODING)
			
			return response
    
	def update(self):
					
		# From what I read you can't update the music library on a per directory or per path basis
		# so need to update the whole thing
		
		updatecommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(music)'}
		
		logger.info('Sending library update command to XBMC')
		request = self._send(updatecommand)
		
		if not request:
			logger.warn('Error sending update request to XBMC')
			
	def notify(self, artist, album, albumartpath):
	
		header = "Headphones"
		message = "%s - %s added to your library" % (artist, album)
		time = "3000" # in ms
		
		
		notification = header + "," + message + "," + time + "," + albumartpath
		
		notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')' }
		
		logger.info('Sending notification command to XMBC')
		request = self._send(notifycommand)
		
		if not request:
			logger.warn('Error sending notification request to XBMC')