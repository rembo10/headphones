# -*- coding: latin-1 -*-
# Author: Guillaume Serre <guillaume.serre@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import urllib2
import cookielib
from urlparse import urlparse
from bs4 import BeautifulSoup
from headphones import logger, db
import lib.bencode as bencode
import os
import headphones

class T411():

    def __init__(self):
        
                
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        
        self.url = "http://www.t411.me"
        
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
            searchparams = urllib.urlencode( {'search': searchterm, 'cat' : 395, 'submit' : 'Recherche', 'subcat': 623} ) + "&term%5B16%5D%5B%5D=529"
        elif format == 'lossless+mp3':
            searchparams = urllib.urlencode( {'search': searchterm, 'cat' : 395, 'submit' : 'Recherche', 'subcat': 623 } ) + "&term%5B16%5D%5B%5D=529&term%5B16%5D%5B%5D=533&term%5B16%5D%5B%5D=685&term%5B16%5D%5B%5D=534&term%5B16%5D%5B%5D=527"
        else:
            searchparams= urllib.urlencode( {'search': searchterm, 'cat' : 395, 'submit' : 'Recherche', 'subcat': 623 } ) + "&term%5B16%5D%5B%5D=533&term%5B16%5D%5B%5D=685&term%5B16%5D%5B%5D=534&term%5B16%5D%5B%5D=527"

        searchurl = self.url + '/torrents/search/?' + searchparams
              
        
        return searchurl
        
      
    def _doLogin(self, login, password):

        data = urllib.urlencode({'login': login, 'password' : password, 'submit' : 'Connexion', 'remember': 1, 'url' : '/'})
        self.opener.open(self.url + '/users/login', data)
    
    def search(self, searchurl, maxsize, minseeders, albumid, bitrate):
        
        if not self.login_done:
            self._doLogin( headphones.T411_LOGIN, headphones.T411_PASSWORD )

        results = []
        logger.debug(u"Search string: " + searchurl)
        
        r = self.opener.open( searchurl )
        soup = BeautifulSoup( r, "html.parser" )
        resultsTable = soup.find("table", { "class" : "results" })
        if resultsTable:
            rows = resultsTable.find("tbody").findAll("tr")
    
            for row in rows:
                link = row.find("a", title=True)
                title = link['title']
                id = row.find_all('td')[2].find_all('a')[0]['href'][1:].replace('torrents/nfo/?id=','')
                downloadURL = ('http://www.t411.me/torrents/download/?id=%s' % id)
                
                
                results.append( T411SearchResult( self.opener, link['title'], downloadURL ) )
                
                
        return results
    
    def get_torrent(self, url, savelocation,torrent_name):
    
                          
        torrent_name = torrent_name + '.torrent'
        download_path = os.path.join(savelocation, torrent_name)
        
        try:
            page = self.opener.open(url)
            torrent = page.read()
            fp = open (download_path, 'wb')
            fp.write (torrent)
            fp.close ()                        
            os.chmod(download_path, 777)
        except Exception, e:
            logger.error('Error getting torrent: %s' % e)  
            return False      
        
        return download_path
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.TorrentDataSearchResult(episodes)
        result.provider = self

        return result    
    
class T411SearchResult:
    
    def __init__(self, opener, title, url):
        self.opener = opener
        self.title = title
        self.url = url
        
    def getNZB(self):
        return self.opener.open( self.url , 'wb').read()


provider = T411()
