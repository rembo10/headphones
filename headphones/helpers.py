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

import os, time
from operator import itemgetter
import datetime
import re, shutil

from beets.mediafile import MediaFile, FileTypeError, UnreadableFileError

import headphones

# Modified from https://github.com/Verrus/beets-plugin-featInTitle
RE_FEATURING = re.compile(r"[fF]t\.|[fF]eaturing|[fF]eat\.|\b[wW]ith\b|&|vs\.")

RE_CD_ALBUM = re.compile(r"\(?((CD|disc)\s*[0-9]+)\)", re.I)
RE_CD = re.compile(r"^(CD|dics)\s*[0-9]+$", re.I)

def multikeysort(items, columns):

    comparers = [ ((itemgetter(col[1:].strip()), -1) if col.startswith('-') else (itemgetter(col.strip()), 1)) for col in columns]
    
    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp(fn(left), fn(right))
            if result:
                return mult * result
        else:
            return 0
    
    return sorted(items, cmp=comparer)
    
def checked(variable):
    if variable:
        return 'Checked'
    else:
        return ''
        
def radio(variable, pos):

    if variable == pos:
        return 'Checked'
    else:
        return ''
        
def latinToAscii(unicrap):
    """
    From couch potato
    """
    xlate = {0xc0:'A', 0xc1:'A', 0xc2:'A', 0xc3:'A', 0xc4:'A', 0xc5:'A',
        0xc6:'Ae', 0xc7:'C',
        0xc8:'E', 0xc9:'E', 0xca:'E', 0xcb:'E', 0x86:'e',
        0xcc:'I', 0xcd:'I', 0xce:'I', 0xcf:'I',
        0xd0:'Th', 0xd1:'N',
        0xd2:'O', 0xd3:'O', 0xd4:'O', 0xd5:'O', 0xd6:'O', 0xd8:'O',
        0xd9:'U', 0xda:'U', 0xdb:'U', 0xdc:'U',
        0xdd:'Y', 0xde:'th', 0xdf:'ss',
        0xe0:'a', 0xe1:'a', 0xe2:'a', 0xe3:'a', 0xe4:'a', 0xe5:'a',
        0xe6:'ae', 0xe7:'c',
        0xe8:'e', 0xe9:'e', 0xea:'e', 0xeb:'e', 0x0259:'e',
        0xec:'i', 0xed:'i', 0xee:'i', 0xef:'i',
        0xf0:'th', 0xf1:'n',
        0xf2:'o', 0xf3:'o', 0xf4:'o', 0xf5:'o', 0xf6:'o', 0xf8:'o',
        0xf9:'u', 0xfa:'u', 0xfb:'u', 0xfc:'u',
        0xfd:'y', 0xfe:'th', 0xff:'y',
        0xa1:'!', 0xa2:'{cent}', 0xa3:'{pound}', 0xa4:'{currency}',
        0xa5:'{yen}', 0xa6:'|', 0xa7:'{section}', 0xa8:'{umlaut}',
        0xa9:'{C}', 0xaa:'{^a}', 0xab:'<<', 0xac:'{not}',
        0xad:'-', 0xae:'{R}', 0xaf:'_', 0xb0:'{degrees}',
        0xb1:'{+/-}', 0xb2:'{^2}', 0xb3:'{^3}', 0xb4:"'",
        0xb5:'{micro}', 0xb6:'{paragraph}', 0xb7:'*', 0xb8:'{cedilla}',
        0xb9:'{^1}', 0xba:'{^o}', 0xbb:'>>',
        0xbc:'{1/4}', 0xbd:'{1/2}', 0xbe:'{3/4}', 0xbf:'?',
        0xd7:'*', 0xf7:'/'
        }

    r = ''
    for i in unicrap:
        if xlate.has_key(ord(i)):
            r += xlate[ord(i)]
        elif ord(i) >= 0x80:
            pass
        else:
            r += str(i)
    return r
    
def convert_milliseconds(ms):

    seconds = ms/1000
    gmtime = time.gmtime(seconds)
    if seconds > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes
    
def convert_seconds(s):

    gmtime = time.gmtime(s)
    if s > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes
    
def today():
    today = datetime.date.today()
    yyyymmdd = datetime.date.isoformat(today)
    return yyyymmdd
    
def now():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")
    
def get_age(date):

    try:
        split_date = date.split('-')
    except:
        return False
    
    try:
        days_old = int(split_date[0])*365 + int(split_date[1])*30 + int(split_date[2])
    except IndexError:
        days_old = False
        
    return days_old
    
def bytes_to_mb(bytes):

    mb = int(bytes)/1048576
    size = '%.1f MB' % mb
    return size

def mb_to_bytes(mb_str):
    result = re.search('^(\d+(?:\.\d+)?)\s?(?:mb)?', mb_str, flags=re.I)
    if result:
        return int(float(result.group(1))*1048576)
        
def piratesize(size):
    split = size.split(" ")
    factor = float(split[0])
    unit = split[1]
    if unit == 'MiB':
        size = factor * 1048576
    elif unit == 'GiB':
        size = factor * 1073741824
    elif unit == 'KiB':
        size = factor * 1024
    elif unit == "B":
        size = factor
    else:
        size = 0
    
    return size

