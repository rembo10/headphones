# -*- coding: utf-8 -*-
# Deezloader (c) 2016 by ParadoxalManiak
#
# Deezloader is licensed under a
# Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#
# You should have received a copy of the license along with this
# work. If not, see <http://creativecommons.org/licenses/by-nc-sa/3.0/>.
#
# Version 2.1.0
# Maintained by ParadoxalManiak <https://www.reddit.com/user/ParadoxalManiak/>
# Original work by ZzMTV <https://boerse.to/members/zzmtv.3378614/>
#
# Author's disclaimer:
#  I am not responsible for the usage of this program by other people.
#  I do not recommend you doing this illegally or against Deezer's terms of service.
#  This project is licensed under CC BY-NC-SA 4.0

import re
import os
from datetime import datetime
from hashlib import md5
import binascii

from beets.mediafile import MediaFile
from headphones import logger, request, helpers
from headphones.classes import OptionalImport, CacheDict
import headphones


# Try to import optional Crypto.Cipher packages
try:
    from Crypto.Cipher import AES, Blowfish
except ImportError:
    AES = OptionalImport('Crypto.Cipher.AES')
    Blowfish = OptionalImport('Crypto.Cipher.Blowfish')

# Public constants
PROVIDER_NAME = 'Deezer'

# Internal constants
__API_URL = "http://www.deezer.com/ajax/gw-light.php"
__API_INFO_URL = "http://api.deezer.com/"
__HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Content-Language": "en-US",
    "Cache-Control": "max-age=0",
    "Accept": "*/*",
    "Accept-Charset": "utf-8,ISO-8859-1;q=0.7,*;q=0.3",
    "Accept-Language": "de-DE,de;q=0.8,en-US;q=0.6,en;q=0.4"
}

# Internal variables
__api_queries = {
    'api_version': "1.0",
    'api_token': "None",
    'input': "3"
}
__cookies = None
__tracks_cache = CacheDict(size_limit=512)
__albums_cache = CacheDict(size_limit=64)


def __getApiToken():
    global __cookies
    response = request.request_response(url="http://www.deezer.com/", headers=__HTTP_HEADERS)
    __cookies = response.cookies
    data = response.content
    if data:
        matches = re.search(r"checkForm\s*=\s*['|\"](.*)[\"|'];", data)
        if matches:
            token = matches.group(1)
            __api_queries['api_token'] = token
            logger.debug(u"Deezloader : api token loaded ('%s')" % token)

    if not token:
        logger.error(u"Deezloader: Unable to get api token")


def getAlbumByLink(album_link):
    """Returns deezer album infos using album link url

    :param str album_link: deezer album link url (eg: 'http://www.deezer.com/album/1234567/')
    """
    matches = re.search(r"album\/([0-9]+)\/?$", album_link)
    if matches:
        return getAlbum(matches.group(1))


def getAlbum(album_id):
    """Returns deezer album infos

    :param int album_id: deezer album id
    """
    global __albums_cache

    if str(album_id) in __albums_cache:
        return __albums_cache[str(album_id)]

    url = __API_INFO_URL + "album/" + str(album_id)
    data = request.request_json(url=url, headers=__HTTP_HEADERS, cookies=__cookies)

    if data and 'error' not in data:
        __albums_cache[str(album_id)] = data
        return data
    else:
        logger.debug("Deezloader: Can't load album infos")
        return None


def searchAlbums(search_term):
    """Search for deezer albums using search term

    :param str search_term: search term to search album for
    """
    logger.info(u'Searching Deezer using term: "%s"' % search_term)

    url = __API_INFO_URL + "search/album?q=" + search_term
    data = request.request_json(url=url, headers=__HTTP_HEADERS, cookies=__cookies)

    albums = []

    # Process content
    if data and 'total' in data and data['total'] > 0 and 'data' in data:
        for item in data['data']:
            try:
                albums.append(getAlbum(item['id']))
            except Exception as e:
                logger.error(u"An unknown error occurred in the Deezer search album parser: %s" % e)
    else:
        logger.info(u'No results found from Deezer using term: "%s"' % search_term)

    return albums


