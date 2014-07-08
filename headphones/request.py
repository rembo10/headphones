from headphones import logger

from xml.dom import minidom
from bs4 import BeautifulSoup

import requests
import feedparser
import headphones

def request_response(url, method="get", auto_raise=True, whitelist_status_code=None, **kwargs):
    """
    Convenient wrapper for `requests.get', which will capture the exceptions and
    log them. On success, the Response object is returned. In case of a
    exception, None is returned.
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

    try:
        # Request the URL
        logger.debug("Requesting URL via %s method: %s", method.upper(), url)
        response = request_method(url, **kwargs)

        # If status code != OK, then raise exception, except if the status code
        # is white listed.
        if whitelist_status_code and auto_raise:
            if response.status_code not in whitelist_status_code:
                try:
                    response.raise_for_status()
                except:
                    logger.debug("Response status code %d is not white listed, raised exception", response.status_code)
                    raise
        elif auto_raise:
            response.raise_for_status()

        return response
    except requests.ConnectionError:
        logger.error("Unable to connect to remote host. Check if the remote host is up and running.")
    except requests.Timeout:
        logger.error("Request timed out. The remote host did not respeond timely.")
    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code >= 500:
                cause = "remote server error"
            elif e.response.status_code >= 400:
                cause = "local request error"
            else:
                # I don't think we will end up here, but for completeness
                cause = "unknown"

            logger.error("Request raise HTTP error with status code %d (%s).", e.response.status_code, cause)

            # Some servers return extra information in the result. Try to parse
            # it for debugging purpose. Messages are limited to 100 characters,
            # since it may return the whole page in case of normal web page URLs
            if headphones.VERBOSE:
                if e.response.headers.get('content-type') == 'text/html':
                    soup = BeautifulSoup(e.response.content, "html5lib")

                    message = soup.find("body")
                    message = message.text if message else soup.text
                else:
                    message = e.response.content

                if message:
                    # Truncate message if it is too long.
                    if len(message) > 100:
                        message = message[:100] + "..."

                    logger.debug("Server responded with message: %s", message)
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
                logger.error("JSON validation result vailed")
            else:
                return result
        except ValueError:
            logger.error("Response returned invalid JSON data")

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