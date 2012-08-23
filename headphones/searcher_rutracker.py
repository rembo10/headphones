#!/usr/bin/env python
# coding=utf-8

# Headphones rutracker.org search
# Functions called from searcher.py
# Requires BeautifulSoup 4 for parsing http://www.crummy.com/software/BeautifulSoup/

import urllib
import urllib2
import cookielib
from urlparse import urlparse
from bs4 import BeautifulSoup
from headphones import logger, db
import lib.bencode as bencode
import os

class Rutracker():

    logged_in = False
    # Stores a number of login attempts to prevent recursion.
    login_counter = 0
    
    def __init__(self):

        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        urllib2.install_opener(self.opener)

    def login(self, login, password):
        """Implements tracker login procedure."""
        
        self.logged_in = False

        if login is None or password is None:
            return False

        self.login_counter += 1
        
        # No recursion wanted.
        #if self.login_counter > 1:
        #    return False
        
        params = urllib.urlencode({"login_username" : login,
                                   "login_password" : password,
                                   "login" : "Вход"})

        try:
            self.opener.open("http://login.rutracker.org/forum/login.php", params)
        except :
            pass
            
        # Check if we're logged in
        
        for cookie in self.cookiejar:
            if cookie.name == 'bb_data':
                self.logged_in = True
        
        return self.logged_in

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
        searchterm = searchterm + year
        
        providerurl = "http://rutracker.org/forum/tracker.php"
        
        if format == 'lossless':
            format = '+lossless'
        elif format == 'lossless+mp3':
            format = '+lossless||mp3||aac'
        else:
            format = '+mp3||aac'
            
        # sort by size, descending. 
        
        sort = '&o=7&s=2'
        
        searchurl = "%s?nm=%s%s%s" % (providerurl, urllib.quote(searchterm), format, sort)
        
        return searchurl
    
    def search(self, searchurl, maxsize, minseeders, albumid, bitrate):
        """
        Parse the search results and return the first valid torrent
        """
        
        titles = []
        urls = []
        seeders = []
        sizes = []
        torrentlist = [] 
        rulist = []
        
        try:
            
            page = self.opener.open(searchurl, timeout=60)
            soup = BeautifulSoup(page.read(), from_encoding="utf-8")
            
            # Debug
            #logger.debug (soup.prettify()) 
            
            # Title
             
            for link in soup.find_all('a', attrs={'class' : 'med tLink bold'}): 
                title = link.get_text()
                titles.append(title)
            
            # Download URL

            for link in soup.find_all('a', attrs={'class' : 'small tr-dl dl-stub'}):
                url = link.get('href')
                urls.append(url)
                
            # Seeders
             
            for link in soup.find_all('td', attrs={'class' : 'row4 seedmed'}): 
                seeder = link.get_text()
                seeders.append(seeder)
            
            # Size
             
            for link in soup.find_all('td', attrs={'class' : 'row4 small nowrap tor-size'}): 
                size = link.u.string
                sizes.append(size)
                
        except :
            pass
            
        # Combine lists
        
        torrentlist = zip(titles, urls, seeders, sizes)
        
        # return if nothing found
        
        if not torrentlist:
            return False
            
         # get headphones track count for album, return if not found
        
        hptrackcount = 0
        
        myDB = db.DBConnection()
        tracks = myDB.select('SELECT TrackTitle from tracks WHERE AlbumID=?', [albumid])
        for track in tracks:
            hptrackcount += 1
        
        if not hptrackcount:
            logger.info('headphones track info not found, cannot compare to torrent') 
            return False
        
        # Return the first valid torrent, unless we want a preferred bitrate then we want all valid entries
       
        for torrent in torrentlist:
            
            title = torrent[0]
            url = torrent[1]
            seeders = torrent[2]
            size = torrent[3]
            
            # Attempt to filter out unwanted
            
            if 'Promo' not in title and 'promo' not in title and 'Vinyl' not in title and 'vinyl' not in title \
              and 'ongbook' not in title and 'TVRip' not in title and 'HDTV' not in title and 'DVD' not in title \
              and int(size) <= maxsize and int(seeders) >= minseeders:
                     
                # Check torrent info
                
                torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
                self.cookiejar.set_cookie(cookielib.Cookie(version=0, name='bb_dl', value=torrent_id, port=None, port_specified=False, domain='.rutracker.org', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False))
                                          
                # Debug
                for cookie in self.cookiejar:
                    logger.debug ('Cookie: %s' % cookie) 
                     
                try:
                    page = self.opener.open(url)
                    torrent = page.read()
                    if torrent:
                        decoded = bencode.bdecode(torrent)
                        metainfo = decoded['info']
                    page.close ()
                except Exception, e:
                    logger.error('Error getting torrent: %s' % e)  
                    return False      
                
                # get torrent track count
                
                trackcount = 0
                
                if 'files' in metainfo: # multi
                    for pathfile in metainfo['files']:
                        path = pathfile['path']
                        for file in path:
                            if '.ape' in file or '.flac' in file or '.ogg' in file or '.m4a' in file or '.aac' in file or '.mp3' in file or '.wav' in file or '.aif' in file:
                                trackcount += 1
                            
                logger.debug ('torrent title: %s' % title)
                logger.debug ('hp trackcount: %s' % hptrackcount) 
                logger.debug ('torrent trackcount: %s' % trackcount)
                
                #Torrent topic page
        
                topicurl = 'http://rutracker.org/forum/viewtopic.php?t=' + torrent_id
                
                # If torrent track count = hp track count then return torrent, 
                # if greater, check for deluxe/special/foreign editions
                
                valid = False
                
                if trackcount == hptrackcount:
                    valid = True
                elif trackcount > hptrackcount:
                    if 'eluxe' in title or 'dition' in title or 'apanese' in title or 'elease' in title:
                        valid = True
                        
                # return 1st valid torrent if not checking by bitrate, else add to list and return at end
                
                if valid:
                    rulist.append((title, size, topicurl))
                    if not bitrate:
                        return rulist
                         
        return rulist


    def get_torrent(self, url, savelocation):
    
        torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
        self.cookiejar.set_cookie(cookielib.Cookie(version=0, name='bb_dl', value=torrent_id, port=None, port_specified=False, domain='.rutracker.org', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False))
        downloadurl = 'http://dl.rutracker.org/forum/dl.php?t=' + torrent_id                  
        torrent_name = torrent_id + '.torrent'
        download_path = os.path.join(savelocation, torrent_name)
        
        try:
            page = self.opener.open(downloadurl)
            torrent = page.read()
            fp = open (download_path, 'wb')
            fp.write (torrent)
            fp.close ()
        except Exception, e:
            logger.error('Error getting torrent: %s' % e)  
            return False      
        
        return download_path
        
