"""
The MIT License

Copyright (c) 2007 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import urllib
import time
import random
import urlparse
import hmac
import binascii
import lib.httplib2 as httplib2

try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class Error(RuntimeError):
    """Generic exception class."""

    def __init__(self, message='OAuth error occured.'):
        self._message = message

    @property
    def message(self):
        """A hack to get around the deprecation errors in 2.6."""
        return self._message

    def __str__(self):
        return self._message

class MissingSignature(Error):
    pass

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class Consumer(object):
    """A consumer of OAuth-protected services.
 
    The OAuth consumer is a "third-party" service that wants to access
    protected resources from an OAuth service provider on behalf of an end
    user. It's kind of the OAuth client.
 
    Usually a consumer must be registered with the service provider by the
    developer of the consumer software. As part of that process, the service
    provider gives the consumer a *key* and a *secret* with which the consumer
    software can identify itself to the service. The consumer will include its
    key in each request to identify itself, but will use its secret only when
    signing requests, to prove that the request is from that particular
    registered consumer.
 
    Once registered, the consumer can then use its consumer credentials to ask
    the service provider for a request token, kicking off the OAuth
    authorization process.
    """

    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

    def __str__(self):
        data = {
            'oauth_consumer_key': self.key,
            'oauth_consumer_secret': self.secret
        }

        return urllib.urlencode(data)


class Token(object):
    """An OAuth credential used to request authorization or a protected
    resource.
 
    Tokens in OAuth comprise a *key* and a *secret*. The key is included in
    requests to identify the token being used, but the secret is used only in
    the signature, to prove that the requester is who the server gave the
    token to.
 
    When first negotiating the authorization, the consumer asks for a *request
    token* that the live user authorizes with the service provider. The
    consumer then exchanges the request token for an *access token* that can
    be used to access protected resources.
    """

    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        """Returns this token as a plain string, suitable for storage.
 
        The resulting string includes the token's secret, so you should never
        send or store this string where a third party can read it.
        """

        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }

        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    @staticmethod
    def from_string(s):
        """Deserializes a token from a string like one returned by
        `to_string()`."""

        if not len(s):
            raise ValueError("Invalid parameter string.")

        params = parse_qs(s, keep_blank_values=False)
        if not len(params):
            raise ValueError("Invalid parameter string.")

        try:
            key = params['oauth_token'][0]
        except Exception:
            raise ValueError("'oauth_token' not found in OAuth request.")

        try:
            secret = params['oauth_token_secret'][0]
        except Exception:
            raise ValueError("'oauth_token_secret' not found in " 
                "OAuth request.")

        token = Token(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token

    def __str__(self):
        return self.to_string()


def setter(attr):
    name = attr.__name__
 
    def getter(self):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError(name)
 
    def deleter(self):
        del self.__dict__[name]
 
    return property(getter, attr, deleter)


class Request(dict):
 
    """The parameters and information for an HTTP request, suitable for
    authorizing with OAuth credentials.
 
    When a consumer wants to access a service's protected resources, it does
    so using a signed HTTP request identifying itself (the consumer) with its
    key, and providing an access token authorized by the end user to access
    those resources.
 
    """
 
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION
 
    def __init__(self, method=HTTP_METHOD, url=None, parameters=None):
        if method is not None:
            self.method = method
 
        if url is not None:
            self.url = url
 
        if parameters is not None:
            self.update(parameters)
 
    @setter
    def url(self, value):
        parts = urlparse.urlparse(value)
        scheme, netloc, path = parts[:3]

        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]

        if scheme != 'http' and scheme != 'https':
            raise ValueError("Unsupported URL %s (%s)." % (value, scheme))

        value = '%s://%s%s' % (scheme, netloc, path)
        self.__dict__['url'] = value
 
    @setter
    def method(self, value):
        self.__dict__['method'] = value.upper()
 
    def _get_timestamp_nonce(self):
        return self['oauth_timestamp'], self['oauth_nonce']
 
    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        return dict([(k, v) for k, v in self.iteritems() 
                    if not k.startswith('oauth_')])
 
    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        oauth_params = ((k, v) for k, v in self.items() 
                            if k.startswith('oauth_'))
        stringy_params = ((k, escape(str(v))) for k, v in oauth_params)
        header_params = ('%s="%s"' % (k, v) for k, v in stringy_params)
        params_header = ', '.join(header_params)
 
        auth_header = 'OAuth realm="%s"' % realm
        if params_header:
            auth_header = "%s, %s" % (auth_header, params_header)
 
        return {'Authorization': auth_header}
 
    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return self.encode_postdata(self)

    def encode_postdata(self, data):
        # tell urlencode to deal with sequence values and map them correctly
        # to resulting querystring. for example self["k"] = ["v1", "v2"] will
        # result in 'k=v1&k=v2' and not k=%5B%27v1%27%2C+%27v2%27%5D
        return urllib.urlencode(data, True)

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.url, self.to_postdata())

    def get_parameter(self, parameter):
        ret = self.get(parameter)
        if ret is None:
            raise Error('Parameter not found: %s' % parameter)

        return ret
 
    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        items = [(k, v) for k, v in self.items() if k != 'oauth_signature']
        encoded_str = urllib.urlencode(sorted(items), True)
        # Encode signature parameters per Oauth Core 1.0 protocol
        # spec draft 7, section 3.6
        # (http://tools.ietf.org/html/draft-hammer-oauth-07#section-3.6)
        # Spaces must be encoded with "%20" instead of "+"
        return encoded_str.replace('+', '%20')
 
    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of sign."""

        if 'oauth_consumer_key' not in self:
            self['oauth_consumer_key'] = consumer.key

        if token and 'oauth_token' not in self:
            self['oauth_token'] = token.key

        self['oauth_signature_method'] = signature_method.name
        self['oauth_signature'] = signature_method.sign(self, consumer, token)
 
    @classmethod
    def make_timestamp(cls):
        """Get seconds since epoch (UTC)."""
        return str(int(time.time()))
 
    @classmethod
    def make_nonce(cls):
        """Generate pseudorandom number."""
        return str(random.randint(0, 100000000))
 
    @classmethod
    def from_request(cls, http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}
 
        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = cls._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise Error('Unable to parse OAuth parameters from '
                        'Authorization header.')
 
        # GET or POST query string.
        if query_string:
            query_params = cls._split_url_string(query_string)
            parameters.update(query_params)
 
        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = cls._split_url_string(param_str)
        parameters.update(url_params)
 
        if parameters:
            return cls(http_method, http_url, parameters)
 
        return None
 
    @classmethod
    def from_consumer_and_token(cls, consumer, token=None,
            http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}
 
        defaults = {
            'oauth_consumer_key': consumer.key,
            'oauth_timestamp': cls.make_timestamp(),
            'oauth_nonce': cls.make_nonce(),
            'oauth_version': cls.version,
        }
 
        defaults.update(parameters)
        parameters = defaults
 
        if token:
            parameters['oauth_token'] = token.key
 
        return Request(http_method, http_url, parameters)
 
    @classmethod
    def from_token_and_callback(cls, token, callback=None, 
        http_method=HTTP_METHOD, http_url=None, parameters=None):

        if not parameters:
            parameters = {}
 
        parameters['oauth_token'] = token.key
 
        if callback:
            parameters['oauth_callback'] = callback
 
        return cls(http_method, http_url, parameters)
 
    @staticmethod
    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
 
    @staticmethod
    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters


