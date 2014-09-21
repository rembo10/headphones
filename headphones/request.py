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

from headphones import logger

from xml.dom import minidom
from bs4 import BeautifulSoup

import time
import requests
import feedparser
import headphones
import collections

# Dictionary with last request times, for rate limiting.
last_requests = collections.defaultdict(int)

def request_response(url, method="get", auto_raise=True,
    whitelist_status_code=None, rate_limit=None, **kwargs):
    """
    Convenient wrapper for `requests.get', which will capture the exceptions and
    log them. On success, the Response object is returned. In case of a
    exception, None is returned.

    Additionally, there is support for rate limiting. To use this feature,
    supply a tuple of (lock, request_limit). The lock is used to make sure no
    other request with the same lock is executed. The request limit is the
    minimal time between two requests (and so 1/request_limit is the number of
    requests per seconds).
    """

    # Convert whitelist_status_code to a list if needed
    if whitelist_status_code and type(whitelist_status_code) != list:
        whitelist_status_code = [whitelist_status_code]

    # Disable verification of SSL certificates if requested. Note: this could
    # pose a security issue!
    kwargs["verify"] = headphones.VERIFY_SSL_CERT

    # Map method to the request.XXX method. This is a simple hack, but it allows
    # requests to apply more magic per method. See lib/requests/api.py.
    request_method = getattr(requests, method.lower())

    # Enfore request rate limit if applicable. This uses the lock so there
    # is synchronized access to the API. When N threads enter this method, the
    # first will pass trough, since there there was no last request recorded.
    # The last request time will be set. Then, the second thread will unlock,
    # and see that the last request was X seconds ago. It will sleep
    # (request_limit - X) seconds, and then continue. Then the third one will
    # unblock, and so on. After all threads finished, the total time will at
    # least be (N * request_limit) seconds. If some request takes longer than
    # request_limit seconds, the next unblocked thread will wait less.
    if rate_limit:
        lock, request_limit = rate_limit

        with lock:
            delta = time.time() - last_requests[lock]
            limit = int(1.0 / request_limit)

            if delta < request_limit:
                logger.debug("Sleeping %.2f seconds for request, limit " \
                    "is %d req/sec.", request_limit - delta, limit)

                # Sleep the remaining time
                time.sleep(request_limit - delta)

            # Update last request time.
            last_requests[lock] = time.time()

    try:
        # Request URL and wait for response
        logger.debug("Requesting URL via %s method: %s", method.upper(), url)
        response = request_method(url, **kwargs)

        # If status code != OK, then raise exception, except if the status code
        # is white listed.
        if whitelist_status_code and auto_raise:
            if response.status_code not in whitelist_status_code:
                try:
                    response.raise_for_status()
                except:
                    logger.debug("Response status code %d is not white " \
                         "listed, raised exception", response.status_code)
                    raise
        elif auto_raise:
            response.raise_for_status()

        return response
    except requests.ConnectionError:
        logger.error("Unable to connect to remote host. Check if the remote " \
            "host is up and running.")
    except requests.Timeout:
        logger.error("Request timed out. The remote host did not respeond " \
            "timely.")
    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code >= 500:
                cause = "remote server error"
            elif e.response.status_code >= 400:
                cause = "local client error"
            else:
                # I don't think we will end up here, but for completeness
                cause = "unknown"

            logger.error("Request raise HTTP error with status code %d (%s).",
                e.response.status_code, cause)

            # Debug response
            if headphones.VERBOSE:
                server_message(e.response)
        else:
            logger.error("Request raised HTTP error.")
    except requests.RequestException as e:
        logger.error("Request raised exception: %s", e)

def request_soup(url, **kwargs):
    """
    Wrapper for `request_response', which will return a BeatifulSoup object if
    no exceptions are raised.
    """

    parser = kwargs.pop("parser", "html5lib")
    response = request_response(url, **kwargs)

    if response is not None:
        return BeautifulSoup(response.content, parser)

def request_minidom(url, **kwargs):
    """
    Wrapper for `request_response', which will return a Minidom object if no
    exceptions are raised.
    """

    response = request_response(url, **kwargs)

    if response is not None:
        return minidom.parseString(response.content)

def request_json(url, **kwargs):
    """
    Wrapper for `request_response', which will decode the response as JSON
    object and return the result, if no exceptions are raised.

    As an option, a validator callback can be given, which should return True if
    the result is valid.
    """

    validator = kwargs.pop("validator", None)
    response = request_response(url, **kwargs)

    if response is not None:
        try:
            result = response.json()

            if validator and not validator(result):
                logger.error("JSON validation result failed")
            else:
                return result
        except ValueError:
            logger.error("Response returned invalid JSON data")

            # Debug response
            if headphones.VERBOSE:
                server_message(response)

def request_content(url, **kwargs):
    """
    Wrapper for `request_response', which will return the raw content.
    """

    response = request_response(url, **kwargs)

    if response is not None:
        return response.content

def request_feed(url, **kwargs):
    """
    Wrapper for `request_response', which will return a feed object.
    """

    response = request_response(url, **kwargs)

    if response is not None:
        return feedparser.parse(response.content)

def server_message(response):
    """
    Extract server message from response and log in to logger with DEBUG level.

    Some servers return extra information in the result. Try to parse it for
    debugging purpose. Messages are limited to 150 characters, since it may
    return the whole page in case of normal web page URLs
    """

    message = None

    # First attempt is to 'read' the response as HTML
    if "text/html" in response.headers.get("content-type"):
        try:
            soup = BeautifulSoup(response.content, "html5lib")
        except Exception:
            pass

        # Find body and cleanup common tags to grab content, which probably
        # contains the message.
        message = soup.find("body")

        for element in ["header", "script", "footer", "nav", "input",
            "textarea"]:

            for tag in soup.find_all(element):
                tag.replaceWith("")

        message = message.text if message else soup.text
        message = message.strip()

    # Second attempt is to just take the response
    if message is None:
        message = response.content.strip()

    if message:
        # Truncate message if it is too long.
        if len(message) > 150:
            message = message[:150] + "..."

        logger.debug("Server responded with message: %s", message)