def __matchAlbums(albums, artist_name, album_title, album_length):
    resultlist = []

    for album in albums:
        total_size = 0
        tracks_found = 0

        for track in album['tracks']['data']:
            t = getTrack(track['id'])
            if t:
                if t["FILESIZE_MP3_320"] > 0:
                    size = t["FILESIZE_MP3_320"]
                elif t["FILESIZE_MP3_256"] > 0:
                    size = t["FILESIZE_MP3_256"]
                elif t["FILESIZE_MP3_128"] > 0:
                    size = t["FILESIZE_MP3_128"]
                else:
                    size = t["FILESIZE_MP3_64"]

                size = int(size)
                total_size += size
                tracks_found += 1
                logger.debug(u'Found song "%s". Size: %s' % (t['SNG_TITLE'], helpers.bytes_to_mb(size)))

        if tracks_found == 0:
            logger.info(u'Ignoring album "%s" (no tracks to download)' % album['title'])
            continue

        matched = True
        mismatch_reason = 'matched!'

        if album_length > 0 and abs(int(album['duration']) - album_length) > 240:
            matched = False
            mismatch_reason = (u'duration mismatch: %i not in [%i, %i]' % (int(album['duration']), (album_length - 240), (album_length + 240)))

        elif (helpers.latinToAscii(re.sub(r"\W", "", album_title, 0, re.UNICODE)).lower() !=
              helpers.latinToAscii(re.sub(r"\W", "", album['title'], 0, re.UNICODE)).lower()):
            matched = False
            mismatch_reason = (u'album name mismatch: %s != %s' % (album['title'], album_title))

        elif (helpers.latinToAscii(re.sub(r"\W", "", artist_name, 0, re.UNICODE)).lower() !=
              helpers.latinToAscii(re.sub(r"\W", "", album['artist']['name'], 0, re.UNICODE)).lower()):
            matched = False
            mismatch_reason = (u'artist name mismatch: %s != %s' % (album['artist']['name'], artist_name))

        resultlist.append(
            (album['artist']['name'] + ' - ' + album['title'] + ' [' + album['release_date'][:4] + '] (' + str(tracks_found) + '/' + str(album['nb_tracks']) + ')',
            total_size, album['link'], PROVIDER_NAME, "ddl", matched)
        )
        logger.info(u'Found "%s". Tracks %i/%i. Size: %s (%s)' % (album['title'], tracks_found, album['nb_tracks'], helpers.bytes_to_mb(total_size), mismatch_reason))

    return resultlist


def searchAlbum(artist_name, album_title, user_search_term=None, album_length=None):
    """Search for deezer specific album.
    This will iterate over deezer albums and try to find best matches

    :param str artist_name: album artist name
    :param str album_title: album title
    :param str user_search_term: search terms provided by user
    :param int album_length: targeted album duration in seconds
    """
    # User search term by-pass normal search
    if user_search_term:
        return __matchAlbums(searchAlbums(user_search_term), artist_name, album_title, album_length)

    resultlist = __matchAlbums(searchAlbums((artist_name + ' ' + album_title).strip()), artist_name, album_title, album_length)
    if resultlist:
        return resultlist

    # Deezer API supports unicode, so just remove non alphanumeric characters
    clean_artist_name = re.sub(r"[^\w\s]", " ", artist_name, 0, re.UNICODE).strip()
    clean_album_name = re.sub(r"[^\w\s]", " ", album_title, 0, re.UNICODE).strip()

    resultlist = __matchAlbums(searchAlbums((clean_artist_name + ' ' + clean_album_name).strip()), artist_name, album_title, album_length)
    if resultlist:
        return resultlist

    resultlist = __matchAlbums(searchAlbums(clean_artist_name), artist_name, album_title, album_length)
    if resultlist:
        return resultlist

    return resultlist


