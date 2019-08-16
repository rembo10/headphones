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

from base64 import b16encode, b32decode
from hashlib import sha1
import string
import random
import urllib
import datetime
import subprocess
import unicodedata
import urlparse

import os
import re
from pygazelle import api as gazelleapi
from pygazelle import encoding as gazelleencoding
from pygazelle import format as gazelleformat
from pygazelle import release_type as gazellerelease_type
import headphones
from headphones.common import USER_AGENT
from headphones import logger, db, helpers, classes, sab, nzbget, request
from headphones import utorrent, transmission, notifiers, rutracker, deluge, qbittorrent
from bencode import bencode, bdecode

# Magnet to torrent services, for Black hole. Stolen from CouchPotato.
TORRENT_TO_MAGNET_SERVICES = [
    'http://itorrents.org/torrent/%s.torrent',
    'https://cache.torrentgalaxy.org/get/%s',
    'https://www.seedpeer.me/torrent/%s'
]

# Persistent Orpheus.network API object
orpheusobj = None
ruobj = None
# Persistent RED API object
redobj = None


def fix_url(s, charset="utf-8"):
    """
    Fix the URL so it is proper formatted and encoded.
    """

    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')

    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')

    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def torrent_to_file(target_file, data):
    """
    Write torrent data to file, and change permissions accordingly. Will return
    None in case of a write error. If changing permissions fails, it will
    continue anyway.
    """

    # Write data to file
    try:
        with open(target_file, "wb") as fp:
            fp.write(data)
    except IOError as e:
        logger.error(
            "Could not write torrent file '%s': %s. Skipping.",
            target_file, e.message)
        return

    # Try to change permissions
    if headphones.CONFIG.FILE_PERMISSIONS_ENABLED:
        try:
            os.chmod(target_file, int(headphones.CONFIG.FILE_PERMISSIONS, 8))
        except OSError as e:
            logger.warn(
                "Could not change permissions for file '%s': %s. Continuing.",
                target_file.decode(headphones.SYS_ENCODING, "replace"),
                e.message)
    else:
        logger.debug(
            "Not changing file permissions, since it is disabled: %s",
            target_file.decode(headphones.SYS_ENCODING, "replace"))

    # Done
    return True


def read_torrent_name(torrent_file, default_name=None):
    """
    Read the torrent file and return the torrent name. If the torrent name
    cannot be determined, it will return the `default_name`.
    """

    # Open file
    try:
        with open(torrent_file, "rb") as fp:
            torrent_info = bdecode(fp.read())
    except IOError as e:
        logger.error("Unable to open torrent file: %s", torrent_file)
        return

    # Read dictionary
    if torrent_info:
        try:
            return torrent_info["info"]["name"]
        except KeyError:
            if default_name:
                logger.warning("Couldn't get name from torrent file: %s. "
                               "Defaulting to '%s'", e, default_name)
            else:
                logger.warning("Couldn't get name from torrent file: %s. No "
                               "default given", e)

    # Return default
    return default_name


def calculate_torrent_hash(link, data=None):
    """
    Calculate the torrent hash from a magnet link or data. Raises a ValueError
    when it cannot create a torrent hash given the input data.
    """

    if link.startswith("magnet:"):
        torrent_hash = re.findall("urn:btih:([\w]{32,40})", link)[0]
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash)).lower()
    elif data:
        info = bdecode(data)["info"]
        torrent_hash = sha1(bencode(info)).hexdigest()
    else:
        raise ValueError("Cannot calculate torrent hash without magnet link "
                         "or data")

    return torrent_hash.upper()


def get_seed_ratio(provider):
    """
    Return the seed ratio for the specified provider if applicable. Defaults to
    None in case of an error.
    """

    if provider == 'rutracker.org':
        seed_ratio = headphones.CONFIG.RUTRACKER_RATIO
    elif provider == 'Orpheus.network':
        seed_ratio = headphones.CONFIG.ORPHEUS_RATIO
    elif provider == 'Redacted':
        seed_ratio = headphones.CONFIG.REDACTED_RATIO
    elif provider == 'The Pirate Bay':
        seed_ratio = headphones.CONFIG.PIRATEBAY_RATIO
    elif provider == 'Old Pirate Bay':
        seed_ratio = headphones.CONFIG.OLDPIRATEBAY_RATIO
    elif provider == 'Waffles.ch':
        seed_ratio = headphones.CONFIG.WAFFLES_RATIO
    elif provider.startswith("Jackett_"):
        provider = provider.split("Jackett_")[1]
        if provider in headphones.CONFIG.TORZNAB_HOST:
            seed_ratio = headphones.CONFIG.TORZNAB_RATIO
        else:
            for torznab in headphones.CONFIG.get_extra_torznabs():
                if provider in torznab[0]:
                    seed_ratio = torznab[2]
                    break
    else:
        seed_ratio = None

    if seed_ratio is not None:
        try:
            seed_ratio = float(seed_ratio)
        except ValueError:
            logger.warn("Could not get seed ratio for %s" % provider)

    return seed_ratio


def searchforalbum(albumid=None, new=False, losslessOnly=False,
                   choose_specific_download=False):
    logger.info('Searching for wanted albums')
    myDB = db.DBConnection()

    if not albumid:
        results = myDB.select(
            'SELECT * from albums WHERE Status="Wanted" OR Status="Wanted Lossless"')

        for album in results:

            if not album['AlbumTitle'] or not album['ArtistName']:
                logger.warn('Skipping release %s. No title available', album['AlbumID'])
                continue

            if headphones.CONFIG.WAIT_UNTIL_RELEASE_DATE and album['ReleaseDate']:
                release_date = strptime_musicbrainz(album['ReleaseDate'])
                if not release_date:
                    logger.warn("No valid date for: %s. Skipping automatic search" %
                                album['AlbumTitle'])
                    continue

                elif release_date > datetime.datetime.today():
                    logger.info("Skipping: %s. Waiting for release date of: %s" % (
                        album['AlbumTitle'], album['ReleaseDate']))
                    continue

            new = True

            if album['Status'] == "Wanted Lossless":
                losslessOnly = True

            logger.info('Searching for "%s - %s" since it is marked as wanted' % (
                album['ArtistName'], album['AlbumTitle']))
            do_sorted_search(album, new, losslessOnly)

    elif albumid and choose_specific_download:
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        logger.info('Searching for "%s - %s"' % (album['ArtistName'], album['AlbumTitle']))
        results = do_sorted_search(album, new, losslessOnly, choose_specific_download=True)
        return results

    else:
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        logger.info('Searching for "%s - %s" since it was marked as wanted' % (
            album['ArtistName'], album['AlbumTitle']))
        do_sorted_search(album, new, losslessOnly)

    logger.info('Search for wanted albums complete')


def strptime_musicbrainz(date_str):
    """
    Release date as returned by Musicbrainz may contain the full date (Year-Month-Day)
    but it may as well be just Year-Month or even just the year.

    Args:
        date_str: the date as a string (ex: "2003-05-01", "2003-03", "2003")

    Returns:
        The more accurate datetime object we can create or None if parse failed
    """
    acceptable_formats = ('%Y-%m-%d', '%Y-%m', '%Y')
    for date_format in acceptable_formats:
        try:
            return datetime.datetime.strptime(date_str, date_format)
        except:
            pass
    return None


