#!/usr/bin/env python

import urllib
import requests as requests
from urlparse import urlparse
from bs4 import BeautifulSoup

import os
import time
import re

import headphones
from headphones import logger

class Rutracker(object):

    def __init__(self):
        self.session = requests.session()
        self.timeout = 60
        self.loggedin = False
        self.maxsize = 0
        self.search_referer = 'http://rutracker.org/forum/tracker.php'

    def logged_in(self):
        return self.loggedin

    def still_logged_in(self, html):
        if not html or "action=\"http://login.rutracker.org/forum/login.php\">" in html:
            return False
        else:
            return True

    def login(self):
        """
        Logs in user
        """

        loginpage = 'http://login.rutracker.org/forum/login.php'
        post_params = {
            'login_username': headphones.CONFIG.RUTRACKER_USER,
            'login_password': headphones.CONFIG.RUTRACKER_PASSWORD,
            'login': b'\xc2\xf5\xee\xe4'  # '%C2%F5%EE%E4'
        }

        logger.info("Attempting to log in to rutracker...")

        try:
            r = self.session.post(loginpage, data=post_params, timeout=self.timeout)
            # try again
            if 'bb_data' not in r.cookies.keys():
                time.sleep(10)
                r = self.session.post(loginpage, data=post_params, timeout=self.timeout)
            if r.status_code != 200:
                logger.error("rutracker login returned status code %s" % r.status_code)
                self.loggedin = False
            else:
                if 'bb_data' in r.cookies.keys():
                    self.loggedin = True
                    logger.info("Successfully logged in to rutracker")
                else:
                    logger.error("Could not login to rutracker, credentials maybe incorrect, site is down or too many attempts. Try again later")
                    self.loggedin = False
            return self.loggedin
        except Exception as e:
            logger.error("Unknown error logging in to rutracker: %s" % e)
            self.loggedin = False
            return self.loggedin

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

        if format == 'lossless':
            format = '+lossless'
            self.maxsize = 10000000000
        elif format == 'lossless+mp3':
            format = '+lossless||mp3||aac'
            self.maxsize = 10000000000
        else:
            format = '+mp3||aac'
            self.maxsize = 300000000

        # sort by size, descending.
        sort = '&o=7&s=2'

        searchurl = "%s?nm=%s%s%s" % (self.search_referer, urllib.quote(searchterm), format, sort)

        logger.info("Searching rutracker using term: %s", searchterm)

        return searchurl

    def search(self, searchurl):
        """
        Parse the search results and return valid torrent list
        """

        try:
            headers = {'Referer': self.search_referer}
            r = self.session.get(url=searchurl, headers=headers, timeout=self.timeout)

            soup = BeautifulSoup(r.content, 'html5lib')

            # Debug
            #logger.debug (soup.prettify())

            # Check if still logged in
            if not self.still_logged_in(soup):
                self.login()
                r = self.session.get(url=searchurl, timeout=self.timeout)
                soup = BeautifulSoup(r.content, 'html5lib')
                if not self.still_logged_in(soup):
                    logger.error("Error getting rutracker data")
                    return None

            # Process
            rulist = []
            i = soup.find('table', id='tor-tbl')
            if not i:
                logger.info("No valid results found from rutracker")
                return None
            minimumseeders = int(headphones.CONFIG.NUMBEROFSEEDERS) - 1

            for item in zip(i.find_all(class_='hl-tags'),i.find_all(class_='dl-stub'),i.find_all(class_='seedmed')):
                title = item[0].get_text()
                url = item[1].get('href')
                size_formatted = item[1].get_text()[:-2]
                seeds = item[2].get_text()
                size_parts = size_formatted.split()
                size = float(size_parts[0])

                if size_parts[1] == 'KB':
                    size *= 1024
                if size_parts[1] == 'MB':
                    size *= 1024 ** 2
                if size_parts[1] == 'GB':
                    size *= 1024 ** 3
                if size_parts[1] == 'TB':
                    size *= 1024 ** 4

                if size < self.maxsize and minimumseeders < int(seeds):
                    logger.info('Found %s. Size: %s' % (title, size_formatted))
                    #Torrent topic page
                    torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
                    topicurl = 'http://rutracker.org/forum/viewtopic.php?t=' + torrent_id
                    rulist.append((title, size, topicurl, 'rutracker.org', 'torrent', True))
                else:
                    logger.info("%s is larger than the maxsize or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i)" % (title, size, int(seeds)))

            if not rulist:
                logger.info("No valid results found from rutracker")

            return rulist

        except Exception as e:
            logger.error("An unknown error occurred in the rutracker parser: %s" % e)
            return None


    def get_torrent_data(self, url):
        """
        return the .torrent data
        """

        torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
        downloadurl = 'http://dl.rutracker.org/forum/dl.php?t=' + torrent_id
        cookie = {'bb_dl': torrent_id}
        try:
            headers = {'Referer': url}
            r = self.session.get(url=downloadurl, cookies=cookie, headers=headers, timeout=self.timeout)
            return r.content
        except Exception as e:
            logger.error('Error getting torrent: %s', e)
            return False


    #TODO get this working in utorrent.py
    def utorrent_add_file(self, data):

        host = headphones.CONFIG.UTORRENT_HOST
        if not host.startswith('http'):
            host = 'http://' + host
        if host.endswith('/'):
            host = host[:-1]
        if host.endswith('/gui'):
            host = host[:-4]

        base_url = host

        url = base_url + '/gui/'
        self.session.auth = (headphones.CONFIG.UTORRENT_USERNAME, headphones.CONFIG.UTORRENT_PASSWORD)

        try:
            r = self.session.get(url + 'token.html')
        except Exception as e:
            logger.error('Error getting token: %s', e)
            return

        if r.status_code == 401:
            logger.debug('Error reaching utorrent')
            return

        regex = re.search(r'.+>([^<]+)</div></html>', r.text)
        if regex is None:
            logger.debug('Error reading token')
            return

        self.session.params = {'token': regex.group(1)}
        files = {'torrent_file': ("", data)}

        try:
            self.session.post(url, params={'action': 'add-file'}, files=files)
        except Exception as e:
            logger.exception('Error adding file to utorrent %s', e)

