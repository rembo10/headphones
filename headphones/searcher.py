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

# NZBGet support added by CurlyMo <curlymoo1@gmail.com> as a part of XBian - XBMC on the Raspberry Pi

import urllib, urlparse
from lib.pygazelle import api as gazelleapi
from lib.pygazelle import encoding as gazelleencoding
from lib.pygazelle import format as gazelleformat
from lib.pygazelle import media as gazellemedia
from xml.dom import minidom

import os, re, time
import string
import shutil
import requests
import subprocess

import headphones
from headphones.common import USER_AGENT
from headphones import logger, db, helpers, classes, sab, nzbget, request
from headphones import transmission

import lib.bencode as bencode

import headphones.searcher_rutracker as rutrackersearch
rutracker = rutrackersearch.Rutracker()

# Persistent What.cd API object
gazelle = None

def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def searchforalbum(albumid=None, new=False, losslessOnly=False, choose_specific_download=False):
    myDB = db.DBConnection()

    if not albumid:
        results = myDB.select('SELECT * from albums WHERE Status="Wanted" OR Status="Wanted Lossless"')

        for album in results:

            if not album['AlbumTitle'] or not album['ArtistName']:
                logger.warn('Skipping release %s. No title available' % album['AlbumID'])
                continue

            new = True

            if album['Status'] == "Wanted Lossless":
                losslessOnly = True

            logger.info('Searching for "%s - %s" since it is marked as wanted' % (album['ArtistName'], album['AlbumTitle']))
            do_sorted_search(album, new, losslessOnly)

    elif albumid and choose_specific_download:

        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        logger.info('Searching for "%s - %s"' % (album['ArtistName'], album['AlbumTitle']))
        results = do_sorted_search(album, new, losslessOnly, choose_specific_download=True)
        return results

    else:

        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        logger.info('Searching for "%s - %s" since it was marked as wanted' % (album['ArtistName'], album['AlbumTitle']))
        do_sorted_search(album, new, losslessOnly)

    logger.info('Search for Wanted albums complete')

def do_sorted_search(album, new, losslessOnly, choose_specific_download=False):

    NZB_PROVIDERS = (headphones.HEADPHONES_INDEXER or headphones.NEWZNAB or headphones.NZBSORG or headphones.NZBSRUS or headphones.OMGWTFNZBS)
    NZB_DOWNLOADERS = (headphones.SAB_HOST or headphones.BLACKHOLE_DIR or headphones.NZBGET_HOST)
    TORRENT_PROVIDERS = (headphones.KAT or headphones.PIRATEBAY or headphones.ISOHUNT or headphones.MININOVA or headphones.WAFFLES or headphones.RUTRACKER or headphones.WHATCD)

    results = []

    if headphones.PREFER_TORRENTS == 0:

        if NZB_PROVIDERS and NZB_DOWNLOADERS:
            results = searchNZB(album, new, losslessOnly)

        if not results and TORRENT_PROVIDERS:
            results = searchTorrent(album, new, losslessOnly)

    elif headphones.PREFER_TORRENTS == 1:

        if TORRENT_PROVIDERS:
            results = searchTorrent(album, new, losslessOnly)

        if not results and NZB_PROVIDERS and NZB_DOWNLOADERS:
            results = searchNZB(album, new, losslessOnly)

    else:

        nzb_results = None
        torrent_results = None

        if NZB_PROVIDERS and NZB_DOWNLOADERS:
            nzb_results = searchNZB(album, new, losslessOnly)

        if TORRENT_PROVIDERS:
            torrent_results = searchTorrent(album, new, losslessOnly)

        if not nzb_results:
            nzb_results = []

        if not torrent_results:
            torrent_results = []

        results = nzb_results + torrent_results


    if choose_specific_download:
        return results

    sorted_search_results = sort_search_results(results, album, new)

    if not sorted_search_results:
        return

    logger.info(u"Making sure we can download the best result")
    (data, bestqual) = preprocess(sorted_search_results)

    if data and bestqual:
        send_to_downloader(data, bestqual, album)