def do_sorted_search(album, new, losslessOnly, choose_specific_download=False):
    NZB_PROVIDERS = (headphones.CONFIG.HEADPHONES_INDEXER or
                     headphones.CONFIG.NEWZNAB or
                     headphones.CONFIG.NZBSORG or
                     headphones.CONFIG.OMGWTFNZBS)

    NZB_DOWNLOADERS = (headphones.CONFIG.SAB_HOST or
                       headphones.CONFIG.BLACKHOLE_DIR or
                       headphones.CONFIG.NZBGET_HOST)

    TORRENT_PROVIDERS = (headphones.CONFIG.TORZNAB or
                         headphones.CONFIG.PIRATEBAY or
                         headphones.CONFIG.OLDPIRATEBAY or
                         headphones.CONFIG.WAFFLES or
                         headphones.CONFIG.RUTRACKER or
                         headphones.CONFIG.ORPHEUS or
                         headphones.CONFIG.REDACTED)

    results = []
    myDB = db.DBConnection()
    albumlength = myDB.select('SELECT sum(TrackDuration) from tracks WHERE AlbumID=?',
                              [album['AlbumID']])[0][0]

    if headphones.CONFIG.PREFER_TORRENTS == 0 and not choose_specific_download:

        if NZB_PROVIDERS and NZB_DOWNLOADERS:
            results = searchNZB(album, new, losslessOnly, albumlength)

        if not results and TORRENT_PROVIDERS:
            results = searchTorrent(album, new, losslessOnly, albumlength)

    elif headphones.CONFIG.PREFER_TORRENTS == 1 and not choose_specific_download:

        if TORRENT_PROVIDERS:
            results = searchTorrent(album, new, losslessOnly, albumlength)

        if not results and NZB_PROVIDERS and NZB_DOWNLOADERS:
            results = searchNZB(album, new, losslessOnly, albumlength)

    else:

        nzb_results = None
        torrent_results = None

        if NZB_PROVIDERS and NZB_DOWNLOADERS:
            nzb_results = searchNZB(album, new, losslessOnly, albumlength, choose_specific_download)

        if TORRENT_PROVIDERS:
            torrent_results = searchTorrent(album, new, losslessOnly, albumlength,
                                            choose_specific_download)

        if not nzb_results:
            nzb_results = []

        if not torrent_results:
            torrent_results = []

        results = nzb_results + torrent_results

    if choose_specific_download:
        return results

    # Filter all results that do not comply
    results = [result for result in results if result[5]]

    # Sort the remaining results
    sorted_search_results = sort_search_results(results, album, new, albumlength)

    if not sorted_search_results:
        return

    logger.info(u"Making sure we can download the best result")
    (data, bestqual) = preprocess(sorted_search_results)

    if data and bestqual:
        send_to_downloader(data, bestqual, album)


def removeDisallowedFilenameChars(filename):
    validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').lower()
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)


def more_filtering(results, album, albumlength, new):
    low_size_limit = None
    high_size_limit = None
    allow_lossless = False
    myDB = db.DBConnection()

    # Lossless - ignore results if target size outside bitrate range
    if headphones.CONFIG.PREFERRED_QUALITY == 3 and albumlength and (
            headphones.CONFIG.LOSSLESS_BITRATE_FROM or headphones.CONFIG.LOSSLESS_BITRATE_TO):
        if headphones.CONFIG.LOSSLESS_BITRATE_FROM:
            low_size_limit = albumlength / 1000 * int(headphones.CONFIG.LOSSLESS_BITRATE_FROM) * 128
        if headphones.CONFIG.LOSSLESS_BITRATE_TO:
            high_size_limit = albumlength / 1000 * int(headphones.CONFIG.LOSSLESS_BITRATE_TO) * 128

    # Preferred Bitrate - ignore results if target size outside % buffer
    elif headphones.CONFIG.PREFERRED_QUALITY == 2 and headphones.CONFIG.PREFERRED_BITRATE:
        logger.debug('Target bitrate: %s kbps' % headphones.CONFIG.PREFERRED_BITRATE)
        if albumlength:
            targetsize = albumlength / 1000 * int(headphones.CONFIG.PREFERRED_BITRATE) * 128
            logger.info('Target size: %s' % helpers.bytes_to_mb(targetsize))
            if headphones.CONFIG.PREFERRED_BITRATE_LOW_BUFFER:
                low_size_limit = targetsize * int(
                    headphones.CONFIG.PREFERRED_BITRATE_LOW_BUFFER) / 100
            if headphones.CONFIG.PREFERRED_BITRATE_HIGH_BUFFER:
                high_size_limit = targetsize * int(
                    headphones.CONFIG.PREFERRED_BITRATE_HIGH_BUFFER) / 100
                if headphones.CONFIG.PREFERRED_BITRATE_ALLOW_LOSSLESS:
                    allow_lossless = True

    newlist = []

    for result in results:

        if low_size_limit and (int(result[1]) < low_size_limit):
            logger.info(
                "%s from %s is too small for this album - not considering it. (Size: %s, Minsize: %s)",
                result[0], result[3], helpers.bytes_to_mb(result[1]),
                helpers.bytes_to_mb(low_size_limit))
            continue

        if high_size_limit and (int(result[1]) > high_size_limit):
            logger.info(
                "%s from %s is too large for this album - not considering it. (Size: %s, Maxsize: %s)",
                result[0], result[3], helpers.bytes_to_mb(result[1]),
                helpers.bytes_to_mb(high_size_limit))

            # Keep lossless results if there are no good lossy matches
            if not (allow_lossless and 'flac' in result[0].lower()):
                continue

        if new:
            alreadydownloaded = myDB.select('SELECT * from snatched WHERE URL=?', [result[2]])

            if len(alreadydownloaded):
                logger.info(
                    '%s has already been downloaded from %s. Skipping.' % (result[0], result[3]))
                continue

        newlist.append(result)

    results = newlist

    return results


def sort_search_results(resultlist, album, new, albumlength):
    if new and not len(resultlist):
        logger.info(
            'No more results found for:  %s - %s' % (album['ArtistName'], album['AlbumTitle']))
        return None

    # Add a priority if it has any of the preferred words
    temp_list = []
    preferred_words = None
    if headphones.CONFIG.PREFERRED_WORDS:
        preferred_words = helpers.split_string(headphones.CONFIG.PREFERRED_WORDS)
    for result in resultlist:
        priority = 0
        if preferred_words:
            if any(word.lower() in result[0].lower() for word in preferred_words):
                priority = 1
            # add a search provider priority (weighted based on position)
            i = next((i for i, word in enumerate(preferred_words) if word in result[3].lower()),
                     None)
            if i is not None:
                priority += round((len(preferred_words) - i) / float(len(preferred_words)), 2)

        temp_list.append((result[0], result[1], result[2], result[3], result[4], priority))

    resultlist = temp_list

    # if headphones.CONFIG.PREFERRED_QUALITY == 2 and headphones.CONFIG.PREFERRED_BITRATE and result[3] != 'Orpheus.network':
    if headphones.CONFIG.PREFERRED_QUALITY == 2 and headphones.CONFIG.PREFERRED_BITRATE:

        try:
            targetsize = albumlength / 1000 * int(headphones.CONFIG.PREFERRED_BITRATE) * 128

            if not targetsize:
                logger.info('No track information for %s - %s. Defaulting to highest quality' % (
                    album['ArtistName'], album['AlbumTitle']))
                finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])),
                                   reverse=True)

            else:
                newlist = []
                flac_list = []

                for result in resultlist:

                    # Add lossless results to the "flac list" which we can use if there are no good lossy matches
                    if 'flac' in result[0].lower():
                        flac_list.append(
                            (result[0], result[1], result[2], result[3], result[4], result[5]))
                        continue

                    delta = abs(targetsize - int(result[1]))
                    newlist.append(
                        (result[0], result[1], result[2], result[3], result[4], result[5], delta))

                finallist = sorted(newlist, key=lambda title: (-title[5], title[6]))

                if not len(finallist) and len(
                        flac_list) and headphones.CONFIG.PREFERRED_BITRATE_ALLOW_LOSSLESS:
                    logger.info(
                        "Since there were no appropriate lossy matches (and at least one lossless match), going to use lossless instead")
                    finallist = sorted(flac_list, key=lambda title: (title[5], int(title[1])),
                                       reverse=True)
        except Exception:
            logger.exception('Unhandled exception')
            logger.info('No track information for %s - %s. Defaulting to highest quality',
                        album['ArtistName'], album['AlbumTitle'])

            finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])),
                               reverse=True)

    else:

        finallist = sorted(resultlist, key=lambda title: (title[5], int(title[1])), reverse=True)

        # keep number of seeders order for Orpheus.network
        # if result[3] == 'Orpheus.network':
        #    finallist = resultlist

    if not len(finallist):
        logger.info('No appropriate matches found for %s - %s', album['ArtistName'],
                    album['AlbumTitle'])
        return None

    return finallist


