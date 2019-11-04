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
Test module for metadata.
"""
import headphones as _h
import headphones.metadata as _md
import headphones.helpers as _hp
from headphones.metadata import MetadataDict
import datetime

from unittestcompat import TestCase


__author__ = "Andrzej Ciarkowski <andrzej.ciarkowski@gmail.com>"


class _MockMediaFile(object):

    def __init__(self, artist, album, year, track, title, label):
        self.artist = artist
        self.album = album
        self.year = year
        self.track = track
        self.title = title
        self.label = label
        self.art = 'THIS IS ART BLOB'

    @classmethod
    def readable_fields(cls):
        return 'artist', 'album', 'year', 'track', 'title', 'label', 'art'


class _MockDatabaseRow(object):

    def __init__(self, d):
        self._dict = dict(d)

    def keys(self):
        return self._dict.iterkeys()

    def __getitem__(self, item):
        return self._dict[item]


class MetadataTest(TestCase):
    """
    Tests for metadata module.
    """

    def test_metadata_dict_ci(self):
        """MetadataDict: case-insensitive lookup"""
        expected = u'naïve'
        key_var = '$TitlE'
        m = MetadataDict({key_var.lower(): u'naïve'})
        self.assertFalse('$track' in m)
        self.assertTrue('$tITLe' in m, "cross-case lookup with 'in'")
        self.assertEqual(m[key_var], expected, "cross-case lookup success")
        self.assertEqual(m[key_var.lower()], expected, "same-case lookup "
                                                       "succes")

    def test_metadata_dict_cs(self):
        """MetadataDice: case-preserving lookup"""
        expected_var = u'NaïVe'
        key_var = '$TitlE'
        m = MetadataDict({
            key_var.lower(): expected_var.lower(),
            key_var: expected_var
        })
        self.assertFalse('$track' in m)
        self.assertTrue('$tITLe' in m, "cross-case lookup with 'in'")
        self.assertEqual(m[key_var.lower()], expected_var.lower(),
                         "case-preserving lookup lower")
        self.assertEqual(m[key_var], expected_var,
                         "case-preserving lookup variable")

    def test_dict_intersect(self):
        """metadata: check dictionary intersect function validity"""
        d1 = {
            'one': 'one',
            'two': 'two',
            'three': 'zonk'
        }
        d2 = {
            'two': 'two',
            'three': 'three'
        }
        expected = {
            'two': 'two'
        }
        self.assertItemsEqual(
            expected, _md._intersect(d1, d2), "check dictionary intersection "
                                              "is common part indeed"
        )
        del d1['two']
        expected = {}
        self.assertItemsEqual(
            expected, _md._intersect(d1, d2), "check intersection empty"
        )

    def test_album_metadata_builder(self):
        """AlbumMetadataBuilder: check validity"""
        mb = _md.AlbumMetadataBuilder()
        f1 = _MockMediaFile('artist', 'album', 2000, 1, 'track1', 'Ant-Zen')
        mb.add_media_file(f1)
        f2 = _MockMediaFile('artist', 'album', 2000, 2, 'track2', 'Ant-Zen')
        mb.add_media_file(f2)

        md = mb.build()
        expected = {
            _md.Vars.ARTIST_LOWER: 'artist',
            _md.Vars.ALBUM_LOWER: 'album',
            _md.Vars.YEAR.lower(): 2000,
            '$label': 'Ant-Zen'
        }
        self.assertItemsEqual(
            expected, md, "check AlbumMetadataBuilder validity"
        )

    def test_populate_from_row(self):
        """metadata: check populating metadata from database row"""
        row = _MockDatabaseRow({
            'ArtistName': 'artist',
            'AlbumTitle': 'album',
            'ReleaseDate': datetime.date(2004, 11, 28),
            'Variation': 5,
            'WrongTyped': complex(1, -1)
        })
        md = _md.MetadataDict()
        _md._row_to_dict(row, md)
        expected = {
            '$ArtistName': 'artist',
            '$AlbumTitle': 'album',
            '$ReleaseDate': '2004-11-28',
            '$Variation': '5'
        }
        self.assertItemsEqual(expected, md, "check _row_to_dict() valid")

    def test_album_metadata_with_None(self):
        """metadata: check handling of None metadata values"""
        row = _MockDatabaseRow({
            'ArtistName': 'artist',
            'AlbumTitle': 'Album',
            'Type': None,
            'ReleaseDate': None,
        })
        mb = _md.AlbumMetadataBuilder()
        f1 = _MockMediaFile('artist', None, None, None, None, None)
        mb.add_media_file(f1)
        f2 = _MockMediaFile('artist', None, None, 2, 'track2', None)
        mb.add_media_file(f2)
        md = _md.album_metadata("/music/Artist - Album [2002]", row, mb.build())

        # tests don't undergo normal Headphones init, SYS_ENCODING is not set
        if not _h.SYS_ENCODING:
            _h.SYS_ENCODING = 'UTF-8'

        res = _hp.pattern_substitute(
            "/music/$First/$Artist/$Artist - $Album{ [$Year]}", md, True)

        self.assertEqual(res, u"/music/A/artist/artist - Album",
                         "check correct rendering of None via pattern_substitute()")