def replace_all(text, dic):
    
    if not text:
        return ''
        
    for i, j in dic.iteritems():
        text = text.replace(i, j)
    return text
    
def cleanName(string):

    pass1 = latinToAscii(string).lower()
    out_string = re.sub('[\.\-\/\!\@\#\$\%\^\&\*\(\)\+\-\"\'\,\;\:\[\]\{\}\<\>\=\_]', '', pass1).encode('utf-8')
    
    return out_string
    
def cleanTitle(title):

    title = re.sub('[\.\-\/\_]', ' ', title).lower()
    
    # Strip out extra whitespace
    title = ' '.join(title.split())
    
    title = title.title()
    
    return title
    
def extract_data(s):

    #headphones default format
    pattern = re.compile(r'(?P<name>.*?)\s\-\s(?P<album>.*?)\s\[(?P<year>.*?)\]', re.VERBOSE)
    match = pattern.match(s)
    
    if match:
        name = match.group("name")
        album = match.group("album")
        year = match.group("year")
        return (name, album, year)
    
    #newzbin default format
    pattern = re.compile(r'(?P<name>.*?)\s\-\s(?P<album>.*?)\s\((?P<year>\d+?\))', re.VERBOSE)
    match = pattern.match(s)
    if match:
        name = match.group("name")
        album = match.group("album")
        year = match.group("year")
        return (name, album, year)
    else:
        return (None, None, None)

def extract_metadata(f):
    """
    Scan all files in the given directory and decide on an artist, album and
    year based on the metadata. A decision is based on the number of different
    artists, albums and years found in the media files.
    """

    from headphones import logger

    # Walk directory and scan all media files
    results = []
    count = 0

    for root, dirs, files in os.walk(f):
        for file in files:
            # Count the number of potential media files
            extension = os.path.splitext(file)[1].lower()[1:]

            if extension in headphones.MEDIA_FORMATS:
                count += 1

            # Try to read the file info
            try:
                media_file = MediaFile(os.path.join(root, file))
            except FileTypeError, UnreadableFileError:
                # Probably not a media file
                continue

            # Append metadata to file
            artist = media_file.albumartist or media_file.artist
            album = media_file.album
            year = media_file.year

            if artist and album and year:
                results.append((artist.lower(), album.lower(), year))

    # Verify results
    if len(results) == 0:
        logger.info("No metadata in media files found, ignoring")
        return (None, None, None)

    # Require that some percentage of files have tags
    count_ratio = 0.75

    if count < (count_ratio * len(results)):
        logger.info("Counted %d media files, but only %d have tags, ignoring" % (count, len(results)))
        return (None, None, None)

    # Count distinct values
    artists = list(set([ x[0] for x in results ]))
    albums = list(set([ x[1] for x in results ]))
    years = list(set([ x[2] for x in results ]))

    # Remove things such as CD2 from album names
    if len(albums) > 1:
        new_albums = list(albums)

        # Replace occurences of e.g. CD1
        for index, album in enumerate(new_albums):
            if RE_CD_ALBUM.search(album):
                new_albums[index] = RE_CD_ALBUM.sub("", album).strip()

        # Remove duplicates
        new_albums = list(set(new_albums))

        # Safety check: if nothing has merged, then ignore the work. This can
        # happen if only one CD of a multi part CD is processed.
        if len(new_albums) < len(albums):
            albums = new_albums

    # All files have the same metadata, so it's trivial
    if len(artists) == 1 and len(albums) == 1 and len(years) == 1:
        return (artists[0], albums[0], years[0])

    # (Lots of) different artists. Could be a featuring album, so test for this.
    if len(artists) > 1 and len(albums) == 1 and len(years) == 1:
        split_artists = [ RE_FEATURING.split(artist) for artist in artists ]
        featurings = [ len(split_artist) - 1 for split_artist in split_artists ]
        logger.info("Album seem to feature %d different artists" % sum(featurings))

        if sum(featurings) > 0:
            # Find the artist of which the least splits have been generated.
            # Ideally, this should be 0, which should be the album artist
            # itself.
            artist = split_artists[featurings.index(min(featurings))][0]

            # Done
            return (artist, albums[0], years[0])

    # Not sure what to do here.
    logger.info("Found %d artists, %d albums and %d years in metadata, ignoring" % (len(artists), len(albums), len(years)))
    return (None, None, None)

def extract_logline(s):
    # Default log format
    pattern = re.compile(r'(?P<timestamp>.*?)\s\-\s(?P<level>.*?)\s*\:\:\s(?P<thread>.*?)\s\:\s(?P<message>.*)', re.VERBOSE)
    match = pattern.match(s)
    if match:
        timestamp = match.group("timestamp")
        level = match.group("level")
        thread = match.group("thread")
        message = match.group("message")
        return (timestamp, level, thread, message)
    else:
        return None
        