def getTrack(sng_id, try_reload_api=True):
    """Returns deezer track infos

    :param int sng_id: deezer song id
    :param bool try_reload_api: whether or not try reloading API if session expired
    """
    global __tracks_cache

    if str(sng_id) in __tracks_cache:
        return __tracks_cache[str(sng_id)]

    data = "[{\"method\":\"song.getListData\",\"params\":{\"sng_ids\":[" + str(sng_id) + "]}}]"
    json = request.request_json(url=__API_URL, headers=__HTTP_HEADERS, method='post', params=__api_queries, data=data, cookies=__cookies)

    results = []
    error = None
    invalid_token = False

    if json:
        # Check for errors
        if 'error' in json:
            error = json['error']
            if 'GATEWAY_ERROR' in json['error'] and json['error']['GATEWAY_ERROR'] == u"invalid api token":
                invalid_token = True

        elif 'error' in json[0] and json[0]['error']:
            error = json[0]['error']
            if 'VALID_TOKEN_REQUIRED' in json[0]['error'] and json[0]['error']['VALID_TOKEN_REQUIRED'] == u"Invalid CSRF token":
                invalid_token = True

        # Got invalid token error
        if error:
            if invalid_token and try_reload_api:
                __getApiToken()
                return getTrack(sng_id, False)
            else:
                logger.error(u"An unknown error occurred in the Deezer track parser: %s" % error)
        else:
            try:
                results = json[0]['results']
                item = results['data'][0]
                if 'token' in item:
                    logger.error(u"An unknown error occurred in the Deezer parser: Uploaded Files are currently not supported")
                    return

                sng_id = item["SNG_ID"]
                md5Origin = item["MD5_ORIGIN"]
                sng_format = 3

                if item["FILESIZE_MP3_320"] <= 0:
                    if item["FILESIZE_MP3_256"] > 0:
                        sng_format = 5
                    else:
                        sng_format = 1

                mediaVersion = int(item["MEDIA_VERSION"])
                item['downloadUrl'] = __getDownloadUrl(md5Origin, sng_id, sng_format, mediaVersion)

                __tracks_cache[sng_id] = item
                return item

            except Exception as e:
                logger.error(u"An unknown error occurred in the Deezer track parser: %s" % e)


def __getDownloadUrl(md5Origin, sng_id, sng_format, mediaVersion):
    urlPart = md5Origin.encode('utf-8') + b'\xa4' + str(sng_format) + b'\xa4' + str(sng_id) + b'\xa4' + str(mediaVersion)
    md5val = md5(urlPart).hexdigest()
    urlPart = md5val + b'\xa4' + urlPart + b'\xa4'
    cipher = AES.new('jo6aey6haid2Teih', AES.MODE_ECB)
    ciphertext = cipher.encrypt(__pad(urlPart, AES.block_size))
    return "http://e-cdn-proxy-" + md5Origin[:1] + ".deezer.com/mobile/1/" + binascii.hexlify(ciphertext).lower()


def __pad(raw, block_size):
    if (len(raw) % block_size == 0):
        return raw
    padding_required = block_size - (len(raw) % block_size)
    padChar = b'\x00'
    data = raw + padding_required * padChar
    return data


def __tagTrack(path, track):
    try:
        album = getAlbum(track['ALB_ID'])

        f = MediaFile(path)
        f.artist = track['ART_NAME']
        f.album = track['ALB_TITLE']
        f.title = track['SNG_TITLE']
        f.track = track['TRACK_NUMBER']
        f.tracktotal = album['nb_tracks']
        f.disc = track['DISK_NUMBER']
        f.bpm = track['BPM']
        f.date = datetime.strptime(album['release_date'], '%Y-%m-%d').date()
        f.albumartist = album['artist']['name']
        if u'genres' in album and u'data' in album['genres']:
            f.genres = [genre['name'] for genre in album['genres']['data']]

        f.save()

    except Exception as e:
        logger.error(u'Unable to tag deezer track "%s": %s' % (path, e))


