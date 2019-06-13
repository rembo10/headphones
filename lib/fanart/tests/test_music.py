import os
import unittest
from httpretty import HTTPretty, httprettified
from fanart.music import *
from fanart.tests import LOCALDIR
os.environ['FANART_APIKEY'] = 'e3c7f0d0beeaf45b3a0dd3b9dd8a3338'


class ArtistItemTestCase(unittest.TestCase):
    @httprettified
    def test_get(self):
        artist_id = '24e1b53c-3085-4581-8472-0b0088d2508c'
        with open(os.path.join(LOCALDIR, 'response/music_a7f.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://webservice.fanart.tv/v3/music/{}?api_key={}'.format(
                artist_id, os.environ['FANART_APIKEY']),
            body=body
        )
        a7f = Artist.get(id=artist_id)
        self.assertEqual(a7f.mbid, artist_id)
        self.assertEqual(a7f, eval(repr(a7f)))
        self.assertEqual(len(a7f.thumbs), 4)
