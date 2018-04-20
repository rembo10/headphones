# encoding=utf8
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
"""
Track/album metadata handling routines.
"""

from __future__ import print_function
from beets.mediafile import MediaFile, UnreadableFileError
import headphones
from headphones import logger
import os.path
import datetime

__author__ = "Andrzej Ciarkowski <andrzej.ciarkowski@gmail.com>"


class MetadataDict(dict):
    """
    Dictionary which allows for case-insensitive, but case-preserving lookup,
    allowing to put different values under $Album and $album, but still
    finding some value if only single key is present and called with any
    variation of the name's case.

    Keeps case-sensitive mapping in superclass dict, and case-insensitive (
    lowercase) in member variable self._lower. If case-sensitive lookup
    fails, another case-insensitive attempt is made.
    """
    def __setitem__(self, key, value):
        super(MetadataDict, self).__setitem__(key, value)
        self._lower.__setitem__(key.lower(), value)

    def add_items(self, items):
        # type: (Iterable[Tuple[Any,Any]])->None
        """
        Add (key,value) pairs to this dictionary using iterable as an input.
        :param items: input items.
        """
        for key, value in items:
            self.__setitem__(key, value)

    def __init__(self, seq=None, **kwargs):
        if isinstance(seq, MetadataDict):
            super(MetadataDict, self).__init__(seq)
            self._lower = dict(seq._lower)
        else:
            super(MetadataDict, self).__init__()
            self._lower = {}
            if seq is not None:
                try:
                    self.add_items(seq.iteritems())
                except KeyError:
                    self.add_items(seq)

    def __getitem__(self, item):
        try:
            return super(MetadataDict, self).__getitem__(item)
        except KeyError:
            return self._lower.__getitem__(item.lower())

    def __contains__(self, item):
        return self._lower.__contains__(item.lower())


class Vars:
    """
    Metadata $variable names (only ones set explicitly by headphones).
    """
    DISC = '$Disc'
    TRACK = '$Track'
    TITLE = '$Title'
    ARTIST = '$Artist'
    SORT_ARTIST = '$SortArtist'
    ALBUM = '$Album'
    YEAR = '$Year'
    DATE = '$Date'
    EXTENSION = '$Extension'
    ORIGINAL_FOLDER = '$OriginalFolder'
    FIRST_LETTER = '$First'
    TYPE = '$Type'
    TITLE_LOWER = TITLE.lower()
    ARTIST_LOWER = ARTIST.lower()
    SORT_ARTIST_LOWER = SORT_ARTIST.lower()
    ALBUM_LOWER = ALBUM.lower()
    ORIGINAL_FOLDER_LOWER = ORIGINAL_FOLDER.lower()
    FIRST_LETTER_LOWER = FIRST_LETTER.lower()
    TYPE_LOWER = TYPE.lower()


def _verify_var_type(val):
    """
    Check if type of value is allowed as a variable in pathname substitution.
    """
    return isinstance(val, (basestring, int, float, datetime.date))


def _as_str(val):
    if isinstance(val, basestring):
        return val
    else:
        return str(val)


def _media_file_to_dict(mf, d):
    # type: (MediaFile, MutableMapping[basestring,basestring])->None
    """
    Populate dict with tags read from media file.
    """
    for fld in mf.readable_fields():
        if 'art' == fld:
            # skip embedded artwork as it's a BLOB
            continue
        val = getattr(mf, fld)
        if val is None:
            val = ''
        # include only types with meaningful string representation
        if _verify_var_type(val):
            d['$' + fld] = _as_str(val)


def _row_to_dict(row, d):
    """
    Populate dict with database row fields.
    """
    for fld in row.keys():
        val = row[fld]
        if val is None:
            val = ''
        if _verify_var_type(val):
            d['$' + fld] = _as_str(val)


def _date_year(release):
    # type: (sqlite3.Row)->Tuple[str,str]
    """
    Extract release date and year from database row
    """
    try:
        date = release['ReleaseDate']
    except TypeError:
        date = ''

    if date is not None:
        year = date[:4]
    else:
        year = ''
    return date, year


def _lower(s):
    # type: basestring->basestring
    """
    Return s.lower() if not None
    :param s:
    :return:
    """
    if s:
        return s.lower()
    return None


