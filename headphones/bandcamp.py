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

from headphones import logger, helpers, request
from headphones.common import USER_AGENT

def search(album, albumlength=None, page=1):
    dic = {'...': '', ' & ': ' ', ' = ': ' ', '?': '', '$': 's', ' + ': ' ', '"': '', ',': '',
           '*': '', '.': '', ':': ''}

    cleanalbum = helpers.latinToAscii(helpers.replace_all(album['AlbumTitle'], dic)).strip()
    cleanartist = helpers.latinToAscii(helpers.replace_all(album['ArtistName'], dic)).strip()

    headers = {'User-Agent': USER_AGENT}
    params = {
        "page": page,
        "q": cleanalbum,
    }
    logger.debug("Looking up http://bandcamp.com/search with {}".format(params))
    soup = request.request_soup(
        url='https://bandcamp.com/search', params=params, headers=headers)

    resultlist = []

    for item in soup.find_all("li", class_="searchresult"):
        type = item.find('div', class_='itemtype').text.strip().lower()
        if type == "album":
            data = parse_album(item)

            cleanartist_found = helpers.latinToAscii(helpers.replace_all(data['artist'], dic)).strip()
            cleanalbum_found = helpers.latinToAscii(helpers.replace_all(data['album'], dic)).strip()

            if cleanartist.lower() == cleanartist_found.lower() and cleanalbum.lower()  == cleanalbum_found.lower():
                resultlist.append((data['title'], data['size'], data['url'], 'bandcamp', 'bandcamp', True))
        else:
            continue

    return resultlist

def download(album, bestqual):
    html = request.request_content(url=bestqual[2])
    trackinfo= []
    try:
        trackinfo = json.loads(re.search(r"trackinfo: (\[.*?\]),",html).group(1))
    except:
        logger.warn("Couldn't load json")

    directory = os.path.join(
        headphones.CONFIG.BANDCAMP_DIR,
        "{} - {}".format(
            helpers.latinToAscii(album['ArtistName']).encode('UTF-8').replace('/', '_'),
            helpers.latinToAscii(album['AlbumTitle']).encode('UTF-8').replace('/', '_')))

    if not os.path.exists(directory):
        try:
            logger.debug("Creating directory {}".format(directory))
            os.makedirs(directory)
        except Exception as e:
            logger.warn("Could not create directory {} ({})".format(directory, e))

    index = 1
    for track in trackinfo:
        filename  = helpers.replace_illegal_chars(
                    "{:02d} - {}.mp3".format(index, track['title']))
        fullname  = os.path.join(directory, filename)
        logger.debug("Downloading to {}".format(fullname))

        if track['file']['mp3-128']:
            content = request.request_content(track['file']['mp3-128'])
            open(fullname, 'wb').write(content)

        index += 1

    logger.info("Returning directory {}".format(directory))
    return directory

def parse_album(item):
    album = item.find('div', class_='heading').text.strip()
    artist = item.find('div', class_='subhead').text.strip().replace("by ", "")
    released = item.find('div', class_='released').text.strip().replace(
        "released ", "")
    year = re.search(r"(\d{4})", released).group(1)

    url = item.find('div', class_='heading').find('a')['href'].split("?")[0]

    lenght = item.find('div', class_='length').text.strip()
    tracks, minutes = lenght.split(",")
    tracks = tracks.replace(" tracks", "").replace(" track", "").strip()
    minutes = minutes.replace(" minutes", "").strip()
    # bandcamp offers mp3 128b with should be 960KB/minute
    size = int(minutes) * 983040

    data = {"title": "{} - {} [{}]".format(artist, album, year),
            "artist": artist, "album": album,
            "url": url, "size": size}

    #logger.debug("Found {}".format(data['title']))
    return data