# -*- coding: latin-1 -*-
import urllib
import urllib2
import cookielib
from urlparse import urlparse
from bs4 import BeautifulSoup
from headphones import logger, db
from bencode import bencode as bencode, bdecode
from tempfile import mkdtemp
from hashlib import sha1
import os
import headphones
import re
import json

class FTDB():

    def __init__(self):
        
                
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        
        self.url = "http://www.frenchtorrentdb.com"
        
        self.login_done = False
        
    def searchurl(self, artist, album, year, format):
        
        """
        Return the search url
        """
         
        # Build search url
        
        searchterm = ''
        if artist != 'Various Artists':
            searchterm = artist
            searchterm = searchterm + ' '
        searchterm = searchterm + album
        searchterm = searchterm + ' '
        
        
        if format == "lossless":
            category='&adv_cat%5Bm%5D%5B2%5D=194'
        elif format == 'lossless+mp3':
            category='&adv_cat%5Bm%5D%5B2%5D=194&adv_cat%5Bm%5D%5B1%5D=117'
        else:
            category='&adv_cat%5Bm%5D%5B1%5D=117'
        searchurl=urllib.urlencode( {'name': searchterm, 'exact':1, 'group': 'musiques'})+category
        
        return searchurl
        
      
    def _doLogin(self, login, password):

        challenge = self.opener.open(self.url + '/?section=LOGIN&challenge=1')

        rawData = challenge.read()

        data = json.loads(rawData)

        data = urllib.urlencode({
            'username'    : login,
            'password'    : password,
            'secure_login': self._getSecureLogin(data['challenge']),
            'hash'        : data['hash']
        })

        self.opener.open(self.url + '/?section=LOGIN&ajax=1', data).read()
        self.login_done = self.opener
    
    def _getSecureLogin(self, challenges):

        def fromCharCode(*args):
            return ''.join(map(unichr, args))

        def decodeString(p, a, c, k, e, d):
            a = int(a)
            c = int(c)
            def e(c):
                if c < a:
                    f = ''
                else:
                    f = e(c / a)
                return f + fromCharCode(c % a + 161)
            while c:
                c -= 1
                if k[c]:
                    regex = re.compile(e(c))
                    p = re.sub(regex, k[c], p)
            return p

        def decodeChallenge(challenge):
            challenge      = urllib2.unquote(challenge)
            regexGetArgs   = re.compile('\'([^\']+)\',([0-9]+),([0-9]+),\'([^\']+)\'')
            regexIsEncoded = re.compile('decodeURIComponent')
            regexUnquote   = re.compile('\'')
            if (challenge == 'a'):
                return '05f'
            if (re.match(regexIsEncoded, challenge) == None):
                return re.sub(regexUnquote, '', challenge)
            args = re.findall(regexGetArgs, challenge)
            decoded = decodeString(args[0][0], args[0][1], args[0][2], args[0][3].split('|'), 0, {})
            return urllib2.unquote(decoded.decode('utf8'))

        secureLogin = ''
        for challenge in challenges:
            secureLogin += decodeChallenge(challenge)
        return secureLogin
       
    def search(self, searchurl, maxsize, minseeders, albumid, bitrate):
        
        if not self.login_done:
            self._doLogin( headphones.CONFIG.FTDB_LOGIN, headphones.CONFIG.FTDB_PASSWORD )

        results = []
        logger.debug(u"Search string: " + searchurl)
        URL = self.url + '/?section=TORRENTS&' + searchurl.replace('!','')
        r = self.opener.open(URL)   
        soup = BeautifulSoup( r, "html5lib" )
        resultsTable = soup.find("div", { "class" : "DataGrid" })
        if resultsTable:
            rows = resultsTable.findAll("ul")
            for row in rows:
                link = row.find("a", title=True)
                title = link['title']
                size= row.findAll('li')[3].text
                size = parseSize(size)
                size = tryInt(size)
                leecher=row.findAll('li')[5].text
                seeder=row.findAll('li')[4].text
                seeders = tryInt(seeder)
                autogetURL = self.url +'/'+ (row.find("li", { "class" : "torrents_name"}).find('a')['href'][1:]).replace('#FTD_MENU','&menu=4')
                r = self.opener.open( autogetURL , 'wb').read()
                soup = BeautifulSoup( r, "html5lib" )
                downloadURL = soup.find("div", { "class" : "autoget"}).find('a')['href']
                
                results.append( FTDBSearchResult( self.opener, title, downloadURL,size, seeders) )
        return results

def parseSize(size):
        
        sizeGb = ['gb', 'gib', 'go']
        sizeMb = ['mb', 'mib', 'mo']
        sizeKb = ['kb', 'kib', 'ko']
        
        sizeRaw = size.lower()
        size = tryFloat(re.sub(r'[^0-9.]', '', size).strip())

        for s in sizeGb:
            if s in sizeRaw:
                return size * 1024 * 1048576

        for s in sizeMb:
            if s in sizeRaw:
                return size * 1048576

        for s in sizeKb:
            if s in sizeRaw:
                return size /1024 *1048576

        return
def tryInt(s):
    try: return int(s)
    except: return 0

def tryFloat(s):
    try: return float(s) if '.' in s else tryInt(s)
    except: return 0
    
class FTDBSearchResult:
    
    def __init__(self, opener, title, url, size, seeders):
        self.opener = opener
        self.title = title
        self.url = url
        self.size = size
        self.seeders = seeders

provider = FTDB()
