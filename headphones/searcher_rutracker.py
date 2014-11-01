#!/usr/bin/env python
# coding=utf-8

# Headphones rutracker.org search
# Functions called from searcher.py

from headphones import logger, db, utorrent

from bencode import bencode as bencode, bdecode
from urlparse import urlparse
from bs4 import BeautifulSoup
from tempfile import mkdtemp
from hashlib import sha1

import headphones
import requests
import cookielib
import urllib2
import urllib
import re
import os


class Rutracker():

    logged_in = False

    # Stores a number of login attempts to prevent recursion.
    #login_counter = 0

    def __init__(self):

        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        urllib2.install_opener(self.opener)

    def login(self, login, password):
        """Implements tracker login procedure."""

        self.logged_in = False

        if login is None or password is None:
            return False

        #self.login_counter += 1

        # No recursion wanted.
        #if self.login_counter > 1:
        #    return False

        params = urllib.urlencode({"login_username": login,
                                   "login_password": password,
                                   "login": "Вход"})

        try:
            self.opener.open("http://login.rutracker.org/forum/login.php", params)
        except Exception:
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

    def search(self, searchurl, maxsize, minseeders, albumid):
        """
        Parse the search results and return valid torrent list
        """

        titles = []
        urls = []
        seeders = []
        sizes = []
        torrentlist = []
        rulist = []

        try:

            page = self.opener.open(searchurl, timeout=60)
            soup = BeautifulSoup(page.read())

            # Debug
            #logger.debug (soup.prettify())

            # Title
            for link in soup.find_all('a', attrs={'class': 'med tLink hl-tags bold'}):
                title = link.get_text()
                titles.append(title)

            # Download URL
            for link in soup.find_all('a', attrs={'class': 'small tr-dl dl-stub'}):
                url = link.get('href')
                urls.append(url)

            # Seeders
            for link in soup.find_all('b', attrs={'class': 'seedmed'}):
                seeder = link.get_text()
                seeders.append(seeder)

            # Size
            for link in soup.find_all('td', attrs={'class': 'row4 small nowrap tor-size'}):
                size = link.u.string
                sizes.append(size)

        except:
            pass

        # Combine lists
        torrentlist = zip(titles, urls, seeders, sizes)

        # return if nothing found
        if not torrentlist:
            return False

        # don't bother checking track counts anymore, let searcher filter instead
        # leave code in just in case
        check_track_count = False

        if check_track_count:

            # get headphones track count for album, return if not found
            myDB = db.DBConnection()
            tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])
            hptrackcount = len(tracks)

            if not hptrackcount:
                logger.info('headphones track info not found, cannot compare to torrent')
                return False

            # Return all valid entries, ignored, required words now checked in searcher.py

            #unwantedlist = ['promo', 'vinyl', '[lp]', 'songbook', 'tvrip', 'hdtv', 'dvd']

            formatlist = ['ape', 'flac', 'ogg', 'm4a', 'aac', 'mp3', 'wav', 'aif']
            deluxelist = ['deluxe', 'edition', 'japanese', 'exclusive']

        for torrent in torrentlist:

            returntitle = torrent[0].encode('utf-8')
            url = torrent[1]
            seeders = torrent[2]
            size = torrent[3]

            if int(size) <= maxsize and int(seeders) >= minseeders:

                #Torrent topic page
                torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
                topicurl = 'http://rutracker.org/forum/viewtopic.php?t=' + torrent_id

                # add to list
                if not check_track_count:
                    valid = True
                else:

                    # Check torrent info
                    self.cookiejar.set_cookie(cookielib.Cookie(version=0, name='bb_dl', value=torrent_id, port=None, port_specified=False, domain='.rutracker.org', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False))

                    # Debug
                    #for cookie in self.cookiejar:
                    #    logger.debug ('Cookie: %s' % cookie)

                    try:
                        page = self.opener.open(url)
                        torrent = page.read()
                        if torrent:
                            decoded = bdecode(torrent)
                            metainfo = decoded['info']
                        page.close()
                    except Exception, e:
                        logger.error('Error getting torrent: %s' % e)
                        return False

                    # get torrent track count and check for cue
                    trackcount = 0
                    cuecount = 0

                    if 'files' in metainfo: # multi
                        for pathfile in metainfo['files']:
                            path = pathfile['path']
                            for file in path:
                                if any(file.lower().endswith('.' + x.lower()) for x in formatlist):
                                    trackcount += 1
                                if '.cue' in file:
                                    cuecount += 1

                    title = returntitle.lower()
                    logger.debug('torrent title: %s' % title)
                    logger.debug('headphones trackcount: %s' % hptrackcount)
                    logger.debug('rutracker trackcount: %s' % trackcount)

                    # If torrent track count less than headphones track count, and there's a cue, then attempt to get track count from log(s)
                    # This is for the case where we have a single .flac/.wav which can be split by cue
                    # Not great, but shouldn't be doing this too often
                    totallogcount = 0
                    if trackcount < hptrackcount and cuecount > 0 and cuecount < hptrackcount:
                        page = self.opener.open(topicurl, timeout=60)
                        soup = BeautifulSoup(page.read())
                        findtoc = soup.find_all(text='TOC of the extracted CD')
                        if not findtoc:
                            findtoc = soup.find_all(text='TOC извлечённого CD')
                        for toc in findtoc:
                            logcount = 0
                            for toccontent in toc.find_all_next(text=True):
                                cut_string = toccontent.split('|')
                                new_string = cut_string[0].lstrip().rstrip()
                                if new_string == '1' or new_string == '01':
                                    logcount = 1
                                elif logcount > 0:
                                    if new_string.isdigit():
                                        logcount += 1
                                    else:
                                        break
                            totallogcount = totallogcount + logcount

                    if totallogcount > 0:
                        trackcount = totallogcount
                        logger.debug('rutracker logtrackcount: %s' % totallogcount)

                    # If torrent track count = hp track count then return torrent,
                    # if greater, check for deluxe/special/foreign editions
                    # if less, then allow if it's a single track with a cue
                    valid = False

                    if trackcount == hptrackcount:
                        valid = True
                    elif trackcount > hptrackcount:
                        if any(deluxe in title for deluxe in deluxelist):
                            valid = True

                # Add to list
                if valid:
                    rulist.append((returntitle, size, topicurl))
                else:
                    if topicurl:
                        logger.info(u'<a href="%s">Torrent</a> found with %s tracks but the selected headphones release has %s tracks, skipping for rutracker.org' % (topicurl, trackcount, hptrackcount))
            else:
                logger.info('%s is larger than the maxsize or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i)' % (returntitle, int(size), int(seeders)))

        return rulist

    def get_torrent(self, url, savelocation=None):

        torrent_id = dict([part.split('=') for part in urlparse(url)[4].split('&')])['t']
        self.cookiejar.set_cookie(cookielib.Cookie(version=0, name='bb_dl', value=torrent_id, port=None, port_specified=False, domain='.rutracker.org', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False))
        downloadurl = 'http://dl.rutracker.org/forum/dl.php?t=' + torrent_id
        torrent_name = torrent_id + '.torrent'

        try:
            prev = os.umask(headphones.UMASK)
            page = self.opener.open(downloadurl)
            torrent = page.read()
            decoded = bdecode(torrent)
            metainfo = decoded['info']
            tor_hash = sha1(bencode(metainfo)).hexdigest()
            if savelocation:
                download_path = os.path.join(savelocation, torrent_name)
            else:
                tempdir = mkdtemp(suffix='_rutracker_torrents')
                download_path = os.path.join(tempdir, torrent_name)

            with open(download_path, 'wb') as f:
                f.write(torrent)
            os.umask(prev)

            # Add file to utorrent
            if headphones.CONFIG.TORRENT_DOWNLOADER == 2:
                self.utorrent_add_file(download_path)

        except Exception as e:
            logger.error('Error getting torrent: %s', e)
            return False

        return download_path, tor_hash

    #TODO get this working in utorrent.py
    def utorrent_add_file(self, filename):

        host = headphones.CONFIG.UTORRENT_HOST
        if not host.startswith('http'):
            host = 'http://' + host
        if host.endswith('/'):
            host = host[:-1]
        if host.endswith('/gui'):
            host = host[:-4]

        base_url = host
        username = headphones.CONFIG.UTORRENT_USERNAME
        password = headphones.CONFIG.UTORRENT_PASSWORD

        session = requests.Session()
        url = base_url + '/gui/'
        session.auth = (username, password)

        try:
            r = session.get(url + 'token.html')
        except Exception:
            logger.exception('Error getting token')
            return

        if r.status_code == '401':
            logger.debug('Error reaching utorrent')
            return

        regex = re.search(r'.+>([^<]+)</div></html>', r.text)
        if regex is None:
            logger.debug('Error reading token')
            return

        session.params = {'token': regex.group(1)}

        with open(filename, 'rb') as f:
            try:
                session.post(url, params={'action': 'add-file'},
                    files={'torrent_file': f})
            except Exception:
                logger.exception('Error adding file to utorrent')
                return
