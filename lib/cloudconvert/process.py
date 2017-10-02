import os
import shutil
import time

from .exceptions import (
    APIError, HTTPError, BadRequest, ConversionFailed, TemporaryUnavailable, InvalidResponse, InvalidParameterException
)


class Process(object):
    """
    Process Object wrapper CloudConvert API
    """

    data = {}

    def __init__(self, api, url=None):
        """
        Creates a new Process instance

        :param Api api: API Instance
        :param str url: The Process URL
        """

        self.api = api
        self.url = url



    def refresh(self, parameters = None):
        """
        Refresh process data from API

        :param parameters: Parameters for creating the Process. See https://cloudconvert.com/apidoc#start
        :raises APIError: if the CloudConvert API returns an error
        """

        self.data = self.api.get(self.url, parameters)
        return self


    def start(self, parameters):
        """
        Starts the Process

        :param parameters: Parameters for creating the Process. See https://cloudconvert.com/apidoc#start
        :raises APIError: if the CloudConvert API returns an error
        """

        self.data = self.api.post(self.url, parameters)
        return self


    def delete(self):
        """
        Delete process from API
        :raises APIError: if the CloudConvert API returns an error
        """
        self.api.delete(self.url)
        return self



    def wait(self, interval = 1):
        """
        Waits for the Process to finish (or end with an error). Checks the conversion status every interval seconds.
        :param int interval: Interval in seconds
        :raises APIError: if the CloudConvert API returns an error
        """
        while self['step']!='finished' and self['step'] !='error':
            self.refresh()
            time.sleep(interval)

        return self



    def download(self, localfile = None, remotefile = None):
        """
        Download process file from API
        :param str localfile: Local file name (or directory) the file should be downloaded to
        :param str remotefile: Remote file name which should be downloaded (if there are multiple output files available)
        :raises APIError: if the CloudConvert API returns an error
        """
        if localfile is not None and os.path.isdir(localfile) and 'filename' in self.data.get('output', {}):
            ## localfile is directory
            localfile =  os.path.normpath(localfile) + os.sep + (remotefile if remotefile is not None else self['output']['filename'])
        elif localfile is None and 'filename' in self.data.get('output', {}):
            ## localfile is not set -> set it to output filename
            localfile = remotefile if remotefile is not None else self['output']['filename']

        if localfile is None or os.path.isdir(localfile):
            raise InvalidParameterException("localfile parameter is not set correctly")

        if 'url' not in self.data.get('output', {}):
            raise APIError("There is no output file available (yet)")

        r = self.api.rawCall("GET", self['output']['url'] + ("/" + remotefile if remotefile else ""), stream=True)

        with open(localfile, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)


        return self


    def downloadAll(self, directory = None):
        """
        Download all output process files from API
        :param str directory:  Local directory the files should be downloaded to
        :raises APIError: if the CloudConvert API returns an error
        """
        if 'files' not in self.data.get('output', {}):
            ## there are not multiple output files -> do normal download
            return self.download(localfile=directory)

        for file in self["output"]["files"]:
            self.download(localfile=directory, remotefile=file)

        return self



    def __getitem__(self, item):
        """
        Make process status from API available as object attributes.
        Examples:
            process['step']
            process['message']

        """
        if self.data.get(item):
            return self.data.get(item)
        else:
            # Default behaviour
            raise AttributeError