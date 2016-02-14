#import unittest
#import mock
from unittestcompat import TestCase

import headphones.albumart

# no tests...
class AlbumArtTest(TestCase):
    def test_nothing(self):
        x = 100 - 2 * 50
        if x:
            headphones.albumart.getAlbumArt('asdf')
        self.assertTrue(True)