def get_year_from_release_date(release_date):
    try:
        year = release_date[:4]
    except TypeError:
        year = ''

    return year


def searchNZB(album, new=False, losslessOnly=False, albumlength=None,
              choose_specific_download=False):
    reldate = album['ReleaseDate']
    year = get_year_from_release_date(reldate)

    dic = {'...': '', ' & ': ' ', ' = ': ' ', '?': '', '$': 's', ' + ': ' ', '"': '', ',': '',
           '*': '', '.': '', ':': ''}

    cleanalbum = helpers.latinToAscii(helpers.replace_all(album['AlbumTitle'], dic)).strip()
    cleanartist = helpers.latinToAscii(helpers.replace_all(album['ArtistName'], dic)).strip()

    # Use the provided search term if available, otherwise build a search term
    if album['SearchTerm']:
        term = album['SearchTerm']
    elif album['Type'] == 'part of':
        term = cleanalbum + " " + year
    else:
        # FLAC usually doesn't have a year for some reason so leave it out.
        # Various Artist albums might be listed as VA, so I'll leave that out too
        # Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
        if album['ArtistName'] in album['AlbumTitle'] or len(album['ArtistName']) < 4 or len(
                album['AlbumTitle']) < 4:
            term = cleanartist + ' ' + cleanalbum + ' ' + year
        elif album['ArtistName'] == 'Various Artists':
            term = cleanalbum + ' ' + year
        else:
            term = cleanartist + ' ' + cleanalbum

    # Replace bad characters in the term and unicode it
    term = re.sub('[\.\-\/]', ' ', term).encode('utf-8')
    artistterm = re.sub('[\.\-\/]', ' ', cleanartist).encode('utf-8')

    # If Preferred Bitrate and High Limit and Allow Lossless then get both lossy and lossless
    if headphones.CONFIG.PREFERRED_QUALITY == 2 and headphones.CONFIG.PREFERRED_BITRATE and headphones.CONFIG.PREFERRED_BITRATE_HIGH_BUFFER and headphones.CONFIG.PREFERRED_BITRATE_ALLOW_LOSSLESS:
        allow_lossless = True
    else:
        allow_lossless = False

    logger.debug("Using search term: %s" % term)

    resultlist = []

    if headphones.CONFIG.HEADPHONES_INDEXER:
        provider = "headphones"

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            logger.info("Album type is audiobook/spokenword. Using audiobook category")
            categories = "3030"

        # Request results
        logger.info('Searching Headphones Indexer with search term: %s' % term)

        headers = {'User-Agent': USER_AGENT}
        params = {
            "t": "search",
            "cat": categories,
            "apikey": '964d601959918a578a670984bdee9357',
            "maxage": headphones.CONFIG.USENET_RETENTION,
            "q": term
        }

        data = request.request_feed(
            url="https://indexer.codeshy.com/api",
            params=params, headers=headers,
            auth=(headphones.CONFIG.HPUSER, headphones.CONFIG.HPPASS)
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

                        resultlist.append((title, size, url, provider, 'nzb', True))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    except Exception as e:
                        logger.error(u"An unknown error occurred trying to parse the feed: %s" % e)

    if headphones.CONFIG.NEWZNAB:
        provider = "newznab"
        newznab_hosts = []

        if headphones.CONFIG.NEWZNAB_HOST and headphones.CONFIG.NEWZNAB_ENABLED:
            newznab_hosts.append((headphones.CONFIG.NEWZNAB_HOST, headphones.CONFIG.NEWZNAB_APIKEY,
                                  headphones.CONFIG.NEWZNAB_ENABLED))

        for newznab_host in headphones.CONFIG.get_extra_newznabs():
            if newznab_host[2] == '1' or newznab_host[2] == 1:
                newznab_hosts.append(newznab_host)

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        for newznab_host in newznab_hosts:

            provider = newznab_host[0]

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
            logger.info('Parsing results from %s using search term: %s' % (newznab_host[0], term))

            headers = {'User-Agent': USER_AGENT}
            params = {
                "t": "search",
                "apikey": newznab_host[1],
                "cat": categories,
                "maxage": headphones.CONFIG.USENET_RETENTION,
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
                            if all(word.lower() in title.lower() for word in term.split()):
                                logger.info(
                                    'Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                                resultlist.append((title, size, url, provider, 'nzb', True))
                            else:
                                logger.info('Skipping %s, not all search term words found' % title)

                        except Exception as e:
                            logger.exception(
                                "An unknown error occurred trying to parse the feed: %s" % e)

    if headphones.CONFIG.NZBSORG:
        provider = "nzbsorg"
        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            categories = "3040,3010"
        else:
            categories = "3010"

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        headers = {'User-Agent': USER_AGENT}
        params = {
            "t": "search",
            "apikey": headphones.CONFIG.NZBSORG_HASH,
            "cat": categories,
            "maxage": headphones.CONFIG.USENET_RETENTION,
            "q": term
        }

        data = request.request_feed(
            url='http://beta.nzbs.org/api',
            params=params, headers=headers,
            timeout=5
        )

        logger.info('Parsing results from nzbs.org using search term: %s' % term)
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

                        resultlist.append((title, size, url, provider, 'nzb', True))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    except Exception as e:
                        logger.exception("Unhandled exception while parsing feed")

    if headphones.CONFIG.OMGWTFNZBS:
        provider = "omgwtfnzbs"

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "22"
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            categories = "22,7"
        else:
            categories = "7"

        if album['Type'] == 'Other':
            categories = "29"
            logger.info("Album type is audiobook/spokenword. Searching all music categories")

        # Request results
        logger.info('Parsing results from omgwtfnzbs using search term: %s' % term)

        headers = {'User-Agent': USER_AGENT}
        params = {
            "user": headphones.CONFIG.OMGWTFNZBS_UID,
            "api": headphones.CONFIG.OMGWTFNZBS_APIKEY,
            "catid": categories,
            "retention": headphones.CONFIG.USENET_RETENTION,
            "search": term
        }

        data = request.request_json(
            url='http://api.omgwtfnzbs.me/json/',
            params=params, headers=headers
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

                        resultlist.append((title, size, url, provider, 'nzb', True))
                        logger.info('Found %s. Size: %s', title, helpers.bytes_to_mb(size))
                    except Exception as e:
                        logger.exception("Unhandled exception")

    # attempt to verify that this isn't a substring result
    # when looking for "Foo - Foo" we don't want "Foobar"
    # this should be less of an issue when it isn't a self-titled album so we'll only check vs artist
    #
    # Also will filter flac & remix albums if not specifically looking for it
    # This code also checks the ignored words and required words
    results = [result for result in resultlist if
               verifyresult(result[0], artistterm, term, losslessOnly)]

    # Additional filtering for size etc
    if results and not choose_specific_download:
        results = more_filtering(results, album, albumlength, new)

    return results


def send_to_downloader(data, bestqual, album):
    logger.info(u'Found best result from %s: <a href="%s">%s</a> - %s', bestqual[3], bestqual[2],
                bestqual[0], helpers.bytes_to_mb(bestqual[1]))
    # Get rid of any dodgy chars here so we can prevent sab from renaming our downloads
    kind = bestqual[4]
    seed_ratio = None
    torrentid = None

    if kind == 'nzb':
        folder_name = helpers.sab_sanitize_foldername(bestqual[0])

        if headphones.CONFIG.NZB_DOWNLOADER == 1:

            nzb = classes.NZBDataSearchResult()
            nzb.extraInfo.append(data)
            nzb.name = folder_name
            if not nzbget.sendNZB(nzb):
                return

        elif headphones.CONFIG.NZB_DOWNLOADER == 0:

            nzb = classes.NZBDataSearchResult()
            nzb.extraInfo.append(data)
            nzb.name = folder_name
            if not sab.sendNZB(nzb):
                return

            # If we sent the file to sab, we can check how it was renamed and insert that into the snatched table
            (replace_spaces, replace_dots) = sab.checkConfig()

            if replace_dots:
                folder_name = helpers.sab_replace_dots(folder_name)
            if replace_spaces:
                folder_name = helpers.sab_replace_spaces(folder_name)

        else:
            nzb_name = folder_name + '.nzb'
            download_path = os.path.join(headphones.CONFIG.BLACKHOLE_DIR, nzb_name)

            try:
                prev = os.umask(headphones.UMASK)

                with open(download_path, 'w') as fp:
                    fp.write(data)

                os.umask(prev)
                logger.info('File saved to: %s', nzb_name)
            except Exception as e:
                logger.error('Couldn\'t write NZB file: %s', e)
                return
    else:
        folder_name = '%s - %s [%s]' % (
            helpers.latinToAscii(album['ArtistName']).encode('UTF-8').replace('/', '_'),
            helpers.latinToAscii(album['AlbumTitle']).encode('UTF-8').replace('/', '_'),
            get_year_from_release_date(album['ReleaseDate']))

        # Blackhole
        if headphones.CONFIG.TORRENT_DOWNLOADER == 0:

            # Get torrent name from .torrent, this is usually used by the torrent client as the folder name
            torrent_name = helpers.replace_illegal_chars(folder_name) + '.torrent'
            download_path = os.path.join(headphones.CONFIG.TORRENTBLACKHOLE_DIR, torrent_name)

            if bestqual[2].lower().startswith("magnet:"):
                if headphones.CONFIG.MAGNET_LINKS == 1:
                    try:
                        if headphones.SYS_PLATFORM == 'win32':
                            os.startfile(bestqual[2])
                        elif headphones.SYS_PLATFORM == 'darwin':
                            subprocess.Popen(["open", bestqual[2]], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                        else:
                            subprocess.Popen(["xdg-open", bestqual[2]], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

                        # Gonna just take a guess at this..... Is there a better way to find this out?
                        folder_name = bestqual[0]
                    except Exception as e:
                        logger.error("Error opening magnet link: %s" % str(e))
                        return
                elif headphones.CONFIG.MAGNET_LINKS == 2:
                    # Procedure adapted from CouchPotato
                    torrent_hash = calculate_torrent_hash(bestqual[2])

                    # Randomize list of services
                    services = TORRENT_TO_MAGNET_SERVICES[:]
                    random.shuffle(services)
                    headers = {'User-Agent': USER_AGENT}

                    for service in services:

                        data = request.request_content(service % torrent_hash, headers=headers)
                        if data:
                            if not torrent_to_file(download_path, data):
                                return
                            # Extract folder name from torrent
                            folder_name = read_torrent_name(download_path,
                                                            bestqual[0])

                            # Break for loop
                            break
                    else:
                        # No service succeeded
                        logger.warning("Unable to convert magnet with hash "
                                       "'%s' into a torrent file.", torrent_hash)
                        return
                elif headphones.CONFIG.MAGNET_LINKS == 3:
                    torrent_to_file(download_path, data)
                    return
                else:
                    logger.error("Cannot save magnet link in blackhole. "
                                 "Please switch your torrent downloader to "
                                 "Transmission, uTorrent or Deluge, or allow Headphones "
                                 "to open or convert magnet links")
                    return
            else:

                if not torrent_to_file(download_path, data):
                    return

                # Extract folder name from torrent
                folder_name = read_torrent_name(download_path, bestqual[0])
                if folder_name:
                    logger.info('Torrent folder name: %s' % folder_name)

        elif headphones.CONFIG.TORRENT_DOWNLOADER == 1:
            logger.info("Sending torrent to Transmission")

            # Add torrent
            if bestqual[3] == 'rutracker.org':
                torrentid = transmission.addTorrent('', data)
            else:
                torrentid = transmission.addTorrent(bestqual[2])

            if not torrentid:
                logger.error("Error sending torrent to Transmission. Are you sure it's running?")
                return

            folder_name = transmission.getName(torrentid)
            if folder_name:
                logger.info('Torrent name: %s' % folder_name)
            else:
                logger.error('Torrent name could not be determined')
                return

            # Set Seed Ratio
            seed_ratio = get_seed_ratio(bestqual[3])
            if seed_ratio is not None:
                transmission.setSeedRatio(torrentid, seed_ratio)

        elif headphones.CONFIG.TORRENT_DOWNLOADER == 3:  # Deluge
            logger.info("Sending torrent to Deluge")

            try:
                # Add torrent
                if bestqual[3] == 'rutracker.org':
                    torrentid = deluge.addTorrent('', data)
                else:
                    torrentid = deluge.addTorrent(bestqual[2])

                if not torrentid:
                    logger.error("Error sending torrent to Deluge. Are you sure it's running? Maybe the torrent already exists?")
                    return

                # This pauses the torrent right after it is added
                if headphones.CONFIG.DELUGE_PAUSED:
                    deluge.setTorrentPause({'hash': torrentid})

                # Set Label
                if headphones.CONFIG.DELUGE_LABEL:
                    deluge.setTorrentLabel({'hash': torrentid})

                # Set Seed Ratio
                seed_ratio = get_seed_ratio(bestqual[3])
                if seed_ratio is not None:
                    deluge.setSeedRatio({'hash': torrentid, 'ratio': seed_ratio})

                # Set move-to directory
                if headphones.CONFIG.DELUGE_DONE_DIRECTORY or headphones.CONFIG.DOWNLOAD_TORRENT_DIR:
                    deluge.setTorrentPath({'hash': torrentid})

                # Get folder name from Deluge, it's usually the torrent name
                folder_name = deluge.getTorrentFolder({'hash': torrentid})
                if folder_name:
                    logger.info('Torrent folder name: %s' % folder_name)
                else:
                    logger.error('Torrent folder name could not be determined')
                    return

            except Exception as e:
                logger.error('Error sending torrent to Deluge: %s' % str(e))

        elif headphones.CONFIG.TORRENT_DOWNLOADER == 2:
            logger.info("Sending torrent to uTorrent")

            # Add torrent
            if bestqual[3] == 'rutracker.org':
                ruobj.utorrent_add_file(data)
            else:
                utorrent.addTorrent(bestqual[2])

            # Get hash
            torrentid = calculate_torrent_hash(bestqual[2], data)
            if not torrentid:
                logger.error('Torrent id could not be determined')
                return

            # Get folder
            folder_name = utorrent.getFolder(torrentid)
            if folder_name:
                logger.info('Torrent folder name: %s' % folder_name)
            else:
                logger.error('Torrent folder name could not be determined')
                return

            # Set Label
            if headphones.CONFIG.UTORRENT_LABEL:
                utorrent.labelTorrent(torrentid)

            # Set Seed Ratio
            seed_ratio = get_seed_ratio(bestqual[3])
            if seed_ratio is not None:
                utorrent.setSeedRatio(torrentid, seed_ratio)
        else:  # if headphones.CONFIG.TORRENT_DOWNLOADER == 4:
            logger.info("Sending torrent to QBiTorrent")

            # Add torrent
            if bestqual[3] == 'rutracker.org':
                ruobj.qbittorrent_add_file(data)
            else:
                qbittorrent.addTorrent(bestqual[2])

            # Get hash
            torrentid = calculate_torrent_hash(bestqual[2], data)
            torrentid = torrentid.lower()
            if not torrentid:
                logger.error('Torrent id could not be determined')
                return

            # Get name
            folder_name = qbittorrent.getName(torrentid)
            if folder_name:
                logger.info('Torrent name: %s' % folder_name)
            else:
                logger.error('Torrent name could not be determined')
                return

    myDB = db.DBConnection()
    myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [album['AlbumID']])
    myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?, ?, ?)',
                [album['AlbumID'], bestqual[0], bestqual[1], bestqual[2], "Snatched", folder_name,
                 kind, torrentid])

    # Store the torrent id so we can check later if it's finished seeding and can be removed
    if seed_ratio is not None and seed_ratio != 0 and torrentid:
        myDB.action(
            'INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?, ?, ?)',
            [album['AlbumID'], bestqual[0], bestqual[1], bestqual[2], "Seed_Snatched", folder_name,
             kind, torrentid])

    # notify
    artist = album[1]
    albumname = album[2]
    rgid = album[6]
    title = artist + ' - ' + albumname
    provider = bestqual[3]
    if provider.startswith(("http://", "https://")):
        provider = provider.split("//")[1]
    name = folder_name if folder_name else None

    if headphones.CONFIG.GROWL_ENABLED and headphones.CONFIG.GROWL_ONSNATCH:
        logger.info(u"Sending Growl notification")
        growl = notifiers.GROWL()
        growl.notify(name, "Download started")
    if headphones.CONFIG.PROWL_ENABLED and headphones.CONFIG.PROWL_ONSNATCH:
        logger.info(u"Sending Prowl notification")
        prowl = notifiers.PROWL()
        prowl.notify(name, "Download started")
    if headphones.CONFIG.PUSHOVER_ENABLED and headphones.CONFIG.PUSHOVER_ONSNATCH:
        logger.info(u"Sending Pushover notification")
        prowl = notifiers.PUSHOVER()
        prowl.notify(name, "Download started")
    if headphones.CONFIG.PUSHBULLET_ENABLED and headphones.CONFIG.PUSHBULLET_ONSNATCH:
        logger.info(u"Sending PushBullet notification")
        pushbullet = notifiers.PUSHBULLET()
        pushbullet.notify(name, "Download started")
    if headphones.CONFIG.JOIN_ENABLED and headphones.CONFIG.JOIN_ONSNATCH:
        logger.info(u"Sending Join notification")
        join = notifiers.JOIN()
        join.notify(name, "Download started")
    if headphones.CONFIG.SLACK_ENABLED and headphones.CONFIG.SLACK_ONSNATCH:
        logger.info(u"Sending Slack notification")
        slack = notifiers.SLACK()
        slack.notify(name, "Download started")
    if headphones.CONFIG.TELEGRAM_ENABLED and headphones.CONFIG.TELEGRAM_ONSNATCH:
        logger.info(u"Sending Telegram notification")
        from headphones import cache
        c = cache.Cache()
        album_art = c.get_artwork_from_cache(None, rgid)
        telegram = notifiers.TELEGRAM()
        message = 'Snatched from ' + provider + '. ' + name
        telegram.notify(message, "Snatched: " + title, rgid, image=album_art)
    if headphones.CONFIG.TWITTER_ENABLED and headphones.CONFIG.TWITTER_ONSNATCH:
        logger.info(u"Sending Twitter notification")
        twitter = notifiers.TwitterNotifier()
        twitter.notify_snatch(name)
    if headphones.CONFIG.NMA_ENABLED and headphones.CONFIG.NMA_ONSNATCH:
        logger.info(u"Sending NMA notification")
        nma = notifiers.NMA()
        nma.notify(snatched=name)
    if headphones.CONFIG.PUSHALOT_ENABLED and headphones.CONFIG.PUSHALOT_ONSNATCH:
        logger.info(u"Sending Pushalot notification")
        pushalot = notifiers.PUSHALOT()
        pushalot.notify(name, "Download started")
    if headphones.CONFIG.OSX_NOTIFY_ENABLED and headphones.CONFIG.OSX_NOTIFY_ONSNATCH:
        from headphones import cache
        c = cache.Cache()
        album_art = c.get_artwork_from_cache(None, rgid)
        logger.info(u"Sending OS X notification")
        osx_notify = notifiers.OSX_NOTIFY()
        osx_notify.notify(artist,
                          albumname,
                          'Snatched: ' + provider + '. ' + name,
                          image=album_art)
    if headphones.CONFIG.BOXCAR_ENABLED and headphones.CONFIG.BOXCAR_ONSNATCH:
        logger.info(u"Sending Boxcar2 notification")
        b2msg = 'From ' + provider + '<br></br>' + name
        boxcar = notifiers.BOXCAR()
        boxcar.notify('Headphones snatched: ' + title, b2msg, rgid)
    if headphones.CONFIG.EMAIL_ENABLED and headphones.CONFIG.EMAIL_ONSNATCH:
        logger.info(u"Sending Email notification")
        email = notifiers.Email()
        message = 'Snatched from ' + provider + '. ' + name
        email.notify("Snatched: " + title, message)


def verifyresult(title, artistterm, term, lossless):
    title = re.sub('[\.\-\/\_]', ' ', title)

    # if artistterm != 'Various Artists':
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

    # another attempt to weed out substrings. We don't want "Vol III" when we were looking for "Vol II"

    # Filter out remix search results (if we're not looking for it)
    if 'remix' not in term.lower() and 'remix' in title.lower():
        logger.info(
            "Removed %s from results because it's a remix album and we're not looking for a remix album right now.",
            title)
        return False

    # Filter out FLAC if we're not specifically looking for it
    if headphones.CONFIG.PREFERRED_QUALITY == (
            0 or '0') and 'flac' in title.lower() and not lossless:
        logger.info(
            "Removed %s from results because it's a lossless album and we're not looking for a lossless album right now.",
            title)
        return False

    if headphones.CONFIG.IGNORED_WORDS:
        for each_word in helpers.split_string(headphones.CONFIG.IGNORED_WORDS):
            if each_word.lower() in title.lower():
                logger.info("Removed '%s' from results because it contains ignored word: '%s'",
                            title, each_word)
                return False

    if headphones.CONFIG.REQUIRED_WORDS:
        for each_word in helpers.split_string(headphones.CONFIG.REQUIRED_WORDS):
            if ' OR ' in each_word:
                or_words = helpers.split_string(each_word, 'OR')
                if any(word.lower() in title.lower() for word in or_words):
                    continue
                else:
                    logger.info(
                        "Removed '%s' from results because it doesn't contain any of the required words in: '%s'",
                        title, str(or_words))
                    return False
            if each_word.lower() not in title.lower():
                logger.info(
                    "Removed '%s' from results because it doesn't contain required word: '%s'",
                    title, each_word)
                return False

    if headphones.CONFIG.IGNORE_CLEAN_RELEASES:
        for each_word in ['clean', 'edited', 'censored']:
            logger.debug("Checking if '%s' is in search result: '%s'", each_word, title)
            if each_word.lower() in title.lower() and each_word.lower() not in term.lower():
                logger.info("Removed '%s' from results because it contains clean album word: '%s'",
                            title, each_word)
                return False

    tokens = re.split('\W', term, re.IGNORECASE | re.UNICODE)
    for token in tokens:

        if not token:
            continue
        if token == 'Various' or token == 'Artists' or token == 'VA':
            continue
        if not re.search('(?:\W|^)+' + token + '(?:\W|$)+', title, re.IGNORECASE | re.UNICODE):
            cleantoken = ''.join(c for c in token if c not in string.punctuation)
            if not not re.search('(?:\W|^)+' + cleantoken + '(?:\W|$)+', title,
                                 re.IGNORECASE | re.UNICODE):
                dic = {'!': 'i', '$': 's'}
                dumbtoken = helpers.replace_all(token, dic)
                if not not re.search('(?:\W|^)+' + dumbtoken + '(?:\W|$)+', title,
                                     re.IGNORECASE | re.UNICODE):
                    logger.info("Removed from results: %s (missing tokens: %s and %s)", title,
                                token, cleantoken)
                    return False

    return True


def searchTorrent(album, new=False, losslessOnly=False, albumlength=None,
                  choose_specific_download=False):
    global orpheusobj  # persistent orpheus.network api object to reduce number of login attempts
    global redobj  # persistent redacted api object to reduce number of login attempts
    global ruobj  # and rutracker

    reldate = album['ReleaseDate']

    year = get_year_from_release_date(reldate)

    # MERGE THIS WITH THE TERM CLEANUP FROM searchNZB
    dic = {'...': '', ' & ': ' ', ' = ': ' ', '?': '', '$': 's', ' + ': ' ', '"': '', ',': ' ',
           '*': ''}

    semi_cleanalbum = helpers.replace_all(album['AlbumTitle'], dic)
    cleanalbum = helpers.latinToAscii(semi_cleanalbum)
    semi_cleanartist = helpers.replace_all(album['ArtistName'], dic)
    cleanartist = helpers.latinToAscii(semi_cleanartist)

    # Use provided term if available, otherwise build our own (this code needs to be cleaned up since a lot
    # of these torrent providers are just using cleanartist/cleanalbum terms
    if album['SearchTerm']:
        term = album['SearchTerm']
    elif album['Type'] == 'part of':
        term = cleanalbum + " " + year
    else:
        # FLAC usually doesn't have a year for some reason so I'll leave it out
        # Various Artist albums might be listed as VA, so I'll leave that out too
        # Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
        if album['ArtistName'] in album['AlbumTitle'] or len(album['ArtistName']) < 4 or len(
                album['AlbumTitle']) < 4:
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
    albumterm = re.sub('[\.\-\/]', ' ', cleanalbum).encode('utf-8', 'replace')

    # If Preferred Bitrate and High Limit and Allow Lossless then get both lossy and lossless
    if headphones.CONFIG.PREFERRED_QUALITY == 2 and headphones.CONFIG.PREFERRED_BITRATE and headphones.CONFIG.PREFERRED_BITRATE_HIGH_BUFFER and headphones.CONFIG.PREFERRED_BITRATE_ALLOW_LOSSLESS:
        allow_lossless = True
    else:
        allow_lossless = False

    logger.debug("Using search term: %s" % term)

    resultlist = []
    minimumseeders = int(headphones.CONFIG.NUMBEROFSEEDERS) - 1

    def set_proxy(proxy_url):
        if not proxy_url.startswith('http'):
            proxy_url = 'http://' + proxy_url
        if proxy_url.endswith('/'):
            proxy_url = proxy_url[:-1]

        return proxy_url

    if headphones.CONFIG.TORZNAB:
        provider = "torznab"
        torznab_hosts = []

        if headphones.CONFIG.TORZNAB_HOST and headphones.CONFIG.TORZNAB_ENABLED:
            torznab_hosts.append((headphones.CONFIG.TORZNAB_HOST, headphones.CONFIG.TORZNAB_APIKEY,
                                  headphones.CONFIG.TORZNAB_RATIO, headphones.CONFIG.TORZNAB_ENABLED))

        for torznab_host in headphones.CONFIG.get_extra_torznabs():
            if torznab_host[3] == '1' or torznab_host[3] == 1:
                torznab_hosts.append(torznab_host)

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            categories = "3040"
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            categories = "3040,3010,3050"
            maxsize = 10000000000
        else:
            categories = "3010,3050"
            maxsize = 300000000

        if album['Type'] == 'Other':
            categories = "3030"
            logger.info("Album type is audiobook/spokenword. Using audiobook category")

        for torznab_host in torznab_hosts:

            provider = torznab_host[0]

            # Format Jackett provider
            if "api/v2.0/indexers" in torznab_host[0]:
                provider = "Jackett_" + provider.split("/indexers/", 1)[1].split('/', 1)[0]

            # Request results
            logger.info('Parsing results from %s using search term: %s' % (provider, term))

            headers = {'User-Agent': USER_AGENT}
            params = {
                "t": "search",
                "apikey": torznab_host[1],
                "cat": categories,
                "maxage": headphones.CONFIG.USENET_RETENTION,
                "q": term
            }

            data = request.request_soup(
                url=torznab_host[0],
                params=params, headers=headers
            )

            # Process feed
            if data:
                items = data.find_all('item')
                if not items:
                    logger.info(u"No results found from %s for %s", provider, term)
                else:
                    for item in items:
                        try:
                            title = item.title.get_text()
                            url = item.find("link").next_sibling.strip()
                            seeders = int(item.find("torznab:attr", attrs={"name": "seeders"}).get('value'))

                            # Torrentech hack - size currently not returned, make it up
                            if 'torrentech' in torznab_host[0]:
                                if albumlength:
                                    if 'Lossless' in title:
                                        size = albumlength / 1000 * 800 * 128
                                    elif 'MP3' in title:
                                        size = albumlength / 1000 * 320 * 128
                                    else:
                                        size = albumlength / 1000 * 256 * 128
                                else:
                                    logger.info('Skipping %s, could not determine size' % title)
                                    continue
                            elif item.size:
                                size = int(item.size.string)
                            else:
                                size = int(item.find("torznab:attr", attrs={"name": "size"}).get('value'))

                            if all(word.lower() in title.lower() for word in term.split()):
                                if size < maxsize and minimumseeders < seeders:
                                    logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                                    resultlist.append((title, size, url, provider, 'torrent', True))
                                else:
                                    logger.info(
                                        '%s is larger than the maxsize or has too little seeders for this category, '
                                        'skipping. (Size: %i bytes, Seeders: %d)',
                                        title, size, seeders)
                            else:
                                logger.info('Skipping %s, not all search term words found' % title)

                        except Exception as e:
                            logger.exception(
                                "An unknown error occurred trying to parse the feed: %s" % e)

    if headphones.CONFIG.WAFFLES:
        provider = "Waffles.ch"
        providerurl = fix_url("https://waffles.ch/browse.php")

        bitrate = None
        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            format = "FLAC"
            bitrate = "(Lossless)"
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
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
                            'size:[0 TO %d]' % maxsize])
        # (25/03/2017 Waffles back up after 5 months, all torrents currently have no seeders, remove for now)
        # '-seeders:0'])  cut out dead torrents

        if bitrate:
            query_items.append('bitrate:"%s"' % bitrate)

        # Requesting content
        logger.info('Parsing results from Waffles.ch')

        params = {
            "uid": headphones.CONFIG.WAFFLES_UID,
            "passkey": headphones.CONFIG.WAFFLES_PASSKEY,
            "rss": "1",
            "c0": "1",
            "s": "seeders",  # sort by
            "d": "desc",  # direction
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
                logger.info(u"No results found from %s for %s", provider, term)
            else:
                for item in data.entries:
                    try:
                        title = item.title
                        desc_match = re.search(r"Size: (\d+)<", item.description)
                        size = int(desc_match.group(1))
                        url = item.link
                        resultlist.append((title, size, url, provider, 'torrent', True))
                        logger.info('Found %s. Size: %s', title, helpers.bytes_to_mb(size))
                    except Exception as e:
                        logger.error(
                            u"An error occurred while trying to parse the response from Waffles.ch: %s",
                            e)

    # rutracker.org
    if headphones.CONFIG.RUTRACKER:
        provider = "rutracker.org"

        # Ignore if release date not specified, results too unpredictable
        if not year and not usersearchterm:
            logger.info(u"Release date not specified, ignoring for rutracker.org")
        else:
            if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
                format = 'lossless'
            elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
                format = 'lossless+mp3'
            else:
                format = 'mp3'

            # Login
            if not ruobj or not ruobj.logged_in():
                ruobj = rutracker.Rutracker()
                if not ruobj.login():
                    ruobj = None

            if ruobj and ruobj.logged_in():

                # build search url
                if not usersearchterm:
                    searchURL = ruobj.searchurl(artistterm, albumterm, year, format)
                else:
                    searchURL = ruobj.searchurl(usersearchterm, ' ', ' ', format)

                # parse results
                rulist = ruobj.search(searchURL)
                if rulist:
                    resultlist.extend(rulist)

    if headphones.CONFIG.ORPHEUS:
        provider = "Orpheus.network"
        providerurl = "http://orpheus.network/"

        bitrate = None
        bitrate_string = bitrate

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:  # Lossless Only mode
            search_formats = [gazelleformat.FLAC]
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 2:  # Preferred quality mode
            search_formats = [None]  # should return all
            bitrate = headphones.CONFIG.PREFERRED_BITRATE
            if bitrate:
                if 225 <= int(bitrate) < 256:
                    bitrate = 'V0'
                elif 200 <= int(bitrate) < 225:
                    bitrate = 'V1'
                elif 175 <= int(bitrate) < 200:
                    bitrate = 'V2'
                for encoding_string in gazelleencoding.ALL_ENCODINGS:
                    if re.search(bitrate, encoding_string, flags=re.I):
                        bitrate_string = encoding_string
                if bitrate_string not in gazelleencoding.ALL_ENCODINGS:
                    logger.info(
                        u"Your preferred bitrate is not one of the available Orpheus.network filters, so not using it as a search parameter.")
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:  # Highest quality including lossless
            search_formats = [gazelleformat.FLAC, gazelleformat.MP3]
            maxsize = 10000000000
        else:  # Highest quality excluding lossless
            search_formats = [gazelleformat.MP3]
            maxsize = 300000000

        if not orpheusobj or not orpheusobj.logged_in():
            try:
                logger.info(u"Attempting to log in to Orpheus.network...")
                orpheusobj = gazelleapi.GazelleAPI(headphones.CONFIG.ORPHEUS_USERNAME,
                                                headphones.CONFIG.ORPHEUS_PASSWORD,
                                                headphones.CONFIG.ORPHEUS_URL)
                orpheusobj._login()
            except Exception as e:
                orpheusobj = None
                logger.error(u"Orpheus.network credentials incorrect or site is down. Error: %s %s" % (
                    e.__class__.__name__, str(e)))

        if orpheusobj and orpheusobj.logged_in():
            logger.info(u"Searching %s..." % provider)
            all_torrents = []

            album_type = ""

            # Specify release types to filter by
            if album['Type'] == 'Album':
                album_type = [gazellerelease_type.ALBUM]
            if album['Type'] == 'Soundtrack':
                album_type = [gazellerelease_type.SOUNDTRACK]
            if album['Type'] == 'EP':
                album_type = [gazellerelease_type.EP]
            # No musicbrainz match for this type
            # if album['Type'] == 'Anthology':
            #   album_type = [gazellerelease_type.ANTHOLOGY]
            if album['Type'] == 'Compilation':
                album_type = [gazellerelease_type.COMPILATION]
            if album['Type'] == 'DJ-mix':
                album_type = [gazellerelease_type.DJ_MIX]
            if album['Type'] == 'Single':
                album_type = [gazellerelease_type.SINGLE]
            if album['Type'] == 'Live':
                album_type = [gazellerelease_type.LIVE_ALBUM]
            if album['Type'] == 'Remix':
                album_type = [gazellerelease_type.REMIX]
            if album['Type'] == 'Bootleg':
                album_type = [gazellerelease_type.BOOTLEG]
            if album['Type'] == 'Interview':
                album_type = [gazellerelease_type.INTERVIEW]
            if album['Type'] == 'Mixtape/Street':
                album_type = [gazellerelease_type.MIXTAPE]
            if album['Type'] == 'Other':
                album_type = [gazellerelease_type.UNKNOWN]

            for search_format in search_formats:
                if usersearchterm:
                    all_torrents.extend(
                        orpheusobj.search_torrents(searchstr=usersearchterm, format=search_format,
                                                encoding=bitrate_string, releasetype=album_type)['results'])
                else:
                    all_torrents.extend(orpheusobj.search_torrents(artistname=semi_clean_artist_term,
                                                                groupname=semi_clean_album_term,
                                                                format=search_format,
                                                                encoding=bitrate_string,
                                                                releasetype=album_type)['results'])

            # filter on format, size, and num seeders
            logger.info(u"Filtering torrents by format, maximum size, and minimum seeders...")
            match_torrents = [t for t in all_torrents if
                              t.size <= maxsize and t.seeders >= minimumseeders]

            logger.info(
                u"Remaining torrents: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            # sort by times d/l'd
            if not len(match_torrents):
                logger.info(u"No results found from %s for %s after filtering" % (provider, term))
            elif len(match_torrents) > 1:
                logger.info(u"Found %d matching releases from %s for %s - %s after filtering" %
                            (len(match_torrents), provider, artistterm, albumterm))
                logger.info('Sorting torrents by number of seeders...')
                match_torrents.sort(key=lambda x: int(x.seeders), reverse=True)
                if gazelleformat.MP3 in search_formats:
                    logger.info('Sorting torrents by seeders...')
                    match_torrents.sort(key=lambda x: int(x.seeders), reverse=True)
                if search_formats and None not in search_formats:
                    match_torrents.sort(
                        key=lambda x: int(search_formats.index(x.format)))  # prefer lossless
                #                if bitrate:
                #                    match_torrents.sort(key=lambda x: re.match("mp3", x.getTorrentDetails(), flags=re.I), reverse=True)
                #                    match_torrents.sort(key=lambda x: str(bitrate) in x.getTorrentFolderName(), reverse=True)
                logger.info(
                    u"New order: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            for torrent in match_torrents:
                if not torrent.file_path:
                    torrent.group.update_group_data()  # will load the file_path for the individual torrents
                resultlist.append((torrent.file_path,
                                   torrent.size,
                                   orpheusobj.generate_torrent_link(torrent.id),
                                   provider,
                                   'torrent', True))

    # Redacted - Using same logic as What.CD as it's also Gazelle, so should really make this into something reusable
    if headphones.CONFIG.REDACTED:
        provider = "Redacted"
        providerurl = "https://redacted.ch"

        bitrate = None
        bitrate_string = bitrate

        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:  # Lossless Only mode
            search_formats = [gazelleformat.FLAC]
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 2:  # Preferred quality mode
            search_formats = [None]  # should return all
            bitrate = headphones.CONFIG.PREFERRED_BITRATE
            if bitrate:
                if 225 <= int(bitrate) < 256:
                    bitrate = 'V0'
                elif 200 <= int(bitrate) < 225:
                    bitrate = 'V1'
                elif 175 <= int(bitrate) < 200:
                    bitrate = 'V2'
                for encoding_string in gazelleencoding.ALL_ENCODINGS:
                    if re.search(bitrate, encoding_string, flags=re.I):
                        bitrate_string = encoding_string
                if bitrate_string not in gazelleencoding.ALL_ENCODINGS:
                    logger.info(
                        u"Your preferred bitrate is not one of the available RED filters, so not using it as a search parameter.")
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:  # Highest quality including lossless
            search_formats = [gazelleformat.FLAC, gazelleformat.MP3]
            maxsize = 10000000000
        else:  # Highest quality excluding lossless
            search_formats = [gazelleformat.MP3]
            maxsize = 300000000

        if not redobj or not redobj.logged_in():
            try:
                logger.info(u"Attempting to log in to Redacted...")
                redobj = gazelleapi.GazelleAPI(headphones.CONFIG.REDACTED_USERNAME,
                                                headphones.CONFIG.REDACTED_PASSWORD,
                                                providerurl)
                redobj._login()
            except Exception as e:
                redobj = None
                logger.error(u"Redacted credentials incorrect or site is down. Error: %s %s" % (
                    e.__class__.__name__, str(e)))

        if redobj and redobj.logged_in():
            logger.info(u"Searching %s..." % provider)
            all_torrents = []
            for search_format in search_formats:
                if usersearchterm:
                    all_torrents.extend(
                        redobj.search_torrents(searchstr=usersearchterm, format=search_format,
                                                encoding=bitrate_string)['results'])
                else:
                    all_torrents.extend(redobj.search_torrents(artistname=semi_clean_artist_term,
                                                                groupname=semi_clean_album_term,
                                                                format=search_format,
                                                                encoding=bitrate_string)['results'])

            # filter on format, size, and num seeders
            logger.info(u"Filtering torrents by format, maximum size, and minimum seeders...")
            match_torrents = [t for t in all_torrents if
                              t.size <= maxsize and t.seeders >= minimumseeders]

            logger.info(
                u"Remaining torrents: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            # sort by times d/l'd
            if not len(match_torrents):
                logger.info(u"No results found from %s for %s after filtering" % (provider, term))
            elif len(match_torrents) > 1:
                logger.info(u"Found %d matching releases from %s for %s - %s after filtering" %
                            (len(match_torrents), provider, artistterm, albumterm))
                logger.info(
                    "Sorting torrents by times snatched and preferred bitrate %s..." % bitrate_string)
                match_torrents.sort(key=lambda x: int(x.snatched), reverse=True)
                if gazelleformat.MP3 in search_formats:
                    # sort by size after rounding to nearest 10MB...hacky, but will favor highest quality
                    match_torrents.sort(key=lambda x: int(10 * round(x.size / 1024. / 1024. / 10.)),
                                        reverse=True)
                if search_formats and None not in search_formats:
                    match_torrents.sort(
                        key=lambda x: int(search_formats.index(x.format)))  # prefer lossless
                #                if bitrate:
                #                    match_torrents.sort(key=lambda x: re.match("mp3", x.getTorrentDetails(), flags=re.I), reverse=True)
                #                    match_torrents.sort(key=lambda x: str(bitrate) in x.getTorrentFolderName(), reverse=True)
                logger.info(
                    u"New order: %s" % ", ".join(repr(torrent) for torrent in match_torrents))

            for torrent in match_torrents:
                if not torrent.file_path:
                    torrent.group.update_group_data()  # will load the file_path for the individual torrents
                use_token = headphones.CONFIG.REDACTED_USE_FLTOKEN and torrent.can_use_token
                resultlist.append((torrent.file_path,
                                   torrent.size,
                                   redobj.generate_torrent_link(torrent.id, use_token),
                                   provider,
                                   'torrent', True))

    # Pirate Bay
    if headphones.CONFIG.PIRATEBAY:
        provider = "The Pirate Bay"
        tpb_term = term.replace("!", "").replace("'", " ")

        # Use proxy if specified
        if headphones.CONFIG.PIRATEBAY_PROXY_URL:
            providerurl = fix_url(set_proxy(headphones.CONFIG.PIRATEBAY_PROXY_URL))
        else:
            providerurl = fix_url("https://thepiratebay.org")

        # Build URL
        providerurl = providerurl + "/search/" + tpb_term + "/0/7/"  # 7 is sort by seeders

        # Pick category for torrents
        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            category = '104'  # FLAC
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            category = '100'  # General audio category
            maxsize = 10000000000
        else:
            category = '101'  # MP3 only
            maxsize = 300000000

        # Request content
        logger.info("Searching The Pirate Bay using term: %s", tpb_term)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'}
        data = request.request_soup(url=providerurl + category, headers=headers)

        # Process content
        if data:
            rows = data.select('table tbody tr')

            if not rows:
                logger.info("No results found from The Pirate Bay using term: %s" % tpb_term)
            else:
                for item in rows:
                    try:
                        url = None
                        title = ''.join(item.find("a", {"class": "detLink"}))
                        seeds = int(''.join(item.find("td", {"align": "right"})))

                        if headphones.CONFIG.TORRENT_DOWNLOADER == 0:
                            try:
                                url = item.find("a", {"title": "Download this torrent"})['href']
                            except TypeError:
                                if headphones.CONFIG.MAGNET_LINKS != 0:
                                    url = item.findAll("a")[3]['href']
                                else:
                                    logger.info('"%s" only has a magnet link, skipping' % title)
                                    continue
                        else:
                            url = item.findAll("a")[3]["href"]

                        if url.lower().startswith("//"):
                            url = "http:" + url

                        formatted_size = re.search('Size (.*),', unicode(item)).group(1).replace(
                            u'\xa0', ' ')
                        size = helpers.piratesize(formatted_size)

                        if size < maxsize and minimumseeders < seeds and url is not None:
                            match = True
                            logger.info('Found %s. Size: %s' % (title, formatted_size))
                        else:
                            match = False
                            logger.info('%s is larger than the maxsize or has too little seeders for this category, '
                                        'skipping. (Size: %i bytes, Seeders: %i)' % (title, size, int(seeds)))

                        resultlist.append((title, size, url, provider, "torrent", match))
                    except Exception as e:
                        logger.error(u"An unknown error occurred in the Pirate Bay parser: %s" % e)

    # Old Pirate Bay Compatible
    if headphones.CONFIG.OLDPIRATEBAY:
        provider = "Old Pirate Bay"
        tpb_term = term.replace("!", "")

        # Pick category for torrents
        if headphones.CONFIG.PREFERRED_QUALITY == 3 or losslessOnly:
            maxsize = 10000000000
        elif headphones.CONFIG.PREFERRED_QUALITY == 1 or allow_lossless:
            maxsize = 10000000000
        else:
            maxsize = 300000000

        # Requesting content
        logger.info("Parsing results from Old Pirate Bay")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'}
        provider_url = fix_url(headphones.CONFIG.OLDPIRATEBAY_URL) + \
                       "/search.php?" + urllib.urlencode({"q": tpb_term, "iht": 6})

        data = request.request_soup(url=provider_url, headers=headers)

        # Process content
        if data:
            rows = data.select('table tbody tr')

            if not rows:
                logger.info("No results found")
            else:
                for item in rows:
                    try:
                        links = item.select("td.title-row a")

                        title = links[1].text
                        seeds = int(item.select("td.seeders-row")[0].text)
                        url = links[0][
                            "href"]  # Magnet link. The actual download link is not based on the URL

                        formatted_size = item.select("td.size-row")[0].text
                        size = helpers.piratesize(formatted_size)

                        if size < maxsize and minimumseeders < seeds and url is not None:
                            match = True
                            logger.info('Found %s. Size: %s' % (title, formatted_size))
                        else:
                            match = False
                            logger.info('%s is larger than the maxsize or has too little seeders for this category, '
                                        'skipping. (Size: %i bytes, Seeders: %i)' % (title, size, int(seeds)))

                        resultlist.append((title, size, url, provider, "torrent", match))
                    except Exception as e:
                        logger.error(
                            u"An unknown error occurred in the Old Pirate Bay parser: %s" % e)

    # attempt to verify that this isn't a substring result
    # when looking for "Foo - Foo" we don't want "Foobar"
    # this should be less of an issue when it isn't a self-titled album so we'll only check vs artist
    results = [result for result in resultlist if verifyresult(result[0], artistterm, term, losslessOnly)]

    # Additional filtering for size etc
    # if results and not choose_specific_download and result[3] != 'Orpheus.network':
    if results and not choose_specific_download:
        results = more_filtering(results, album, albumlength, new)

    return results


# THIS IS KIND OF A MESS AND PROBABLY NEEDS TO BE CLEANED UP


def preprocess(resultlist):
    for result in resultlist:
        if result[4] == 'torrent':

            headers = {}

            # rutracker always needs the torrent data
            if result[3] == 'rutracker.org':
                return ruobj.get_torrent_data(result[2]), result

            # Jackett sometimes redirects
            jackett_content = None
            if result[3].startswith('Jackett_') or 'torznab' in result[3].lower():
                r = request.request_response(url=result[2], headers=headers, allow_redirects=False)
                if r:
                    jackett_content = r.content
                    link = r.headers.get('Location')
                    if link and link != result[2]:
                        if link.startswith('magnet:'):
                            result = (result[0], result[1], link, result[3], "magnet", result[5])
                            return "d10:magnet-uri%d:%se" % (len(link), link), result
                        else:
                            result = (result[0], result[1], link, result[3], result[4], result[5])
                            return True, result

            # Get out of here if we're using Transmission or Deluge
            # if not a magnet link still need the .torrent to generate hash... uTorrent support labeling
            if headphones.CONFIG.TORRENT_DOWNLOADER in [1, 3]:
                return True, result

            # Get out of here if it's a magnet link
            if result[2].lower().startswith("magnet:"):
                return True, result

            # Download the torrent file

            if result[3] == 'Orpheus.network':
                headers['User-Agent'] = 'Headphones'
            elif result[3] == 'Redacted':
                headers['User-Agent'] = 'Headphones'
            elif result[3] == "The Pirate Bay" or result[3] == "Old Pirate Bay":
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'
            elif jackett_content:
                return jackett_content, result

            return request.request_content(url=result[2], headers=headers), result

        if result[4] == 'magnet':
            magnet_link = result[2]
            return "d10:magnet-uri%d:%se" % (len(magnet_link), magnet_link), result

        else:
            headers = {'User-Agent': USER_AGENT}

            if result[3] == 'headphones':
                return request.request_content(url=result[2], headers=headers,
                                               auth=(headphones.CONFIG.HPUSER, headphones.CONFIG.HPPASS)), result
            else:
                return request.request_content(url=result[2], headers=headers), result