def sort_search_results(resultlist, album, new):

    myDB = db.DBConnection()

    # Add a priority if it has any of the preferred words
    temp_list = []
    for result in resultlist:
        if headphones.PREFERRED_WORDS and any(word.lower() in result[0].lower() for word in helpers.split_string(headphones.PREFERRED_WORDS)):
            temp_list.append((result[0],result[1],result[2],result[3],result[4],1))
        else:
            temp_list.append((result[0],result[1],result[2],result[3],result[4],0))

    resultlist = temp_list

    if headphones.PREFERRED_QUALITY == 2 and headphones.PREFERRED_BITRATE:

        logger.debug('Target bitrate: %s kbps' % headphones.PREFERRED_BITRATE)

        tracks = myDB.select('SELECT TrackDuration from tracks WHERE AlbumID=?', [album['AlbumID']])

        try:
            albumlength = sum([pair[0] for pair in tracks])

            targetsize = albumlength/1000 * int(headphones.PREFERRED_BITRATE) * 128

            if not targetsize:
                logger.info('No track information for %s - %s. Defaulting to highest quality' % (album['ArtistName'], album['AlbumTitle']))
                finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])), reverse=True)

            else:
                logger.info('Target size: %s' % helpers.bytes_to_mb(targetsize))
                newlist = []
                flac_list = []

                if headphones.PREFERRED_BITRATE_HIGH_BUFFER:
                    high_size_limit = targetsize * int(headphones.PREFERRED_BITRATE_HIGH_BUFFER)/100
                else:
                    high_size_limit = None
                if headphones.PREFERRED_BITRATE_LOW_BUFFER:
                    low_size_limit = targetsize * int(headphones.PREFERRED_BITRATE_LOW_BUFFER)/100
                else:
                    low_size_limit = None

                for result in resultlist:

                    if high_size_limit and (int(result[1]) > high_size_limit):

                        logger.info("%s is too large for this album - not considering it. (Size: %s, Maxsize: %s)", result[0], helpers.bytes_to_mb(result[1]), helpers.bytes_to_mb(high_size_limit))

                        # Add lossless nzbs to the "flac list" which we can use if there are no good lossy matches
                        if 'flac' in result[0].lower():
                            flac_list.append((result[0], result[1], result[2], result[3], result[4], result[5]))

                        continue

                    if low_size_limit and (int(result[1]) < low_size_limit):
                        logger.info("%s is too small for this album - not considering it. (Size: %s, Minsize: %s)", result[0], helpers.bytes_to_mb(result[1]), helpers.bytes_to_mb(low_size_limit))
                        continue

                    delta = abs(targetsize - int(result[1]))
                    newlist.append((result[0], result[1], result[2], result[3], result[4], result[5], delta))

                finallist = sorted(newlist, key=lambda title: (-title[5], title[6]))

                if not len(finallist) and len(flac_list) and headphones.PREFERRED_BITRATE_ALLOW_LOSSLESS:
                    logger.info("Since there were no appropriate lossy matches (and at least one lossless match, going to use lossless instead")
                    finallist = sorted(flac_list, key=lambda title: (title[5], int(title[1])), reverse=True)
        except Exception, e:
            logger.exception('Unhandled exception')
            logger.info('No track information for %s - %s. Defaulting to highest quality', (album['ArtistName'], album['AlbumTitle']))

            finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])), reverse=True)

    else:

        finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])), reverse=True)

    if new:

        while True:

            if len(finallist):

                alreadydownloaded = myDB.select('SELECT * from snatched WHERE URL=?', [finallist[0][2]])

                if len(alreadydownloaded):
                    logger.info('%s has already been downloaded. Skipping.' % finallist[0][0])
                    finallist.pop(0)

                else:
                    break
            else:
                logger.info('No more results found for:  %s - %s' % (album['ArtistName'], album['AlbumTitle']))
                return None

    if not len(finallist):
        logger.info('No appropriate matches found for %s - %s', album['ArtistName'], album['AlbumTitle'])
        return None

    return finallist

def get_year_from_release_date(release_date):

    try:
        year = release_date[:4]
    except TypeError:
        year = ''

    return year