def extract_song_data(s):

    #headphones default format
    music_dir = headphones.MUSIC_DIR
    folder_format = headphones.FOLDER_FORMAT
    file_format = headphones.FILE_FORMAT
    
    full_format = os.path.join(headphones.MUSIC_DIR)
    pattern = re.compile(r'(?P<name>.*?)\s\-\s(?P<album>.*?)\s\[(?P<year>.*?)\]', re.VERBOSE)
    match = pattern.match(s)
    
    if match:
        name = match.group("name")
        album = match.group("album")
        year = match.group("year")
        return (name, album, year)
    else:
        logger.info("Couldn't parse " + s + " into a valid default format")
    
    #newzbin default format
    pattern = re.compile(r'(?P<name>.*?)\s\-\s(?P<album>.*?)\s\((?P<year>\d+?\))', re.VERBOSE)
    match = pattern.match(s)
    if match:
        name = match.group("name")
        album = match.group("album")
        year = match.group("year")
        return (name, album, year)
    else:
        logger.info("Couldn't parse " + s + " into a valid Newbin format")
        return (name, album, year)
        
def smartMove(src, dest, delete=True):
    
    from headphones import logger

    source_dir = os.path.dirname(src)
    filename = os.path.basename(src)
    
    if os.path.isfile(os.path.join(dest, filename)):
        logger.info('Destination file exists: %s' % os.path.join(dest, filename).decode(headphones.SYS_ENCODING, 'replace'))
        title = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1]
        i = 1
        while True:
            newfile = title + '(' + str(i) + ')' + ext
            if os.path.isfile(os.path.join(dest, newfile)):
                i += 1
            else:
                logger.info('Renaming to %s' % newfile)
                try:    
                    os.rename(src, os.path.join(source_dir, newfile))
                    filename = newfile
                except Exception, e:
                    logger.warn('Error renaming %s: %s' % (src.decode(headphones.SYS_ENCODING, 'replace'), str(e).decode(headphones.SYS_ENCODING, 'replace')))
                break

    try:
        if delete:
            shutil.move(os.path.join(source_dir, filename), os.path.join(dest, filename))
        else:
            shutil.copy(os.path.join(source_dir, filename), os.path.join(dest, filename))
            return True
    except Exception, e:
        logger.warn('Error moving file %s: %s' % (filename.decode(headphones.SYS_ENCODING, 'replace'), str(e).decode(headphones.SYS_ENCODING, 'replace')))

#########################
#Sab renaming functions #
#########################

# TODO: Grab config values from sab to know when these options are checked. For now we'll just iterate through all combinations

def sab_replace_dots(name):
    return name.replace('.',' ')
def sab_replace_spaces(name):
    return name.replace(' ','_')

def sab_sanitize_foldername(name):
    """ Return foldername with dodgy chars converted to safe ones
        Remove any leading and trailing dot and space characters
    """
    CH_ILLEGAL = r'\/<>?*|"'
    CH_LEGAL   = r'++{}!@#`'
    
    FL_ILLEGAL = CH_ILLEGAL + ':\x92"'
    FL_LEGAL   = CH_LEGAL +   "-''"
    
    uFL_ILLEGAL = FL_ILLEGAL.decode('latin-1')
    uFL_LEGAL   = FL_LEGAL.decode('latin-1')
    
    if not name:
        return name
    if isinstance(name, unicode):
        illegal = uFL_ILLEGAL
        legal   = uFL_LEGAL
    else:
        illegal = FL_ILLEGAL
        legal   = FL_LEGAL

    lst = []
    for ch in name.strip():
        if ch in illegal:
            ch = legal[illegal.find(ch)]
            lst.append(ch)
        else:
            lst.append(ch)
    name = ''.join(lst)

    name = name.strip('. ')
    if not name:
        name = 'unknown'

    #maxlen = cfg.folder_max_length()
    #if len(name) > maxlen:
    #    name = name[:maxlen]

    return name

def split_string(mystring):
    mylist = []
    for each_word in mystring.split(','):
        mylist.append(each_word.strip())
    return mylist

def create_https_certificates(ssl_cert, ssl_key):
    """
    Stolen from SickBeard (http://github.com/midgetspy/Sick-Beard):
    Create self-signed HTTPS certificares and store in paths 'ssl_cert' and 'ssl_key'
    """
    from headphones import logger
    
    try:
        from OpenSSL import crypto #@UnresolvedImport
        from lib.certgen import createKeyPair, createCertRequest, createCertificate, TYPE_RSA, serial #@UnresolvedImport
    except:
        logger.warn(u"pyopenssl module missing, please install for https access")
        return False

    # Create the CA Certificate
    cakey = createKeyPair(TYPE_RSA, 1024)
    careq = createCertRequest(cakey, CN='Certificate Authority')
    cacert = createCertificate(careq, (careq, cakey), serial, (0, 60*60*24*365*10)) # ten years

    cname = 'Headphones'
    pkey = createKeyPair(TYPE_RSA, 1024)
    req = createCertRequest(pkey, CN=cname)
    cert = createCertificate(req, (cacert, cakey), serial, (0, 60*60*24*365*10)) # ten years

    # Save the key and certificate to disk
    try:
        open(ssl_key, 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        open(ssl_cert, 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    except:
        logger.error(u"Error creating SSL key and certificate")
        return False

    return True
