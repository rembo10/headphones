from unittest import TestCase
from fanart.core import Request
from fanart.errors import RequestFanartError, ResponseFanartError
from httpretty import httprettified, HTTPretty


class RequestTestCase(TestCase):
    def test_valitate_error(self):
        self.assertRaises(RequestFanartError, Request, 'key', 'id', 'sport')

    @httprettified
    def test_response_error(self):
        request = Request('apikey', 'objid', 'tv')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://webservice.fanart.tv/v3/tv/objid?api_key=apikey',
            body='Please specify a valid API key',
        )
        try:
            request.response()
        except ResponseFanartError as e:
            self.assertEqual(repr(e), "ResponseFanartError('Expecting value: "
                                      "line 1 column 1 (char 0)',)")
            self.assertEqual(str(e), "Expecting value: "
                                     "line 1 column 1 (char 0)")