def searchNZB(album, new=False, losslessOnly=False):

    albumid = album['AlbumID']
    reldate = album['ReleaseDate']
    year = get_year_from_release_date(reldate)

    dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':'', '*':'', '.':'', ':':''}

    cleanalbum = helpers.latinToAscii(helpers.replace_all(album['AlbumTitle'], dic)).strip()
    cleanartist = helpers.latinToAscii(helpers.replace_all(album['ArtistName'], dic)).strip()

    # Use the provided search term if available, otherwise build a search term
    if album['SearchTerm']:
        term = album['SearchTerm']

    else:
        # FLAC usually doesn't have a year for some reason so I'll leave it out
        # Various Artist albums might be listed as VA, so I'll leave that out too
        # Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
        if album['ArtistName'] in album['AlbumTitle'] or len(album['ArtistName']) < 4 or len(album['AlbumTitle']) < 4:
            term = cleanartist + ' ' + cleanalbum + ' ' + year
        elif album['ArtistName'] == 'Various Artists':
            term = cleanalbum + ' ' + year
        else:
            term = cleanartist + ' ' + cleanalbum

    # Replace bad characters in the term and unicode it
    term = re.sub('[\.\-\/]', ' ', term).encode('utf-8')
    artistterm = re.sub('[\.\-\/]', ' ', cleanartist).encode('utf-8')

    logger.debug("Using search term: %s" % term)

    resultlist = []

    if headphones.HEADPHONES_INDEXER:
        provider = "headphones"

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.PREFERRED_QUALITY:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        # Request results
        logger.info('Parsing results from Headphones Indexer')

        headers = { 'User-Agent': USER_AGENT }
        params = {
            "t": "search",
            "cat": categories,
            "apikey": '89edf227c1de9b3de50383fff11466c6',
            "maxage": headphones.USENET_RETENTION,
            "q": term
        }

        data = request.request_feed(
            url="http://headphones.codeshy.com/newznab/api",
            params=params, headers=headers,
            auth=(headphones.HPUSER, headphones.HPPASS)
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from %s for %s" % ('Headphones Index', term))
            else:
                for item in data.entries:
                    try:
                        url = item.link
                        title = item.title
                        size = int(item.links[1]['length'])

                        resultlist.append((title, size, url, provider, 'nzb'))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))

                    except Exception, e:
                        logger.error(u"An unknown error occurred trying to parse the feed: %s" % e)

    if headphones.NEWZNAB:
        provider = "newznab"
        newznab_hosts = []

        if headphones.NEWZNAB_HOST and headphones.NEWZNAB_ENABLED:

            newznab_hosts.append((headphones.NEWZNAB_HOST, headphones.NEWZNAB_APIKEY, headphones.NEWZNAB_ENABLED))

        for newznab_host in headphones.EXTRA_NEWZNABS:
            if newznab_host[2] == '1' or newznab_host[2] == 1:
                newznab_hosts.append(newznab_host)

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.PREFERRED_QUALITY:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        for newznab_host in newznab_hosts:
            # Add a little mod for kere.ws
            if newznab_host[0] == "http://kere.ws":
                if categories == "3040":
                    categories = categories + ",4070"
                elif categories == "3040,3010":
                    categories = categories + ",4070,4010"
                elif categories == "3010":
                    categories = categories + ",4010"
                else:
                    categories = categories + ",4050"

            # Request results
            logger.info('Parsing results from %s', newznab_host[0])

            headers = { 'User-Agent': USER_AGENT }
            params = {
                "t": "search",
                "apikey": newznab_host[1],
                "cat": categories,
                "maxage": headphones.USENET_RETENTION,
                "q": term
            }

            data = request.request_feed(
                url=newznab_host[0] + '/api?',
                params=params, headers=headers
            )

            # Process feed
            if data:
                if not len(data.entries):
                    logger.info(u"No results found from %s for %s", newznab_host[0], term)
                else:
                    for item in data.entries:
                        try:
                            url = item.link
                            title = item.title
                            size = int(item.links[1]['length'])

                            resultlist.append((title, size, url, provider, 'nzb'))
                            logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))

                        except Exception, e:
                            logger.exception("An unknown error occurred trying to parse the feed: %s" % e)

    if headphones.NZBSORG:
        provider = "nzbsorg"
        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.PREFERRED_QUALITY:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        # Request results
        logger.info('Parsing results from nzbs.org')

        headers = { 'User-Agent': USER_AGENT }
        params = {
            "t": "search",
            "apikey": headphones.NZBSORG_HASH,
            "cat": categories,
            "maxage": headphones.USENET_RETENTION,
            "q": term
        }

        data = request.request_feed(
            url='http://beta.nzbs.org/api',
            params=params, headers=headers,
            timeout=20
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from nzbs.org for %s" % term)
            else:
                for item in data.entries:
                    try:
                        url = item.link
                        title = item.title
                        size = int(item.links[1]['length'])

                        resultlist.append((title, size, url, provider, 'nzb'))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    except Exception, e:
                        logger.exception("Unhandled exception while parsing feed")

    if headphones.NZBSRUS:
        provider = "nzbsrus"
        categories = "54"

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            sub = "16"
        elif headphones.PREFERRED_QUALITY:
            sub = ""
        else:
            sub = "15"

        if album['Type'] == 'Other':
            sub = ""
            logger.info("Album type is audiobook/spokenword. Searching all music categories")

        # Request results
        logger.info('Parsing results from NZBsRus')

        headers = { 'User-Agent': USER_AGENT }
        params = {
            "uid": headphones.NZBSRUS_UID,
            "key": headphones.NZBSRUS_APIKEY,
            "cat": categories,
            "sub": sub,
            "age": headphones.USENET_RETENTION,
            "searchtext": term
        }

        data = request.request_json(
            url='https://www.nzbsrus.com/api.php',
            params=params, headers=headers,
            validator=lambda x: type(x) == dict
        )

        # Parse response
        if data:
            if data.get('matches', 0) == 0:
                logger.info(u"No results found from NZBsRus for %s", term)
                pass
            else:
                for item in data['results']:
                    try:
                        url = "http://www.nzbsrus.com/nzbdownload_rss.php/" + item['id'] + "/" + headphones.NZBSRUS_UID + "/" + item['key']
                        title = item['name']
                        size = int(item['size'])

                        resultlist.append((title, size, url, provider, 'nzb'))
                        logger.info('Found %s. Size: %s', title, helpers.bytes_to_mb(size))

                    except Exception, e:
                        logger.exception("Unhandled exception")

    if headphones.OMGWTFNZBS:
        provider = "omgwtfnzbs"

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "22"
        elif headphones.PREFERRED_QUALITY:
            categories = "22,7"
        else:
             categories = "7"

        if album['Type'] == 'Other':
            categories = "29"
            logger.info("Album type is audiobook/spokenword. Searching all music categories")

        # Request results
        logger.info('Parsing results from omgwtfnzbs')

        headers = { 'User-Agent': USER_AGENT }
        params = {
            "user": headphones.OMGWTFNZBS_UID,
            "api": headphones.OMGWTFNZBS_APIKEY,
            "catid": categories,
            "retention": headphones.USENET_RETENTION,
            "search": term
        }

        data = request.request_json(
            url='http://api.omgwtfnzbs.org/json/',
            params=params, headers=headers,
            validator=lambda x: type(x) == dict
        )

        # Parse response
        if data:
            if 'notice' in data:
                logger.info(u"No results returned from omgwtfnzbs: %s" % data['notice'])
            else:
                for item in data:
                    try:
                        url = item['getnzb']
                        title = item['release']
                        size = int(item['sizebytes'])

                        resultlist.append((title, size, url, provider, 'nzb'))
                        logger.info('Found %s. Size: %s', title, helpers.bytes_to_mb(size))
                    except Exception, e:
                        logger.exception("Unhandled exception")

    # attempt to verify that this isn't a substring result
    # when looking for "Foo - Foo" we don't want "Foobar"
    # this should be less of an issue when it isn't a self-titled album so we'll only check vs artist
    #
    # Also will filter flac & remix albums if not specifically looking for it
    # This code also checks the ignored words and required words
    return [result for result in resultlist if verifyresult(result[0], artistterm, term, losslessOnly)]

def send_to_downloader(data, bestqual, album):

    logger.info(u'Found best result from %s: <a href="%s">%s</a> - %s', bestqual[3], bestqual[2], bestqual[0], helpers.bytes_to_mb(bestqual[1]))
    # Get rid of any dodgy chars here so we can prevent sab from renaming our downloads
    kind = bestqual[4]

    if kind == 'nzb':
        folder_name = helpers.sab_sanitize_foldername(bestqual[0])

        if headphones.NZB_DOWNLOADER == 1:

            nzb = classes.NZBDataSearchResult()
            nzb.extraInfo.append(data)
            nzb.name = folder_name
            nzbget.sendNZB(nzb)

        elif headphones.NZB_DOWNLOADER == 0:

            nzb = classes.NZBDataSearchResult()
            nzb.extraInfo.append(data)
            nzb.name = folder_name
            sab.sendNZB(nzb)

            # If we sent the file to sab, we can check how it was renamed and insert that into the snatched table
            (replace_spaces, replace_dots) = sab.checkConfig()

            if replace_dots:
                folder_name = helpers.sab_replace_dots(folder_name)
            if replace_spaces:
                folder_name = helpers.sab_replace_spaces(folder_name)

        else:
            nzb_name = folder_name + '.nzb'
            download_path = os.path.join(headphones.BLACKHOLE_DIR, nzb_name)

            try:
                prev = os.umask(headphones.UMASK)

                with open(download_path, 'w') as fp:
                    fp.write(data)

                os.umask(prev)
                logger.info('File saved to: %s', nzb_name)
            except Exception, e:
                logger.error('Couldn\'t write NZB file: %s', e)
                return
    else:
        folder_name = '%s - %s [%s]' % (helpers.latinToAscii(album['ArtistName']).encode('UTF-8').replace('/', '_'), helpers.latinToAscii(album['AlbumTitle']).encode('UTF-8').replace('/', '_'), get_year_from_release_date(album['ReleaseDate']))

        # Blackhole
        if headphones.TORRENT_DOWNLOADER == 0:

            # Get torrent name from .torrent, this is usually used by the torrent client as the folder name
            torrent_name = helpers.replace_illegal_chars(folder_name) + '.torrent'
            download_path = os.path.join(headphones.TORRENTBLACKHOLE_DIR, torrent_name)
            
            if bestqual[2].startswith("magnet:"):
                if headphones.OPEN_MAGNET_LINKS:
                    try:
                        if headphones.SYS_PLATFORM == 'win32':
                            os.startfile(bestqual[2])
                        elif headphones.SYS_PLATFORM == 'darwin':
                            subprocess.Popen(["open", bestqual[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        else:
                            subprocess.Popen(["xdg-open", bestqual[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                        # Gonna just take a guess at this..... Is there a better way to find this out?
                        folder_name = bestqual[0]
                    except Exception, e:
                        logger.error("Error opening magnet link: %s" % str(e))
                        return
                else:
                    logger.error("Cannot save magnet files to blackhole. Please switch your torrent downloader to Transmission or uTorrent or allow Headphones to try to open magnet links")
                    return

            else:
                try:

                    if bestqual[3] == 'rutracker.org':
                        download_path = rutracker.get_torrent(bestqual[2], headphones.TORRENTBLACKHOLE_DIR)
                        if not download_path:
                            return
                    else:
                        #Write the torrent file to a path derived from the TORRENTBLACKHOLE_DIR and file name.
                        with open(download_path, 'wb') as fp:
                            fp.write(data)

                        try:
                            os.chmod(download_path, int(headphones.FILE_PERMISSIONS, 8))
                        except:
                            logger.error("Could not change permissions for file: %s", download_path)

                    #Open the fresh torrent file again so we can extract the proper torrent name
                    #Used later in post-processing.
                    with open(download_path, 'rb') as fp:
                        torrent_info = bencode.bdecode(fp.read())

                    folder_name = torrent_info['info'].get('name', '')
                    logger.info('Torrent folder name: %s' % folder_name)
                except Exception, e:
                    logger.error('Couldn\'t get name from Torrent file: %s. Defaulting to torrent title' % e)
                    folder_name = bestqual[0]

        elif headphones.TORRENT_DOWNLOADER == 1:
            logger.info("Sending torrent to Transmission")

            # rutracker needs cookies to be set, pass the .torrent file instead of url
            if bestqual[3] == 'rutracker.org':
                file_or_url = rutracker.get_torrent(bestqual[2])
            else:
                file_or_url = bestqual[2]

            torrentid = transmission.addTorrent(file_or_url)

            if not torrentid:
                logger.error("Error sending torrent to Transmission. Are you sure it's running?")
                return

            folder_name = transmission.getTorrentFolder(torrentid)
            if folder_name:
                logger.info('Torrent folder name: %s' % folder_name)
            else:
                logger.error('Torrent folder name could not be determined')
                return

            # remove temp .torrent file created above
            if bestqual[3] == 'rutracker.org':
                try:
                    shutil.rmtree(os.path.split(file_or_url)[0])
                except Exception, e:
                    logger.exception("Unhandled exception")

    myDB = db.DBConnection()
    myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [album['AlbumID']])
    myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?, ?)', [album['AlbumID'], bestqual[0], bestqual[1], bestqual[2], "Snatched", folder_name, kind])

def verifyresult(title, artistterm, term, lossless):

    title = re.sub('[\.\-\/\_]', ' ', title)

    #if artistterm != 'Various Artists':
    #
    #    if not re.search('^' + re.escape(artistterm), title, re.IGNORECASE):
    #        #logger.info("Removed from results: " + title + " (artist not at string start).")
    #        #return False
    #    elif re.search(re.escape(artistterm) + '\w', title, re.IGNORECASE | re.UNICODE):
    #        logger.info("Removed from results: " + title + " (post substring result).")
    #        return False
    #    elif re.search('\w' + re.escape(artistterm), title, re.IGNORECASE | re.UNICODE):
    #        logger.info("Removed from results: " + title + " (pre substring result).")
    #        return False

    #another attempt to weed out substrings. We don't want "Vol III" when we were looking for "Vol II"

    # Filter out remix search results (if we're not looking for it)
    if 'remix' not in term.lower() and 'remix' in title.lower():
        logger.info("Removed %s from results because it's a remix album and we're not looking for a remix album right now.", title)
        return False

    # Filter out FLAC if we're not specifically looking for it
    if headphones.PREFERRED_QUALITY == (0 or '0') and 'flac' in title.lower() and not lossless:
        logger.info("Removed %s from results because it's a lossless album and we're not looking for a lossless album right now.", title)
        return False

    if headphones.IGNORED_WORDS:
        for each_word in helpers.split_string(headphones.IGNORED_WORDS):
            if each_word.lower() in title.lower():
                logger.info("Removed '%s' from results because it contains ignored word: '%s'", title, each_word)
                return False

    if headphones.REQUIRED_WORDS:
        for each_word in helpers.split_string(headphones.REQUIRED_WORDS):
            if ' OR ' in each_word:
                or_words = helpers.split_string(each_word, 'OR')
                if any(word.lower() in title.lower() for word in or_words):
                    continue
                else:
                    logger.info("Removed '%s' from results because it doesn't contain any of the required words in: '%s'", title, str(or_words))
                    return False
            if each_word.lower() not in title.lower():
                logger.info("Removed '%s' from results because it doesn't contain required word: '%s'", title, each_word)
                return False

    tokens = re.split('\W', term, re.IGNORECASE | re.UNICODE)
    for token in tokens:

        if not token:
            continue
        if token == 'Various' or token == 'Artists' or token == 'VA':
            continue
        if not re.search('(?:\W|^)+' + token + '(?:\W|$)+', title, re.IGNORECASE | re.UNICODE):
            cleantoken = ''.join(c for c in token if c not in string.punctuation)
            if not not re.search('(?:\W|^)+' + cleantoken + '(?:\W|$)+', title, re.IGNORECASE | re.UNICODE):
                dic = {'!':'i', '$':'s'}
                dumbtoken = helpers.replace_all(token, dic)
                if not not re.search('(?:\W|^)+' + dumbtoken + '(?:\W|$)+', title, re.IGNORECASE | re.UNICODE):
                    logger.info("Removed from results: %s (missing tokens: %s and %s)", title, token, cleantoken)
                    return False

    return True

def getresultNZB(result):
    nzb = None

    if result[3] == 'newzbin':
        response = request.request_response(
            url='https://www.newzbin2.es/api/dnzb/',
            auth=(headphones.HPUSER, headphones.HPPASS),
            params={"username": headphones.NEWZBIN_UID, "password": headphones.NEWZBIN_PASSWORD, "reportid": result[2]},
            headers={'User-Agent': USER_AGENT},
            whitelist_status_code=400
        )

        if response is not None:
            if response.status_code == 400:
                error_code = int(response.headers.header['X-DNZB-RCode'])

                if error_code == 450:
                    result = re.search("wait (\d+) seconds", response.headers['X-DNZB-RText'])
                    seconds = int(result.group(1))

                    logger.info("Newzbin throttled our NZB downloading, pausing for %d seconds", seconds)
                    time.sleep(seconds)

                    # Try again -- possibly forever :(
                    getresultNZB(result)
                else:
                    logger.info("Newzbin error code %d", error_code)
            else:
                nzb = response.content
    elif result[3] == 'headphones':
        nzb = request.request_content(
            url=result[2],
            auth=(headphones.HPUSER, headphones.HPPASS),
            headers={'User-Agent': USER_AGENT}
        )
    else:
        nzb = request.request_content(
            url=result[2],
            headers={'User-Agent': USER_AGENT}
        )

    return nzb

def searchTorrent(album, new=False, losslessOnly=False):
    global gazelle  # persistent what.cd api object to reduce number of login attempts

    # rutracker login

    if headphones.RUTRACKER and album:
        rulogin = rutracker.login(headphones.RUTRACKER_USER, headphones.RUTRACKER_PASSWORD)
        if not rulogin:
            logger.info(u'Could not login to rutracker, search results will exclude this provider')

    albumid = album['AlbumID']
    reldate = album['ReleaseDate']

    year = get_year_from_release_date(reldate)

    # MERGE THIS WITH THE TERM CLEANUP FROM searchNZB
    dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':' ', '*':''}

    semi_cleanalbum = helpers.replace_all(album['AlbumTitle'], dic)
    cleanalbum = helpers.latinToAscii(semi_cleanalbum)
    semi_cleanartist = helpers.replace_all(album['ArtistName'], dic)
    cleanartist = helpers.latinToAscii(semi_cleanartist)

    # Use provided term if available, otherwise build our own (this code needs to be cleaned up since a lot
    # of these torrent providers are just using cleanartist/cleanalbum terms
    if album['SearchTerm']:
        term = album['SearchTerm']

    else:
        # FLAC usually doesn't have a year for some reason so I'll leave it out
        # Various Artist albums might be listed as VA, so I'll leave that out too
        # Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
        if album['ArtistName'] in album['AlbumTitle'] or len(album['ArtistName']) < 4 or len(album['AlbumTitle']) < 4:
            term = cleanartist + ' ' + cleanalbum + ' ' + year
        elif album['ArtistName'] == 'Various Artists':
            term = cleanalbum + ' ' + year
        else:
            term = cleanartist + ' ' + cleanalbum

    # Save user search term
    if album['SearchTerm']:
        usersearchterm = term
    else:
        usersearchterm = ''

    semi_clean_artist_term = re.sub('[\.\-\/]', ' ', semi_cleanartist).encode('utf-8', 'replace')
    semi_clean_album_term = re.sub('[\.\-\/]', ' ', semi_cleanalbum).encode('utf-8', 'replace')
    # Replace bad characters in the term and unicode it
    term = re.sub('[\.\-\/]', ' ', term).encode('utf-8')
    artistterm = re.sub('[\.\-\/]', ' ', cleanartist).encode('utf-8', 'replace')
    albumterm  = re.sub('[\.\-\/]', ' ', cleanalbum).encode('utf-8', 'replace')

    logger.debug("Using search term: %s" % term)

    resultlist = []
    pre_sorted_results = False
    minimumseeders = int(headphones.NUMBEROFSEEDERS) - 1

    if headphones.KAT:
        provider = "Kick Ass Torrent"
        providerurl = url_fix("http://kickass.to/usearch/" + term)
        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "7"        #music
            format = "2"             #flac
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY:
            categories = "7"        #music
            format = "10"            #mp3+flac
            maxsize = 10000000000
        else:
            categories = "7"        #music
            format = "8"            #mp3
            maxsize = 300000000

        # Requesting content
        logger.info('Parsing results from KAT')

        params = {
            "categories[0]": "music",
            "field": "seeders",
            "sorder": "desc",
            "rss": "1"
        }

        data = request.request_feed(
            url=providerurl,
            params=params,
            timeout=20
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from %s for %s" % provider, term)
            else:
                for item in data.entries:
                    try:
                        rightformat = True
                        title = item['title']
                        seeders = item['torrent_seeds']
                        url = item['links'][1]['href']
                        size = int(item['links'][1]['length'])
                        if format == "2":
                            torrent = request.request_content(url)
                            if not torrent or (int(torrent.find(".mp3")) > 0 and int(torrent.find(".flac")) < 1):
                                rightformat = False
                        if rightformat == True and size < maxsize and minimumseeders < int(seeders):
                            resultlist.append((title, size, url, provider, 'torrent'))
                            logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                        else:
                            logger.info('%s is larger than the maxsize, the wrong format or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i, Format: %s)' % (title, size, int(seeders), rightformat))
                    except Exception, e:
                        logger.exception("Unhandled exception in the KAT parser")

    if headphones.WAFFLES:
        provider = "Waffles.fm"
        providerurl = url_fix("https://www.waffles.fm/browse.php")

        bitrate = None
        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            format = "FLAC"
            bitrate = "(Lossless)"
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY:
            format = "FLAC OR MP3"
            maxsize = 10000000000
        else:
            format = "MP3"
            maxsize = 300000000

        if not usersearchterm:
            query_items = ['artist:"%s"' % artistterm,
                           'album:"%s"' % albumterm,
                           'year:(%s)' % year]
        else:
            query_items = [usersearchterm]

        query_items.extend(['format:(%s)' % format,
                            'size:[0 TO %d]' % maxsize,
                            '-seeders:0']) # cut out dead torrents

        if bitrate:
            query_items.append('bitrate:"%s"' % bitrate)

        # Requesting content
        logger.info('Parsing results from Waffles')

        params = {
            "uid": headphones.WAFFLES_UID,
            "passkey": headphones.WAFFLES_PASSKEY,
            "rss": "1",
            "c0": "1",
            "s": "seeders", # sort by
            "d": "desc", # direction
            "q": " ".join(query_items)
        }

        data = request.request_feed(
            url=providerurl,
            params=params,
            timeout=20
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from %s for %s" % (provider, term))
            else:
                for item in data.entries:
                    try:
                        title = item.title
                        desc_match = re.search(r"Size: (\d+)<", item.description)
                        size = int(desc_match.group(1))
                        url = item.link
                        resultlist.append((title, size, url, provider, 'torrent'))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    except Exception, e:
                        logger.error(u"An error occurred while trying to parse the response from Waffles.fm: %s" % e)

    # rutracker.org

    if headphones.RUTRACKER and rulogin:

        provider = "rutracker.org"

        # Ignore if release date not specified, results too unpredictable

        if not year and not usersearchterm:
            logger.info(u'Release date not specified, ignoring for rutracker.org')
        else:

            bitrate = False

            if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
                format = 'lossless'
                maxsize = 10000000000
            elif headphones.PREFERRED_QUALITY == 1:
                format = 'lossless+mp3'
                maxsize = 10000000000
            else:
                format = 'mp3'
                maxsize = 300000000
                if headphones.PREFERRED_QUALITY == 2 and headphones.PREFERRED_BITRATE:
                    bitrate = True

            # build search url based on above

            if not usersearchterm:
                searchURL = rutracker.searchurl(artistterm, albumterm, year, format)
            else:
                searchURL = rutracker.searchurl(usersearchterm, ' ', ' ', format)

            logger.info(u'Parsing results from <a href="%s">rutracker.org</a>' % searchURL)

            # parse results and get best match

            rulist = rutracker.search(searchURL, maxsize, minimumseeders, albumid, bitrate)

            # add best match to overall results list

            if rulist:
                for ru in rulist:
                    title = ru[0].decode('utf-8')
                    size = ru[1]
                    url = ru[2]
                    resultlist.append((title, size, url, provider, 'torrent'))
                    logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
            else:
                logger.info(u"No valid results found from %s" % (provider))

    if headphones.WHATCD:
        provider = "What.cd"
        providerurl = "http://what.cd/"

        bitrate = None
        bitrate_string = bitrate

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:  # Lossless Only mode
            search_formats = [gazelleformat.FLAC]
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY == 2:  # Preferred quality mode
            search_formats = [None]  # should return all
            bitrate = headphones.PREFERRED_BITRATE
            if bitrate:
                for encoding_string in gazelleencoding.ALL_ENCODINGS:
                    if re.search(bitrate, encoding_string, flags=re.I):
                        bitrate_string = encoding_string
                if bitrate_string not in gazelleencoding.ALL_ENCODINGS:
                    raise Exception("Preferred bitrate %s not recognized by %s" % (bitrate_string, provider))
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY == 1:  # Highest quality including lossless
            search_formats = [gazelleformat.FLAC, gazelleformat.MP3]
            maxsize = 10000000000
        else:  # Highest quality excluding lossless
            search_formats = [gazelleformat.MP3]
            maxsize = 300000000

        if not gazelle or not gazelle.logged_in():
            try:
                logger.info(u"Attempting to log in to What.cd...")
                gazelle = gazelleapi.GazelleAPI(headphones.WHATCD_USERNAME, headphones.WHATCD_PASSWORD)
                gazelle._login()
            except Exception, e:
                gazelle = None
                logger.error(u"What.cd credentials incorrect or site is down. Error: %s %s" % (e.__class__.__name__, str(e)))

        if gazelle and gazelle.logged_in():
            logger.info(u"Searching %s..." % provider)
            all_torrents = []
            for search_format in search_formats:
                all_torrents.extend(gazelle.search_torrents(artistname=semi_clean_artist_term,
                                                              groupname=semi_clean_album_term,
                                                              format=search_format, encoding=bitrate_string)['results'])

            # filter on format, size, and num seeders
            logger.info(u"Filtering torrents by format, maximum size, and minimum seeders...")
            match_torrents = [ torrent for torrent in all_torrents if torrent.size <= maxsize ]
            match_torrents = [ torrent for torrent in match_torrents if torrent.seeders >= minimumseeders ]

            logger.info(u"Remaining torrents: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            # sort by times d/l'd
            if not len(match_torrents):
                logger.info(u"No results found from %s for %s after filtering" % (provider, term))
            elif len(match_torrents) > 1:
                logger.info(u"Found %d matching releases from %s for %s - %s after filtering" %
                            (len(match_torrents), provider, artistterm, albumterm))
                logger.info("Sorting torrents by times snatched and preferred bitrate %s..." % bitrate_string)
                match_torrents.sort(key=lambda x: int(x.snatched), reverse=True)
                if gazelleformat.MP3 in search_formats:
                    # sort by size after rounding to nearest 10MB...hacky, but will favor highest quality
                    match_torrents.sort(key=lambda x: int(10 * round(x.size/1024./1024./10.)), reverse=True)
                if search_formats and None not in search_formats:
                    match_torrents.sort(key=lambda x: int(search_formats.index(x.format)))  # prefer lossless
#                if bitrate:
#                    match_torrents.sort(key=lambda x: re.match("mp3", x.getTorrentDetails(), flags=re.I), reverse=True)
#                    match_torrents.sort(key=lambda x: str(bitrate) in x.getTorrentFolderName(), reverse=True)
                logger.info(u"New order: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            pre_sorted_results = True
            for torrent in match_torrents:
                if not torrent.file_path:
                    torrent.group.update_group_data() # will load the file_path for the individual torrents
                resultlist.append((torrent.file_path,
                                   torrent.size,
                                   gazelle.generate_torrent_link(torrent.id),
                                   provider,
                                   'torrent'))

    # Pirate Bay
    if headphones.PIRATEBAY:
        provider = "The Pirate Bay"
        if headphones.PIRATEBAY_PROXY_URL:
            #Might need to clean up the user submitted url
            pirate_proxy = headphones.PIRATEBAY_PROXY_URL

            if not pirate_proxy.startswith('http'):
                pirate_proxy = 'http://' + pirate_proxy
            if pirate_proxy.endswith('/'):
                pirate_proxy = pirate_proxy[:-1]

            providerurl = url_fix(pirate_proxy + "/search/" + term + "/0/99/")

        else:
            providerurl = url_fix("http://thepiratebay.se/search/" + term + "/0/99/")

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            category = '104'          #flac
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY:
            category = '100'          #audio cat
            maxsize = 10000000000
        else:
            category = '101'          #mp3
            maxsize = 300000000

        # Requesting content
        logger.info('Parsing results from The Pirate Bay')

        headers = { 'User-Agent' : 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Safari/535.19' }
        params = {
            "iht": "2",
            "sort": "seeds"
        }

        data = request.request_soup(
            url=providerurl + category,
            params=params,
            headers=headers,
            timeout=20
        )

        # Process content
        if data:
            rows = data.select('table tr')

            if not rows or len(rows) == '1':
                logger.info(u"No results found from %s for %s" % (provider, term))
            else:
                for item in rows[1:]:
                    try:
                        rightformat = True
                        title = ''.join(item.find("a", {"class" : "detLink"}))
                        seeds = int(''.join(item.find("td", {"align" : "right"})))
                        url = None
                        if headphones.TORRENT_DOWNLOADER == 0:
                            try:
                                url = item.find("a", {"title":"Download this torrent"})['href']
                            except TypeError:
                                if headphones.OPEN_MAGNET_LINKS:
                                    url = item.findAll("a")[3]['href']
                                else:
                                    logger.info('"%s" only has a magnet link, skipping' % title)
                                    continue
                        else:
                            url = item.findAll("a")[3]['href']
                        formatted_size = re.search('Size (.*),', unicode(item)).group(1).replace(u'\xa0', ' ')
                        size = helpers.piratesize(formatted_size)
                        if size < maxsize and minimumseeders < seeds and url != None:
                            resultlist.append((title, size, url, provider, 'torrent'))
                            logger.info('Found %s. Size: %s' % (title, formatted_size))
                        else:
                            logger.info('%s is larger than the maxsize or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i)' % (title, size, int(seeds)))

                    except Exception, e:
                        logger.error(u"An unknown error occurred in the Pirate Bay parser: %s" % e)

    if headphones.ISOHUNT:
        provider = "isoHunt"
        providerurl = url_fix("http://isohunt.com/js/rss/" + term)
        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "7"        #music
            format = "2"             #flac
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY:
            categories = "7"        #music
            format = "10"            #mp3+flac
            maxsize = 10000000000
        else:
            categories = "7"        #music
            format = "8"            #mp3
            maxsize = 300000000

        # Requesting content
        logger.info('Parsing results from ISOHunt')

        headers = { 'User-Agent': USER_AGENT }
        params = {
            "iht": "2",
            "sort": "seeds"
        }

        data = request.request_feed(
            url=providerurl,
            params=params, headers=headers,
            auth=(headphones.HPUSER, headphones.HPPASS),
            timeout=20
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from %s for %s", provider, term)
            else:
                for item in data.entries:
                    try:
                        rightformat = True
                        title = re.sub(r"(?<=  \[)(.+)(?=\])","",item.title)
                        title = title.replace("[]","")
                        sxstart = item.description.find("Seeds: ") + 7
                        seeds = ""
                        while item.description[sxstart:sxstart + 1] != " ":
                            seeds = seeds + item.description[sxstart:sxstart + 1]
                            sxstart = sxstart + 1
                        url = item.links[1]['url']
                        size = int(item.links[1]['length'])
                        if format == "2":
                            torrent = request.request_content(url)

                            if not torrent or (int(torrent.find(".mp3")) > 0 and int(torrent.find(".flac")) < 1):
                                rightformat = False
                        for findterm in term.split(" "):
                            if not findterm in title:
                                rightformat = False
                        if rightformat == True and size < maxsize and minimumseeders < seeds:
                            resultlist.append((title, size, url, provider, 'torrent'))
                            logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                        else:
                            logger.info('%s is larger than the maxsize, the wrong format or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i, Format: %s)' % (title, size, int(seeds), rightformat))
                    except Exception:
                        logger.exception("Unhandled exception in isoHunt parser")

    if headphones.MININOVA:
        provider = "Mininova"
        providerurl = url_fix("http://www.mininova.org/rss/" + term + "/5")

        if headphones.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "7"        #music
            format = "2"             #flac
            maxsize = 10000000000
        elif headphones.PREFERRED_QUALITY:
            categories = "7"        #music
            format = "10"            #mp3+flac
            maxsize = 10000000000
        else:
            categories = "7"        #music
            format = "8"            #mp3
            maxsize = 300000000

        # Requesting content
        logger.info('Parsing results from Mininova')

        data = request.request_feed(
            url=providerurl,
            timeout=20
        )

        # Process feed
        if data:
            if not len(data.entries):
                logger.info(u"No results found from %s for %s" % (provider, term))
            else:
                for item in data.entries:
                    try:
                        rightformat = True
                        title = item.title
                        sxstart = item.description.find("Ratio: ") + 7
                        seeds = ""
                        while item.description[sxstart:sxstart + 1] != " ":
                            seeds = seeds + item.description[sxstart:sxstart + 1]
                            sxstart = sxstart + 1
                        url = item.links[1]['url']
                        size = int(item.links[1]['length'])
                        if format == "2":
                            torrent = request.request_content(url)

                            if not torrent or (int(torrent.find(".mp3")) > 0 and int(torrent.find(".flac")) < 1):
                                rightformat = False
                        if rightformat == True and size < maxsize and minimumseeders < seeds:
                            resultlist.append((title, size, url, provider, 'torrent'))
                            logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                        else:
                            logger.info('%s is larger than the maxsize, the wrong format or has too little seeders for this category, skipping. (Size: %i bytes, Seeders: %i, Format: %s)' % (title, size, int(seeds), rightformat))

                    except Exception, e:
                        logger.exception("Unhandled exception in Mininova Parser")

    #attempt to verify that this isn't a substring result
    #when looking for "Foo - Foo" we don't want "Foobar"
    #this should be less of an issue when it isn't a self-titled album so we'll only check vs artist
    return [result for result in resultlist if verifyresult(result[0], artistterm, term, losslessOnly)]

# THIS IS KIND OF A MESS AND PROBABLY NEEDS TO BE CLEANED UP
def preprocess(resultlist):

    for result in resultlist:

        if result[4] == 'torrent':
            #Get out of here if we're using Transmission or uTorrent
            if headphones.TORRENT_DOWNLOADER != 0:
                return True, result
            # get outta here if rutracker or piratebay
            if result[3] == 'rutracker.org':
                return True, result
            # Get out of here if it's a magnet link
            if result[2].startswith("magnet"):
                return True, result

            # Download the torrent file
            headers = {}

            if result[3] == 'Kick Ass Torrent':
                headers['Referer'] = 'http://kat.ph/'
            elif result[3] == 'What.cd':
                headers['User-Agent'] = 'Headphones'
            elif result[3] == "The Pirate Bay":
                headers['User-Agent'] = 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Safari/535.19'
            return request.request_content(url=result[2], headers=headers), result

        else:
            usenet_retention = int(headphones.USENET_RETENTION or 2000)
            nzb = getresultNZB(result)

            if nzb:
                try:
                    d = minidom.parseString(nzb)
                    node = d.documentElement
                    nzbfiles = d.getElementsByTagName("file")
                    skipping = False
                    for nzbfile in nzbfiles:
                        if int(nzbfile.getAttribute("date")) < (time.time() - usenet_retention * 86400):
                            logger.info('NZB contains a file out of your retention. Skipping.')
                            skipping = True
                            break
                    if skipping:
                        continue

                        #TODO: Do we want rar checking in here to try to keep unknowns out?
                        #or at least the option to do so?
                except Exception, e:
                    logger.exception('Unhandled exception. Unable to parse the best result NZB. Error: %s. (Make sure your username/password/API is correct for provider: %s', e ,result[3])
                    continue

                return nzb, result
            else:
                logger.error("Couldn't retrieve the best nzb. Skipping.")
                continue

        return (None, None)