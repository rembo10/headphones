import json
from fanart.errors import ResponseFanartError
import os
import unittest
from httpretty import HTTPretty, httprettified
from fanart.tv import *
from fanart.tests import LOCALDIR
os.environ['FANART_APIKEY'] = 'e3c7f0d0beeaf45b3a0dd3b9dd8a3338'


class TvItemTestCase(unittest.TestCase):
    @httprettified
    def test_get_wilfred(self):
        with open(os.path.join(LOCALDIR, 'response/tv_239761.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://webservice.fanart.tv/v3/tv/239761?api_key={}'.format(
                os.environ['FANART_APIKEY']),
            body=body
        )
        wilfred = TvShow.get(id=239761)

        # If we update `response/tv_239761.json`, then we also must update
        # `json/wilfred.json`, and to do so, we can use the following command:
        # print(wilfred.json(indent=4))

        self.assertEqual(wilfred.tvdbid, '239761')
        with open(os.path.join(LOCALDIR, 'json/wilfred.json')) as fp:
            self.assertEqual(json.loads(wilfred.json()), json.load(fp))

    @httprettified
    def test_get_dexter(self):
        with open(os.path.join(LOCALDIR, 'response/tv_79349.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://webservice.fanart.tv/v3/tv/79349?api_key={}'.format(
                os.environ['FANART_APIKEY']),
            body=body
        )
        dexter = TvShow.get(id=79349)
        self.assertEqual(dexter.tvdbid, '79349')
        self.assertEqual(dexter, eval(repr(dexter)))

    @httprettified
    def test_get_null(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://webservice.fanart.tv/v3/tv/79349?api_key={}'.format(
                os.environ['FANART_APIKEY']),
            body='null'
        )
        self.assertRaises(ResponseFanartError, TvShow.get, id=79349)
