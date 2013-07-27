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

## uTorrentAPI class taken from CouchPotatoServer
## http://github.com/RuudBurger/CouchPotatoServer

class uTorrentAPI(object):

    def __init__(self, host = 'localhost', port = 8000, username = None, password = None):

        super(uTorrentAPI, self).__init__()

        self.url = 'http://' + str(host) + ':' + str(port) + '/gui/'
        self.token = ''
        self.last_time = time.time()
        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)
        self.opener.addheaders = [('User-agent', 'couchpotato-utorrent-client/1.0')]
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm = None, uri = self.url, user = username, passwd = password)
            self.opener.add_handler(urllib2.HTTPBasicAuthHandler(password_manager))
            self.opener.add_handler(urllib2.HTTPDigestAuthHandler(password_manager))
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.token = self.get_token()

    def _request(self, action, data = None):
        if time.time() > self.last_time + 1800:
            self.last_time = time.time()
            self.token = self.get_token()
        request = urllib2.Request(self.url + "?token=" + self.token + "&" + action, data)
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            if response:
                return response
            else:
                log.debug('Unknown failure sending command to uTorrent. Return text is: %s', response)
        except httplib.InvalidURL, err:
            log.error('Invalid uTorrent host, check your config %s', err)
        except urllib2.HTTPError, err:
            if err.code == 401:
                log.error('Invalid uTorrent Username or Password, check your config')
            else:
                log.error('uTorrent HTTPError: %s', err)
        except urllib2.URLError, err:
            log.error('Unable to connect to uTorrent %s', err)
        return False

    def get_token(self):
        request = self.opener.open(self.url + "token.html")
        token = re.findall("<div.*?>(.*?)</", request.read())[0]
        return token

    def add_torrent_uri(self, torrent):
        action = "action=add-url&s=%s" % urllib.quote(torrent)
        return self._request(action)

    def add_torrent_file(self, filename, filedata):
        action = "action=add-file"
        return self._request(action, {"torrent_file": (ss(filename), filedata)})

    def set_torrent(self, hash, params):
        action = "action=setprops&hash=%s" % hash
        for k, v in params.iteritems():
            action += "&s=%s&v=%s" % (k, v)
        return self._request(action)

    def pause_torrent(self, hash):
        action = "action=pause&hash=%s" % hash
        return self._request(action)

    def get_status(self):
        action = "list=1"
        return self._request(action)

    def get_settings(self):
        action = "action=getsettings"
        settings_dict = {}
        try:
            utorrent_settings = json.loads(self._request(action))

            # Create settings dict
            for item in utorrent_settings['settings']:
                if item[1] == 0: # int
                    settings_dict[item[0]] = int(item[2] if not item[2].strip() == '' else '0')
                elif item[1] == 1: # bool
                    settings_dict[item[0]] = True if item[2] == 'true' else False
                elif item[1] == 2: # string
                    settings_dict[item[0]] = item[2]

            #log.debug('uTorrent settings: %s', settings_dict)

        except Exception, err:
            log.error('Failed to get settings from uTorrent: %s', err)

        return settings_dict