def decryptTracks(paths):
    """Decrypt downloaded deezer tracks.

    :param paths: list of path to deezer tracks (*.dzr files).
    """
    # Note: tracks can be from different albums
    decrypted_tracks = {}

    # First pass: load tracks data
    for path in paths:
        try:
            album_folder = os.path.dirname(path)
            sng_id = os.path.splitext(os.path.basename(path))[0]
            track = getTrack(sng_id)
            if track:
                track_number = int(track['TRACK_NUMBER'])
                disk_number = int(track['DISK_NUMBER'])

                if album_folder not in decrypted_tracks:
                    decrypted_tracks[album_folder] = {}

                if disk_number not in decrypted_tracks[album_folder]:
                    decrypted_tracks[album_folder][disk_number] = {}

                decrypted_tracks[album_folder][disk_number][track_number] = track

        except Exception as e:
            logger.error(u'Unable to load deezer track infos "%s": %s' % (path, e))

    # Second pass: decrypt tracks
    for album_folder in decrypted_tracks:
        multi_disks = len(decrypted_tracks[album_folder]) > 1
        for disk_number in decrypted_tracks[album_folder]:
            for track_number, track in decrypted_tracks[album_folder][disk_number].items():
                try:
                    filename = helpers.replace_illegal_chars(track['SNG_TITLE']).strip()
                    filename = ('{:02d}'.format(track_number) + '_' + filename + '.mp3')

                    # Add a 'cd x' sub-folder if album has more than one disk
                    disk_folder = os.path.join(album_folder, 'cd ' + str(disk_number)) if multi_disks else album_folder

                    dest = os.path.join(disk_folder, filename).encode(headphones.SYS_ENCODING, 'replace')

                    # Decrypt track if not already done
                    if not os.path.exists(dest):
                        try:
                            __decryptDownload(path, sng_id, dest)
                            __tagTrack(dest, track)
                        except Exception as e:
                            logger.error(u'Unable to decrypt deezer track "%s": %s' % (path, e))
                            if os.path.exists(dest):
                                os.remove(dest)
                            decrypted_tracks[album_folder][disk_number].pop(track_number)
                            continue

                    decrypted_tracks[album_folder][disk_number][track_number]['path'] = dest

                except Exception as e:
                    logger.error(u'Unable to decrypt deezer track "%s": %s' % (path, e))

    return decrypted_tracks


def __decryptDownload(source, sng_id, dest):
    interval_chunk = 3
    chunk_size = 2048
    blowFishKey = __getBlowFishKey(sng_id)
    i = 0
    iv = "\x00\x01\x02\x03\x04\x05\x06\x07"

    dest_folder = os.path.dirname(dest)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    f = open(source, "rb")
    fout = open(dest, "wb")
    try:
        chunk = f.read(chunk_size)
        while chunk:
            if(i % interval_chunk == 0):
                cipher = Blowfish.new(blowFishKey, Blowfish.MODE_CBC, iv)
                chunk = cipher.decrypt(__pad(chunk, Blowfish.block_size))

            fout.write(chunk)
            i += 1
            chunk = f.read(chunk_size)
    finally:
        f.close()
        fout.close()


def __getBlowFishKey(encryptionKey):
    if encryptionKey < 1:
        encryptionKey *= -1

    hashcode = md5(str(encryptionKey)).hexdigest()
    hPart = hashcode[0:16]
    lPart = hashcode[16:32]
    parts = ['g4el58wc0zvf9na1', hPart, lPart]

    return __xorHex(parts)


def __xorHex(parts):
    data = ""
    for i in range(0, 16):
        character = ord(parts[0][i])

        for j in range(1, len(parts)):
            character ^= ord(parts[j][i])

        data += chr(character)

    return data
