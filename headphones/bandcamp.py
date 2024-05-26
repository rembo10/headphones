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
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>

import headphones
import json
import os
import re

from headphones import logger, helpers, metadata, request
from headphones.common import USER_AGENT
from headphones.types import Result

from mediafile import MediaFile, UnreadableFileError
from bs4 import BeautifulSoup
from bs4 import FeatureNotFound


def search(album, albumlength=None, page=1, resultlist=None):
    dic = {'...': '', ' & ': ' ', ' = ': ' ', '?': '', '$': 's', ' + ': ' ',
           '"': '', ',': '', '*': '', '.': '', ':': ''}
    if resultlist is None:
        resultlist = []

    cleanalbum = helpers.latinToAscii(
        helpers.replace_all(album['AlbumTitle'], dic)
        ).strip()
    cleanartist = helpers.latinToAscii(
        helpers.replace_all(album['ArtistName'], dic)
        ).strip()

    headers = {'User-Agent': USER_AGENT}
    params = {
        "page": page,
        "q": cleanalbum,
    }
    logger.info("Looking up https://bandcamp.com/search with {}".format(
        params))
    content = request.request_content(
        url='https://bandcamp.com/search',
        params=params,
        headers=headers
        ).decode('utf8')
    try:
        soup = BeautifulSoup(content, "html5lib")
    except FeatureNotFound:
        soup = BeautifulSoup(content, "html.parser")

    for item in soup.find_all("li", class_="searchresult"):
        type = item.find('div', class_='itemtype').text.strip().lower()
        if type == "album":
            data = parse_album(item)

            cleanartist_found = helpers.latinToAscii(data['artist'])
            cleanalbum_found = helpers.latinToAscii(data['album'])

            logger.debug(u"{} - {}".format(data['album'], cleanalbum_found))

            logger.debug("Comparing {} to {}".format(
                cleanalbum, cleanalbum_found))
            if (cleanartist.lower() == cleanartist_found.lower() and
                    cleanalbum.lower() == cleanalbum_found.lower()):
                resultlist.append(Result(
                    data['title'], data['size'], data['url'],
                    'bandcamp', 'bandcamp', True))
        else:
            continue

    if(soup.find('a', class_='next')):
        page += 1
        logger.debug("Calling next page ({})".format(page))
        search(album, albumlength=albumlength,
               page=page, resultlist=resultlist)

    return resultlist


def download(album, bestqual):
    html = request.request_content(url=bestqual.url).decode('utf-8')
    trackinfo = []
    try:
        trackinfo = json.loads(
            re.search(r"trackinfo&quot;:(\[.*?\]),", html)
            .group(1)
            .replace('&quot;', '"'))
    except ValueError as e:
        logger.warn("Couldn't load json: {}".format(e))

    directory = os.path.join(
        headphones.CONFIG.BANDCAMP_DIR,
        u'{} - {}'.format(
            album['ArtistName'].replace('/', '_'),
            album['AlbumTitle'].replace('/', '_')))
    directory = helpers.latinToAscii(directory)

    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except Exception as e:
            logger.warn("Could not create directory ({})".format(e))

    index = 1
    for track in trackinfo:
        filename = helpers.replace_illegal_chars(
                    u'{:02d} - {}.mp3'.format(index, track['title']))
        fullname = os.path.join(directory.encode('utf-8'),
                                filename.encode('utf-8'))
        logger.debug("Downloading to {}".format(fullname))

        if 'file' in track and track['file'] != None and 'mp3-128' in track['file']:
            content = request.request_content(track['file']['mp3-128'])
            open(fullname, 'wb').write(content)
            try:
                f = MediaFile(fullname)
                date, year = metadata._date_year(album)
                f.update({
                    'artist': album['ArtistName'].encode('utf-8'),
                    'album': album['AlbumTitle'].encode('utf-8'),
                    'title': track['title'].encode('utf-8'),
                    'track': track['track_num'],
                    'tracktotal': len(trackinfo),
                    'year': year,
                })
                f.save()
            except UnreadableFileError as ex:
                logger.warn("MediaFile couldn't parse: %s (%s)",
                            fullname,
                            str(ex))

        index += 1

    return directory


def parse_album(item):
    album = item.find('div', class_='heading').text.strip()
    artist = item.find('div', class_='subhead').text.strip().replace("by ", "")
    released = item.find('div', class_='released').text.strip().replace(
        "released ", "")
    year = re.search(r"(\d{4})", released).group(1)

    url = item.find('div', class_='heading').find('a')['href'].split("?")[0]

    length = item.find('div', class_='length').text.strip()
    tracks, minutes = length.split(",")
    tracks = tracks.replace(" tracks", "").replace(" track", "").strip()
    minutes = minutes.replace(" minutes", "").strip()
    # bandcamp offers mp3 128b with should be 960KB/minute
    size = int(minutes) * 983040

    data = {"title": u'{} - {} [{}]'.format(artist, album, year),
            "artist": artist, "album": album,
            "url": url, "size": size}

    return data
