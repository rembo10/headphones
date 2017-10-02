import json

try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote


import io

from requests import request, Session
from requests.exceptions import RequestException
from .urlencoder import urlencode

from .process import Process
from .exceptions import (
    APIError, HTTPError, BadRequest, ConversionFailed, TemporaryUnavailable, InvalidResponse, InvalidParameterException
)

class Api(object):
    """
    Base CloudConvert API Wrapper for Python
    """

    endpoint = "api.cloudconvert.com"
    protocol = "https"

    def __init__(self, api_key=None):
        """
        Creates a new API Client. No credential check is done at this point.

        :param str api_key: API key as provided by CloudConvert (https://cloudconvert.com/user/profile)
        """

        self._api_key = api_key

        # use a requests session to reuse HTTPS connections between requests
        self._session = Session()




    def get(self, path, parameters=None, is_authenticated=False):
        """
        'GET' :py:func:`Client.call` wrapper.
        Query string parameters can be set either directly in ``_target`` or as
        keywork arguments.
        :param string path: API method to call
        :param string is_authenticated: If True, send authentication headers. This is
            the default
        """
        if parameters:
            query_string = urlencode(parameters)
            if '?' in path:
                path = '%s&%s' % (path, query_string)
            else:
                path = '%s?%s' % (path, query_string)
        return self.rawCall('GET', path, None, is_authenticated)



    def post(self, path, parameters=None, is_authenticated=False):
        """
        'POST' :py:func:`Client.call` wrapper
        Body parameters can be set either directly in ``_target`` or as keywork
        arguments.
        :param string path: API method to call
        :param string is_authenticated: If True, send authentication headers. This is
            the default
        """
        return self.rawCall('POST', path, parameters, is_authenticated)



    def delete(self, path, is_authenticated=False):
        """
        'DELETE' :py:func:`Client.call` wrapper
        :param string path: API method to call
        :param string is_authenticated: If True, send authentication headers. This is
            the default
        """
        return self.rawCall('DELETE', path, None, is_authenticated)



    def rawCall(self, method, path, content=None, is_authenticated=False, stream=False):
        """
        Low level call helper for making HTTP requests.
        :param str method: HTTP method of request (GET,POST,PUT,DELETE)
        :param str path: relative url of API request
        :param content: body of the request (query parameters for GET requests or body for POST requests)
        :param boolean is_authenticated: if the request use authentication
        :raises HTTPError: when underlying request failed for network reason
        :raises InvalidResponse: when API response could not be decoded
        """

        url = path
        if path.startswith("//"):
            url = self.protocol + ":" + path
        elif not path.startswith("http"):
            url = self.protocol + "://" + self.endpoint + path


        body = None
        files = None
        headers = {}

        # include payload
        if content is not None:

            ## check if we upload anything
            isupload = False

            try:
               fileInstance=file # python 2
            except NameError:
               fileInstance=io.BufferedReader # python 3

            for key, value in content.items():
                if key == 'file':
                    x= ""
                if isinstance(value, fileInstance):
                    ## if it is file: remove from content dict and add it to files dict
                    isupload = True
                    files = {key: value}
                    del content[key]
                    break

            if isupload:
                url += "?" + unquote(urlencode(content))
            else:
                headers['Content-type'] = 'application/json'
                body = json.dumps(content)


        # add auth header
        if is_authenticated and self._api_key is not None:
            headers['Authorization'] = 'Bearer '  + self._api_key

        # attempt request
        try:
            result = self._session.request(method, url, headers=headers,
                                           data=body, files=files, stream=stream)
        except RequestException as error:
            raise HTTPError("HTTP request failed error", error)

        code = result.status_code

        # error check
        if code >= 100 and code < 300:
            if stream:
                return result

            try:
                return result.json()
            except ValueError as error:
                raise InvalidResponse("Failed to decode API response", error)
        else:
            json_result = result.json()
            msg = json_result.get('message') if json_result.get('message') else json_result.get('error')
            if code == 400:
                raise BadRequest(msg)
            elif code == 422:
                raise ConversionFailed(msg)
            elif code == 503:
                raise TemporaryUnavailable(msg)
            else:
                raise APIError(msg)

    def createProcess(self, parameters):
        """
        Create a new Process
        :param parameters: Parameters for creating the Process. See https://cloudconvert.com/apidoc#create
        :raises APIError: if the CloudConvert API returns an error
        """
        result = self.post("/process", parameters, True)
        return Process(self, result['url'])


    def convert(self, parameters):
        """
        Shortcut: Create a new Process and starts it
        :param parameters: Parameters for starting the Process. See https://cloudconvert.com/apidoc#start
        :raises APIError: if the CloudConvert API returns an error
        """

        startparameters=parameters.copy()
        ## we don't need the input file for creating the process
        del startparameters['file']
        process = self.createProcess(startparameters)
        return process.start(parameters)