def file_metadata(path, release):
    # type: (str,sqlite3.Row)->Tuple[Mapping[str,str],bool]
    """
    Prepare metadata dictionary for path substitution, based on file name,
    the tags stored within it and release info from the db.
    :param path: media file path
    :param release: database row with release info
    :return: pair (dict,boolean indicating if Vars.TITLE is taken from tags or
    file name). (None,None) if unable to parse the media file.
    """
    try:
        f = MediaFile(path)
    except UnreadableFileError as ex:
        logger.info("MediaFile couldn't parse: %s (%s)",
                    path.decode(headphones.SYS_ENCODING, 'replace'),
                    str(ex))
        return None, None

    res = MetadataDict()
    # add existing tags first, these will get overwritten by musicbrainz from db
    _media_file_to_dict(f, res)
    # raw database fields come next
    _row_to_dict(release, res)

    date, year = _date_year(release)
    if not f.disc:
        disc_number = ''
    else:
        disc_number = '%d' % f.disc

    if not f.track:
        track_number = ''
    else:
        track_number = '%02d' % f.track

    if not f.title:
        basename = os.path.basename(
            path.decode(headphones.SYS_ENCODING, 'replace'))
        title = os.path.splitext(basename)[0]
        from_metadata = False
    else:
        title = f.title
        from_metadata = True

    ext = os.path.splitext(path)[1]
    if release['ArtistName'] == "Various Artists" and f.artist:
        artist_name = f.artist
    else:
        artist_name = release['ArtistName']

    if artist_name and artist_name.startswith('The '):
        sort_name = artist_name[4:] + ", The"
    else:
        sort_name = artist_name

    album_title = release['AlbumTitle']
    override_values = {
        Vars.DISC: disc_number,
        Vars.TRACK: track_number,
        Vars.TITLE: title,
        Vars.ARTIST: artist_name,
        Vars.SORT_ARTIST: sort_name,
        Vars.ALBUM: album_title,
        Vars.YEAR: year,
        Vars.DATE: date,
        Vars.EXTENSION: ext,
        Vars.TITLE_LOWER: _lower(title),
        Vars.ARTIST_LOWER: _lower(artist_name),
        Vars.SORT_ARTIST_LOWER: _lower(sort_name),
        Vars.ALBUM_LOWER: _lower(album_title),
    }
    res.add_items(override_values.iteritems())
    return res, from_metadata


def _intersect(d1, d2):
    # type: (Mapping,Mapping)->Mapping
    """
    Create intersection (common part) of two dictionaries.
    """
    res = {}
    for key, val in d1.iteritems():
        if key in d2 and d2[key] == val:
            res[key] = val
    return res


def album_metadata(path, release, common_tags):
    # type: (str,sqlite3.Row,Mapping[str,str])->Mapping[str,str]
    """
    Prepare metadata dictionary for path substitution of album folder.
    :param path: album path to prepare metadata for.
    :param release: database row with release properties.
    :param common_tags: common set of tags gathered from media files.
    :return: metadata dictionary with substitution variables for rendering path.
    """
    date, year = _date_year(release)
    artist = release['ArtistName']
    if artist:
        artist = artist.replace('/', '_')
    album = release['AlbumTitle']
    if album:
        album = album.replace('/', '_')
    release_type = release['Type']
    if release_type:
        release_type = release_type.replace('/', '_')

    if artist and artist.startswith('The '):
        sort_name = artist[4:] + ", The"
    else:
        sort_name = artist

    if not sort_name or sort_name[0].isdigit():
        first_char = u'0-9'
    else:
        first_char = sort_name[0]

    orig_folder = u''

    # Get from temp path
    if "_@hp@_" in path:
        orig_folder = path.rsplit("headphones_", 1)[1].split("_@hp@_")[0]
        orig_folder = orig_folder.decode(headphones.SYS_ENCODING, 'replace')
    else:
        for r, d, f in os.walk(path):
            try:
                orig_folder = os.path.basename(
                    os.path.normpath(r).decode(headphones.SYS_ENCODING, 'replace'))
                break
            except:
                pass

    override_values = {
        Vars.ARTIST: artist,
        Vars.SORT_ARTIST: sort_name,
        Vars.ALBUM: album,
        Vars.YEAR: year,
        Vars.DATE: date,
        Vars.TYPE: release_type,
        Vars.ORIGINAL_FOLDER: orig_folder,
        Vars.FIRST_LETTER: first_char.upper(),
        Vars.ARTIST_LOWER: _lower(artist),
        Vars.SORT_ARTIST_LOWER: _lower(sort_name),
        Vars.ALBUM_LOWER: _lower(album),
        Vars.TYPE_LOWER: _lower(release_type),
        Vars.FIRST_LETTER_LOWER: _lower(first_char),
        Vars.ORIGINAL_FOLDER_LOWER: _lower(orig_folder)
    }
    res = MetadataDict(common_tags)
    res.add_items(override_values.iteritems())
    return res


def albumart_metadata(release, common_tags):
    # type: (sqlite3.Row,Mapping)->Mapping
    """
    Prepare metadata dictionary for path subtitution of album art file.
    :param release: database row with release properties.
    :param common_tags: common set of tags gathered from media files.
    :return: metadata dictionary with substitution variables for rendering path.
    """
    date, year = _date_year(release)
    artist = release['ArtistName']
    album = release['AlbumTitle']

    override_values = {
        Vars.ARTIST: artist,
        Vars.ALBUM: album,
        Vars.YEAR: year,
        Vars.DATE: date,
        Vars.ARTIST_LOWER: _lower(artist),
        Vars.ALBUM_LOWER: _lower(album)
    }
    res = MetadataDict(common_tags)
    res.add_items(override_values.iteritems())
    return res


class AlbumMetadataBuilder(object):
    """
    Facilitates building of album metadata as a common set of tags retrieved
    from media files.
    """

    def __init__(self):
        self._common = None

    def add_media_file(self, mf):
        # type: (Mapping)->None
        """
        Add metadata tags read from media file to album metadata.
        :param mf: MediaFile
        """
        md = {}
        _media_file_to_dict(mf, md)
        if self._common is None:
            self._common = md
        else:
            self._common = _intersect(self._common, md)

    def build(self):
        # type: (None)->Mapping
        """
        Build case-insensitive, case-preserving dict from gathered metadata
        tags.
        :return: dictinary-like object filled with $variables based on common
        tags.
        """
        return MetadataDict(self._common)
