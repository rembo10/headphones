from headphones.unittestcompat import TestCase

import headphones.albumart


class AlbumArtTest(TestCase):
    def test_nothing(self):
        x = 100 - 2 * 50
        if x:
            headphones.albumart.getAlbumArt('asdf')
        self.assertTrue(True)