class Server(object):
    """A skeletal implementation of a service provider, providing protected
    resources to requests from authorized consumers.
 
    This class implements the logic to check requests for authorization. You
    can use it with your web server or web framework to protect certain
    resources with OAuth.
    """

    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None

    def __init__(self, signature_methods=None):
        self.signature_methods = signature_methods or {}

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.name] = signature_method
        return self.signature_methods

    def verify_request(self, request, consumer, token):
        """Verifies an api call and checks all the parameters."""

        version = self._get_version(request)
        self._check_signature(request, consumer, token)
        parameters = request.get_nonoauth_parameters()
        return parameters

    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, request):
        """Verify the correct version request for this server."""
        try:
            version = request.get_parameter('oauth_version')
        except:
            version = VERSION

        if version and version != self.version:
            raise Error('OAuth version %s not supported.' % str(version))

        return version

    def _get_signature_method(self, request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = request.get_parameter('oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD

        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise Error('Signature method %s not supported try one of the following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_verifier(self, request):
        return request.get_parameter('oauth_verifier')

    def _check_signature(self, request, consumer, token):
        timestamp, nonce = request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        signature_method = self._get_signature_method(request)

        try:
            signature = request.get_parameter('oauth_signature')
        except:
            raise MissingSignature('Missing oauth_signature.')

        # Validate the signature.
        valid = signature_method.check(request, consumer, token, signature)

        if not valid:
            key, base = signature_method.signing_base(request, consumer, token)

            raise Error('Invalid signature. Expected signature base ' 
                'string: %s' % base)

        built = signature_method.sign(request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise Error('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' % (timestamp, now, self.timestamp_threshold))


class Client(httplib2.Http):
    """OAuthClient is a worker to attempt to execute a request."""

    def __init__(self, consumer, token=None, cache=None, timeout=None,
        proxy_info=None):

        if consumer is not None and not isinstance(consumer, Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, Token):
            raise ValueError("Invalid token.")

        self.consumer = consumer
        self.token = token
        self.method = SignatureMethod_HMAC_SHA1()

        httplib2.Http.__init__(self, cache=cache, timeout=timeout, 
            proxy_info=proxy_info)

    def set_signature_method(self, method):
        if not isinstance(method, SignatureMethod):
            raise ValueError("Invalid signature method.")

        self.method = method

    def request(self, uri, method="GET", body=None, headers=None, 
        redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None,
        force_auth_header=False):
        
        if not isinstance(headers, dict):
            headers = {}

        if body and method == "POST":
            parameters = dict(parse_qsl(body))
        elif method == "GET":
            parsed = urlparse.urlparse(uri)
            parameters = parse_qs(parsed.query)     
        else:
            parameters = None

        req = Request.from_consumer_and_token(self.consumer, token=self.token,
            http_method=method, http_url=uri, parameters=parameters)

        req.sign_request(self.method, self.consumer, self.token)

        if force_auth_header:
            # ensure we always send Authorization
            headers.update(req.to_header())

        if method == "POST":
            if not force_auth_header:
                body = req.to_postdata()
            else:
                body = req.encode_postdata(req.get_nonoauth_parameters())
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        elif method == "GET":
            if not force_auth_header:
                uri = req.to_url()
        else:
            if not force_auth_header:
                # don't call update twice.
                headers.update(req.to_header())

        return httplib2.Http.request(self, uri, method=method, body=body, 
            headers=headers, redirections=redirections, 
            connection_type=connection_type)


class SignatureMethod(object):
    """A way of signing requests.
 
    The OAuth protocol lets consumers and service providers pick a way to sign
    requests. This interface shows the methods expected by the other `oauth`
    modules for signing requests. Subclass it and implement its methods to
    provide a new way to sign requests.
    """

    def signing_base(self, request, consumer, token):
        """Calculates the string that needs to be signed.

        This method returns a 2-tuple containing the starting key for the
        signing and the message to be signed. The latter may be used in error
        messages to help clients debug their software.

        """
        raise NotImplementedError

    def sign(self, request, consumer, token):
        """Returns the signature for the given request, based on the consumer
        and token also provided.

        You should use your implementation of `signing_base()` to build the
        message to sign. Otherwise it may be less useful for debugging.

        """
        raise NotImplementedError

    def check(self, request, consumer, token, signature):
        """Returns whether the given signature is the correct signature for
        the given consumer and token signing the given request."""
        built = self.sign(request, consumer, token)
        return built == signature


class SignatureMethod_HMAC_SHA1(SignatureMethod):
    name = 'HMAC-SHA1'
        
    def signing_base(self, request, consumer, token):
        sig = (
            escape(request.method),
            escape(request.url),
            escape(request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except ImportError:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]

class SignatureMethod_PLAINTEXT(SignatureMethod):

    name = 'PLAINTEXT'

    def signing_base(self, request, consumer, token):
        """Concatenates the consumer key and secret with the token's
        secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def sign(self, request, consumer, token):
        key, raw = self.signing_base(request, consumer, token)
        return raw

