"""Classes for interacting with the MusicBrainz XML web service.

The L{WebService} class talks to a server implementing the MusicBrainz XML
web service. It mainly handles URL generation and network I/O. Use this
if maximum control is needed.

The L{Query} class provides a convenient interface to the most commonly
used features of the web service. By default it uses L{WebService} to
retrieve data and the L{XML parser <musicbrainz2.wsxml>} to parse the
responses. The results are object trees using the L{MusicBrainz domain
model <musicbrainz2.model>}.

@author: Matthias Friedrich <matt@mafr.de>
"""
__revision__ = '$Id: webservice.py 12973 2011-04-29 11:49:31Z luks $'

import re
import urllib
import urllib2
import base64
import urlparse
import logging
import os.path
from StringIO import StringIO
import lib.musicbrainz2 as musicbrainz2
from lib.musicbrainz2.model import Artist, Release, Track
from lib.musicbrainz2.wsxml import MbXmlParser, ParseError
import lib.musicbrainz2.utils as mbutils

__all__ = [
	'WebServiceError', 'AuthenticationError', 'ConnectionError',
	'RequestError', 'ResourceNotFoundError', 'ResponseError', 
	'IIncludes', 'ArtistIncludes', 'ReleaseIncludes', 'TrackIncludes',
	'LabelIncludes', 'ReleaseGroupIncludes',
	'IFilter', 'ArtistFilter', 'ReleaseFilter', 'TrackFilter',
	'UserFilter', 'LabelFilter', 'ReleaseGroupFilter',
	'IWebService', 'WebService', 'Query',
]


class IWebService(object):
	"""An interface all concrete web service classes have to implement.

	All web service classes have to implement this and follow the
	method specifications.
	"""

	def get(self, entity, id_, include, filter, version):
		"""Query the web service.

		Using this method, you can either get a resource by id (using
		the C{id_} parameter, or perform a query on all resources of
		a type.

		The C{filter} and the C{id_} parameter exclude each other. If
		you are using a filter, you may not set C{id_} and vice versa.

		Returns a file-like object containing the result or raises a
		L{WebServiceError} or one of its subclasses in case of an
		error. Which one is used depends on the implementing class.

		@param entity: a string containing the entity's name
		@param id_: a string containing a UUID, or the empty string
		@param include: a tuple containing values for the 'inc' parameter
		@param filter: parameters, depending on the entity
		@param version: a string containing the web service version to use

		@return: a file-like object

		@raise WebServiceError: in case of errors
		"""
		raise NotImplementedError()


	def post(self, entity, id_, data, version):
		"""Submit data to the web service.

		@param entity: a string containing the entity's name
		@param id_: a string containing a UUID, or the empty string
		@param data: A string containing the data to post
		@param version: a string containing the web service version to use

		@return: a file-like object

		@raise WebServiceError: in case of errors
		"""
		raise NotImplementedError()


class WebServiceError(Exception):
	"""A web service error has occurred.

	This is the base class for several other web service related
	exceptions.
	"""

	def __init__(self, msg='Webservice Error', reason=None):
		"""Constructor.

		Set C{msg} to an error message which explains why this
		exception was raised. The C{reason} parameter should be the
		original exception which caused this L{WebService} exception
		to be raised. If given, it has to be an instance of
		C{Exception} or one of its child classes.

		@param msg: a string containing an error message
		@param reason: another exception instance, or None
		"""
		Exception.__init__(self)
		self.msg = msg
		self.reason = reason

	def __str__(self):
		"""Makes this class printable.

		@return: a string containing an error message
		"""
		return self.msg


class ConnectionError(WebServiceError):
	"""Getting a server connection failed.

	This exception is mostly used if the client couldn't connect to
	the server because of an invalid host name or port. It doesn't
	make sense if the web service in question doesn't use the network.
	"""
	pass


class RequestError(WebServiceError):
	"""An invalid request was made.

	This exception is raised if the client made an invalid request.
	That could be syntactically invalid identifiers or unknown or
	invalid parameter values.
	"""
	pass


class ResourceNotFoundError(WebServiceError):
	"""No resource with the given ID exists.

	This is usually a wrapper around IOError (which is superclass of
	HTTPError).
	"""
	pass


class AuthenticationError(WebServiceError):
	"""Authentication failed.

	This is thrown if user name, password or realm were invalid while
	trying to access a protected resource.
	"""
	pass


class ResponseError(WebServiceError):
	"""The returned resource was invalid.

	This may be due to a malformed XML document or if the requested
	data wasn't part of the response. It can only occur in case of
	bugs in the web service itself.
	"""
	pass

class DigestAuthHandler(urllib2.HTTPDigestAuthHandler):
	"""Patched DigestAuthHandler to correctly handle Digest Auth according to RFC 2617.
	
	This will allow multiple qop values in the WWW-Authenticate header (e.g. "auth,auth-int").
	The only supported qop value is still auth, though.
	See http://bugs.python.org/issue9714
	
	@author Kuno Woudt
	"""
	def get_authorization(self, req, chal):
		qop = chal.get('qop')
		if qop and ',' in qop and 'auth' in qop.split(','):
			chal['qop'] = 'auth'
		
		return urllib2.HTTPDigestAuthHandler.get_authorization(self, req, chal)

class WebService(IWebService):
	"""An interface to the MusicBrainz XML web service via HTTP.

	By default, this class uses the MusicBrainz server but may be
	configured for accessing other servers as well using the
	L{constructor <__init__>}. This implements L{IWebService}, so
	additional documentation on method parameters can be found there.
	"""

	def __init__(self, host='musicbrainz.org', port=80, pathPrefix='/ws',
			username=None, password=None, realm='musicbrainz.org',
			opener=None, mirror=None):
		"""Constructor.

		This can be used without parameters. In this case, the
		MusicBrainz server will be used.

		@param host: a string containing a host name
		@param port: an integer containing a port number
		@param pathPrefix: a string prepended to all URLs
		@param username: a string containing a MusicBrainz user name
		@param password: a string containing the user's password
		@param realm: a string containing the realm used for authentication
		@param opener: an C{urllib2.OpenerDirector} object used for queries
		"""
		self._host = host
		self._port = port
		self._username = username
		self._password = password
		self._realm = realm
		self._pathPrefix = pathPrefix
		self._log = logging.getLogger(str(self.__class__))
		self._mirror = mirror

		if opener is None:
			self._opener = urllib2.build_opener()
		else:
			self._opener = opener

		passwordMgr = self._RedirectPasswordMgr()
		authHandler = DigestAuthHandler(passwordMgr)
		authHandler.add_password(self._realm, (), # no host set
			self._username, self._password)
		self._opener.add_handler(authHandler)


	def _makeUrl(self, entity, id_, include=( ), filter={ },
			version='1', type_='xml'):
		params = dict(filter)
		if type_ is not None:
			params['type'] = type_
		if len(include) > 0:
			params['inc'] = ' '.join(include)

		netloc = self._host
		if self._port != 80:
			netloc += ':' + str(self._port)
		path = '/'.join((self._pathPrefix, version, entity, id_))

		query = urllib.urlencode(params)

		url = urlparse.urlunparse(('http', netloc, path, '', query,''))

		return url


	def _openUrl(self, url, data=None):
		userAgent = 'python-headphones/' + musicbrainz2.__version__
		req = urllib2.Request(url)
		req.add_header('User-Agent', userAgent)
		if self._mirror == 'headphones':
			base64string = base64.encodestring('%s:%s' % (self._username, self._password)).replace('\n', '')
			req.add_header("Authorization", "Basic %s" % base64string)
		return self._opener.open(req, data)


	def get(self, entity, id_, include=( ), filter={ }, version='1'):
		"""Query the web service via HTTP-GET.

		Returns a file-like object containing the result or raises a
		L{WebServiceError}. Conditions leading to errors may be
		invalid entities, IDs, C{include} or C{filter} parameters
		and unsupported version numbers.

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid IDs or parameters
		@raise AuthenticationError: invalid user name and/or password
		@raise ResourceNotFoundError: resource doesn't exist

		@see: L{IWebService.get}
		"""
		url = self._makeUrl(entity, id_, include, filter, version)

		self._log.debug('GET ' + url)

		try:
			return self._openUrl(url)
		except urllib2.HTTPError, e:
			self._log.debug("GET failed: " + str(e))
			if e.code == 400:   # in python 2.4: httplib.BAD_REQUEST
				raise RequestError(str(e), e)
			elif e.code == 401: # httplib.UNAUTHORIZED
				raise AuthenticationError(str(e), e)
			elif e.code == 404: # httplib.NOT_FOUND
				raise ResourceNotFoundError(str(e), e)
			else:
				raise WebServiceError(str(e), e)
		except urllib2.URLError, e:
			self._log.debug("GET failed: " + str(e))
			raise ConnectionError(str(e), e)


	def post(self, entity, id_, data, version='1'):
		"""Send data to the web service via HTTP-POST.

		Note that this may require authentication. You can set
		user name, password and realm in the L{constructor <__init__>}.

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid IDs or parameters
		@raise AuthenticationError: invalid user name and/or password
		@raise ResourceNotFoundError: resource doesn't exist

		@see: L{IWebService.post}
		"""
		url = self._makeUrl(entity, id_, version=version, type_=None)

		self._log.debug('POST ' + url)
		self._log.debug('POST-BODY: ' + data)

		try:
			return self._openUrl(url, data)
		except urllib2.HTTPError, e:
			self._log.debug("POST failed: " + str(e))
			if e.code == 400:   # in python 2.4: httplib.BAD_REQUEST
				raise RequestError(str(e), e)
			elif e.code == 401: # httplib.UNAUTHORIZED
				raise AuthenticationError(str(e), e)
			elif e.code == 404: # httplib.NOT_FOUND
				raise ResourceNotFoundError(str(e), e)
			else:
				raise WebServiceError(str(e), e)
		except urllib2.URLError, e:
			self._log.debug("POST failed: " + str(e))
			raise ConnectionError(str(e), e)


	# Special password manager which also works with redirects by simply
	# ignoring the URI. As a consequence, only *ONE* (username, password)
	# tuple per realm can be used for all URIs.
	#
	class _RedirectPasswordMgr(urllib2.HTTPPasswordMgr):
		def __init__(self):
			self._realms = { }

		def find_user_password(self, realm, uri):
			# ignoring the uri parameter intentionally
			try:
				return self._realms[realm]
			except KeyError:
				return (None, None)

		def add_password(self, realm, uri, username, password):
			# ignoring the uri parameter intentionally
			self._realms[realm] = (username, password)


class IFilter(object):
	"""A filter for collections.

	This is the interface all filters have to implement. Filter classes
	are initialized with a set of criteria and are then applied to
	collections of items. The criteria are usually strings or integer
	values, depending on the filter.

	Note that all strings passed to filters should be unicode strings
	(python type C{unicode}). Standard strings are converted to unicode
	internally, but have a limitation: Only 7 Bit pure ASCII characters
	may be used, otherwise a C{UnicodeDecodeError} is raised.
	"""
	def createParameters(self):
		"""Create a list of query parameters.

		This method creates a list of (C{parameter}, C{value}) tuples,
		based on the contents of the implementing subclass.
		C{parameter} is a string containing a parameter name
		and C{value} an arbitrary string. No escaping of those strings
		is required. 

		@return: a sequence of (key, value) pairs
		"""
		raise NotImplementedError()


class ArtistFilter(IFilter):
	"""A filter for the artist collection."""

	def __init__(self, name=None, limit=None, offset=None, query=None):
		"""Constructor.

		The C{query} parameter may contain a query in U{Lucene syntax
		<http://lucene.apache.org/java/docs/queryparsersyntax.html>}.
		Note that the C{name} and C{query} may not be used together.

		@param name: a unicode string containing the artist's name
		@param limit: the maximum number of artists to return
		@param offset: start results at this zero-based offset
		@param query: a string containing a query in Lucene syntax
		"""
		self._params = [
			('name', name),
			('limit', limit),
			('offset', offset),
			('query', query),
		]

		if not _paramsValid(self._params):
			raise ValueError('invalid combination of parameters')

	def createParameters(self):
		return _createParameters(self._params)


class LabelFilter(IFilter):
	"""A filter for the label collection."""

	def __init__(self, name=None, limit=None, offset=None, query=None):
		"""Constructor.

		The C{query} parameter may contain a query in U{Lucene syntax
		<http://lucene.apache.org/java/docs/queryparsersyntax.html>}.
		Note that the C{name} and C{query} may not be used together.

		@param name: a unicode string containing the label's name
		@param limit: the maximum number of labels to return
		@param offset: start results at this zero-based offset
		@param query: a string containing a query in Lucene syntax
		"""
		self._params = [
			('name', name),
			('limit', limit),
			('offset', offset),
			('query', query),
		]

		if not _paramsValid(self._params):
			raise ValueError('invalid combination of parameters')

	def createParameters(self):
		return _createParameters(self._params)

class ReleaseGroupFilter(IFilter):
	"""A filter for the release group collection."""

	def __init__(self, title=None, releaseTypes=None, artistName=None,
			artistId=None, limit=None, offset=None, query=None):
		"""Constructor.

		If C{artistId} is set, only releases matching those IDs are
		returned.  The C{releaseTypes} parameter allows you to limit
		the types of the release groups returned. You can set it to
		C{(Release.TYPE_ALBUM, Release.TYPE_OFFICIAL)}, for example,
		to only get officially released albums. Note that those values
		are connected using the I{AND} operator. MusicBrainz' support
		is currently very limited, so C{Release.TYPE_LIVE} and
		C{Release.TYPE_COMPILATION} exclude each other (see U{the
		documentation on release attributes
		<http://wiki.musicbrainz.org/AlbumAttribute>} for more
		information and all valid values).

		If both the C{artistName} and the C{artistId} parameter are
		given, the server will ignore C{artistName}.

		The C{query} parameter may contain a query in U{Lucene syntax
		<http://lucene.apache.org/java/docs/queryparsersyntax.html>}.
		Note that C{query} may not be used together with the other
		parameters except for C{limit} and C{offset}.

		@param title: a unicode string containing the release group's title
		@param releaseTypes: a sequence of release type URIs
		@param artistName: a unicode string containing the artist's name
		@param artistId: a unicode string containing the artist's ID
		@param limit: the maximum number of release groups to return
		@param offset: start results at this zero-based offset
		@param query: a string containing a query in Lucene syntax

		@see: the constants in L{musicbrainz2.model.Release}
		"""
		if releaseTypes is None or len(releaseTypes) == 0:
			releaseTypesStr = None
		else:
			releaseTypesStr = ' '.join(map(mbutils.extractFragment, releaseTypes))

		self._params = [
			('title', title),
			('releasetypes', releaseTypesStr),
			('artist', artistName),
			('artistid', mbutils.extractUuid(artistId)),
			('limit', limit),
			('offset', offset),
			('query', query),
		]

		if not _paramsValid(self._params):
			raise ValueError('invalid combination of parameters')

	def createParameters(self):
		return _createParameters(self._params)


class ReleaseFilter(IFilter):
	"""A filter for the release collection."""

	def __init__(self, title=None, discId=None, releaseTypes=None,
			artistName=None, artistId=None, limit=None,
			offset=None, query=None, trackCount=None):
		"""Constructor.

		If C{discId} or C{artistId} are set, only releases matching
		those IDs are returned. The C{releaseTypes} parameter allows
		to limit the types of the releases returned. You can set it to
		C{(Release.TYPE_ALBUM, Release.TYPE_OFFICIAL)}, for example,
		to only get officially released albums. Note that those values
		are connected using the I{AND} operator. MusicBrainz' support
		is currently very limited, so C{Release.TYPE_LIVE} and
		C{Release.TYPE_COMPILATION} exclude each other (see U{the
		documentation on release attributes
		<http://wiki.musicbrainz.org/AlbumAttribute>} for more
		information and all valid values).

		If both the C{artistName} and the C{artistId} parameter are
		given, the server will ignore C{artistName}.

		The C{query} parameter may contain a query in U{Lucene syntax
		<http://lucene.apache.org/java/docs/queryparsersyntax.html>}.
		Note that C{query} may not be used together with the other
		parameters except for C{limit} and C{offset}.

		@param title: a unicode string containing the release's title
		@param discId: a unicode string containing the DiscID
		@param releaseTypes: a sequence of release type URIs
		@param artistName: a unicode string containing the artist's name
		@param artistId: a unicode string containing the artist's ID
		@param limit: the maximum number of releases to return
		@param offset: start results at this zero-based offset
		@param query: a string containing a query in Lucene syntax
		@param trackCount: the number of tracks in the release

		@see: the constants in L{musicbrainz2.model.Release}
		"""
		if releaseTypes is None or len(releaseTypes) == 0:
			releaseTypesStr = None
		else:
			tmp = [ mbutils.extractFragment(x) for x in releaseTypes ]
			releaseTypesStr = ' '.join(tmp)

		self._params = [
			('title', title),
			('discid', discId),
			('releasetypes', releaseTypesStr),
			('artist', artistName),
			('artistid', mbutils.extractUuid(artistId)),
			('limit', limit),
			('offset', offset),
			('query', query),
			('count', trackCount),
		]

		if not _paramsValid(self._params):
			raise ValueError('invalid combination of parameters')

	def createParameters(self):
		return _createParameters(self._params)


class TrackFilter(IFilter):
	"""A filter for the track collection."""

	def __init__(self, title=None, artistName=None, artistId=None,
			releaseTitle=None, releaseId=None,
			duration=None, puid=None, limit=None, offset=None,
			query=None):
		"""Constructor.

		If C{artistId}, C{releaseId} or C{puid} are set, only tracks
		matching those IDs are returned.

		The server will ignore C{artistName} and C{releaseTitle} if
		C{artistId} or ${releaseId} are set respectively.

		The C{query} parameter may contain a query in U{Lucene syntax
		<http://lucene.apache.org/java/docs/queryparsersyntax.html>}.
		Note that C{query} may not be used together with the other
		parameters except for C{limit} and C{offset}.

		@param title: a unicode string containing the track's title
		@param artistName: a unicode string containing the artist's name
		@param artistId: a string containing the artist's ID
		@param releaseTitle: a unicode string containing the release's title
		@param releaseId: a string containing the release's title
		@param duration: the track's length in milliseconds
		@param puid: a string containing a PUID
		@param limit: the maximum number of releases to return
		@param offset: start results at this zero-based offset
		@param query: a string containing a query in Lucene syntax
		"""
		self._params = [
			('title', title),
			('artist', artistName),
			('artistid', mbutils.extractUuid(artistId)),
			('release', releaseTitle),
			('releaseid', mbutils.extractUuid(releaseId)),
			('duration', duration),
			('puid', puid),
			('limit', limit),
			('offset', offset),
			('query', query),
		]

		if not _paramsValid(self._params):
			raise ValueError('invalid combination of parameters')

	def createParameters(self):
		return _createParameters(self._params)


class UserFilter(IFilter):
	"""A filter for the user collection."""

	def __init__(self, name=None):
		"""Constructor.

		@param name: a unicode string containing a MusicBrainz user name
		"""
		self._name = name

	def createParameters(self):
		if self._name is not None:
			return [ ('name', self._name.encode('utf-8')) ]
		else:
			return [ ]


class IIncludes(object):
	"""An interface implemented by include tag generators."""
	def createIncludeTags(self):
		raise NotImplementedError()


class ArtistIncludes(IIncludes):
	"""A specification on how much data to return with an artist.

	Example:

	>>> from musicbrainz2.model import Release
	>>> from musicbrainz2.webservice import ArtistIncludes
	>>> inc = ArtistIncludes(artistRelations=True, releaseRelations=True,
	... 		releases=(Release.TYPE_ALBUM, Release.TYPE_OFFICIAL))
	>>>

	The MusicBrainz server only supports some combinations of release
	types for the C{releases} and C{vaReleases} include tags. At the
	moment, not more than two release types should be selected, while
	one of them has to be C{Release.TYPE_OFFICIAL},
	C{Release.TYPE_PROMOTION} or C{Release.TYPE_BOOTLEG}.

	@note: Only one of C{releases} and C{vaReleases} may be given.
	"""
	def __init__(self, aliases=False, releases=(), vaReleases=(),
			artistRelations=False, releaseRelations=False,
			trackRelations=False, urlRelations=False, tags=False,
			ratings=False, releaseGroups=False):

		assert not isinstance(releases, basestring)
		assert not isinstance(vaReleases, basestring)
		assert len(releases) == 0 or len(vaReleases) == 0

		self._includes = {
			'aliases':		aliases,
			'artist-rels':		artistRelations,
			'release-groups':	releaseGroups,
			'release-rels':		releaseRelations,
			'track-rels':		trackRelations,
			'url-rels':		urlRelations,
			'tags':			tags,
			'ratings':		ratings,
		}

		for elem in releases:
			self._includes['sa-' + mbutils.extractFragment(elem)] = True

		for elem in vaReleases:
			self._includes['va-' + mbutils.extractFragment(elem)] = True

	def createIncludeTags(self):
		return _createIncludes(self._includes)


class ReleaseIncludes(IIncludes):
	"""A specification on how much data to return with a release."""
	def __init__(self, artist=False, counts=False, releaseEvents=False,
			discs=False, tracks=False,
			artistRelations=False, releaseRelations=False,
			trackRelations=False, urlRelations=False,
			labels=False, tags=False, ratings=False, isrcs=False,
			releaseGroup=False):
		self._includes = {
			'artist':		artist,
			'counts':		counts,
			'labels':		labels,
			'release-groups':	releaseGroup,
			'release-events':	releaseEvents,
			'discs':		discs,
			'tracks':		tracks,
			'artist-rels':		artistRelations,
			'release-rels':		releaseRelations,
			'track-rels':		trackRelations,
			'url-rels':		urlRelations,
			'tags':			tags,
			'ratings':		ratings,
			'isrcs':		isrcs,
		}

		# Requesting labels without releaseEvents makes no sense,
		# so we pull in releaseEvents, if necessary.
		if labels and not releaseEvents:
			self._includes['release-events'] = True
		# Ditto for isrcs with no tracks
		if isrcs and not tracks:
			self._includes['tracks'] = True

	def createIncludeTags(self):
		return _createIncludes(self._includes)


class ReleaseGroupIncludes(IIncludes):
	"""A specification on how much data to return with a release group."""

	def __init__(self, artist=False, releases=False, tags=False):
		"""Constructor.

		@param artist: Whether to include the release group's main artist info.
		@param releases: Whether to include the release group's releases.
		"""
		self._includes = {
			'artist':		artist,
			'releases':		releases,
		}

	def createIncludeTags(self):
		return _createIncludes(self._includes)


class TrackIncludes(IIncludes):
	"""A specification on how much data to return with a track."""
	def __init__(self, artist=False, releases=False, puids=False,
			artistRelations=False, releaseRelations=False,
			trackRelations=False, urlRelations=False, tags=False,
			ratings=False, isrcs=False):
		self._includes = {
			'artist':		artist,
			'releases':		releases,
			'puids':		puids,
			'artist-rels':		artistRelations,
			'release-rels':		releaseRelations,
			'track-rels':		trackRelations,
			'url-rels':		urlRelations,
			'tags':			tags,
			'ratings':		ratings,
			'isrcs':		isrcs,
		}

	def createIncludeTags(self):
		return _createIncludes(self._includes)


class LabelIncludes(IIncludes):
	"""A specification on how much data to return with a label."""
	def __init__(self, aliases=False, tags=False, ratings=False):
		self._includes = {
			'aliases':		aliases,
			'tags':			tags,
			'ratings':		ratings,
		}

	def createIncludeTags(self):
		return _createIncludes(self._includes)


class Query(object):
	"""A simple interface to the MusicBrainz web service.

	This is a facade which provides a simple interface to the MusicBrainz
	web service. It hides all the details like fetching data from a server,
	parsing the XML and creating an object tree. Using this class, you can
	request data by ID or search the I{collection} of all resources
	(artists, releases, or tracks) to retrieve those matching given
	criteria. This document contains examples to get you started.


	Working with Identifiers
	========================

	MusicBrainz uses absolute URIs as identifiers. For example, the artist
	'Tori Amos' is identified using the following URI::
		http://musicbrainz.org/artist/c0b2500e-0cef-4130-869d-732b23ed9df5

	In some situations it is obvious from the context what type of 
	resource an ID refers to. In these cases, abbreviated identifiers may
	be used, which are just the I{UUID} part of the URI. Thus the ID above
	may also be written like this::
		c0b2500e-0cef-4130-869d-732b23ed9df5

	All methods in this class which require IDs accept both the absolute
	URI and the abbreviated form (aka the relative URI).


	Creating a Query Object
	=======================

	In most cases, creating a L{Query} object is as simple as this:

	>>> import musicbrainz2.webservice as ws
	>>> q = ws.Query()
	>>>

	The instantiated object uses the standard L{WebService} class to
	access the MusicBrainz web service. If you want to use a different 
	server or you have to pass user name and password because one of
	your queries requires authentication, you have to create the
	L{WebService} object yourself and configure it appropriately.
	This example uses the MusicBrainz test server and also sets
	authentication data:

	>>> import musicbrainz2.webservice as ws
	>>> service = ws.WebService(host='test.musicbrainz.org',
	...				username='whatever', password='secret')
	>>> q = ws.Query(service)
	>>>


	Querying for Individual Resources
	=================================

	If the MusicBrainz ID of a resource is known, then the L{getArtistById},
	L{getReleaseById}, or L{getTrackById} method can be used to retrieve
	it. Example:

	>>> import musicbrainz2.webservice as ws
	>>> q = ws.Query()
	>>> artist = q.getArtistById('c0b2500e-0cef-4130-869d-732b23ed9df5')
	>>> artist.name
	u'Tori Amos'
	>>> artist.sortName
	u'Amos, Tori'
	>>> print artist.type
	http://musicbrainz.org/ns/mmd-1.0#Person
	>>>

	This returned just the basic artist data, however. To get more detail
	about a resource, the C{include} parameters may be used which expect
	an L{ArtistIncludes}, L{ReleaseIncludes}, or L{TrackIncludes} object,
	depending on the resource type.

	To get data about a release which also includes the main artist
	and all tracks, for example, the following query can be used:

	>>> import musicbrainz2.webservice as ws
	>>> q = ws.Query()
	>>> releaseId = '33dbcf02-25b9-4a35-bdb7-729455f33ad7'
	>>> include = ws.ReleaseIncludes(artist=True, tracks=True)
	>>> release = q.getReleaseById(releaseId, include)
	>>> release.title
	u'Tales of a Librarian'
	>>> release.artist.name
	u'Tori Amos'
	>>> release.tracks[0].title
	u'Precious Things'
	>>>

	Note that the query gets more expensive for the server the more
	data you request, so please be nice.


	Searching in Collections
	========================

	For each resource type (artist, release, and track), there is one
	collection which contains all resources of a type. You can search
	these collections using the L{getArtists}, L{getReleases}, and
	L{getTracks} methods. The collections are huge, so you have to
	use filters (L{ArtistFilter}, L{ReleaseFilter}, or L{TrackFilter})
	to retrieve only resources matching given criteria.

	For example, If you want to search the release collection for
	releases with a specified DiscID, you would use L{getReleases}
	and a L{ReleaseFilter} object:

	>>> import musicbrainz2.webservice as ws
	>>> q = ws.Query()
	>>> filter = ws.ReleaseFilter(discId='8jJklE258v6GofIqDIrE.c5ejBE-')
	>>> results = q.getReleases(filter=filter)
	>>> results[0].score
	100
	>>> results[0].release.title
	u'Under the Pink'
	>>>

	The query returns a list of results (L{wsxml.ReleaseResult} objects
	in this case), which are ordered by score, with a higher score
	indicating a better match. Note that those results don't contain
	all the data about a resource. If you need more detail, you can then
	use the L{getArtistById}, L{getReleaseById}, or L{getTrackById}
	methods to request the resource.

	All filters support the C{limit} argument to limit the number of
	results returned. This defaults to 25, but the server won't send
	more than 100 results to save bandwidth and processing power. Using
	C{limit} and the C{offset} parameter, you can page through the
	results.


	Error Handling
	==============

	All methods in this class raise a L{WebServiceError} exception in case
	of errors. Depending on the method, a subclass of L{WebServiceError} may
	be raised which allows an application to handle errors more precisely.
	The following example handles connection errors (invalid host name
	etc.) separately and all other web service errors in a combined
	catch clause:

	>>> try:
	...     artist = q.getArtistById('c0b2500e-0cef-4130-869d-732b23ed9df5')
	... except ws.ConnectionError, e:
	...     pass # implement your error handling here
	... except ws.WebServiceError, e:
	...     pass # catches all other web service errors
	... 
	>>>
	"""

	def __init__(self, ws=None, wsFactory=WebService, clientId=None):
		"""Constructor.

		The C{ws} parameter has to be a subclass of L{IWebService}.
		If it isn't given, the C{wsFactory} parameter is used to
		create an L{IWebService} subclass.

		If the constructor is called without arguments, an instance
		of L{WebService} is used, preconfigured to use the MusicBrainz
		server. This should be enough for most users.

		If you want to use queries which require authentication you
		have to pass a L{WebService} instance where user name and
		password have been set.

		The C{clientId} parameter is required for data submission.
		The format is C{'application-version'}, where C{application}
		is your application's name and C{version} is a version
		number which may not include a '-' character.

		@param ws: a subclass instance of L{IWebService}, or None
		@param wsFactory: a callable object which creates an object
		@param clientId: a unicode string containing the application's ID
		"""
		if ws is None:
			self._ws = wsFactory()
		else:
			self._ws = ws

		self._clientId = clientId
		self._log = logging.getLogger(str(self.__class__))


	def getArtistById(self, id_, include=None):
		"""Returns an artist.

		If no artist with that ID can be found, C{include} contains
		invalid tags or there's a server problem, an exception is
		raised.

		@param id_: a string containing the artist's ID
		@param include: an L{ArtistIncludes} object, or None

		@return: an L{Artist <musicbrainz2.model.Artist>} object, or None

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResourceNotFoundError: artist doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		uuid = mbutils.extractUuid(id_, 'artist')
		result = self._getFromWebService('artist', uuid, include)
		artist = result.getArtist()
		if artist is not None:
			return artist
		else:
			raise ResponseError("server didn't return artist")


	def getArtists(self, filter):
		"""Returns artists matching given criteria.

		@param filter: an L{ArtistFilter} object

		@return: a list of L{musicbrainz2.wsxml.ArtistResult} objects

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResponseError: server returned invalid data
		"""
		result = self._getFromWebService('artist', '', filter=filter)
		return result.getArtistResults()

	def getLabelById(self, id_, include=None):
		"""Returns a L{model.Label}
		
		If no label with that ID can be found, or there is a server problem,
		an exception is raised.
		
		@param id_: a string containing the label's ID.

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResourceNotFoundError: release doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		uuid = mbutils.extractUuid(id_, 'label')
		result = self._getFromWebService('label', uuid, include)
		label = result.getLabel()
		if label is not None:
			return label
		else:
			raise ResponseError("server didn't return a label")
	
	def getLabels(self, filter):
		result = self._getFromWebService('label', '', filter=filter)
		return result.getLabelResults()

	def getReleaseById(self, id_, include=None):
		"""Returns a release.

		If no release with that ID can be found, C{include} contains
		invalid tags or there's a server problem, and exception is
		raised.

		@param id_: a string containing the release's ID
		@param include: a L{ReleaseIncludes} object, or None

		@return: a L{Release <musicbrainz2.model.Release>} object, or None

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResourceNotFoundError: release doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		uuid = mbutils.extractUuid(id_, 'release')
		result = self._getFromWebService('release', uuid, include)
		release = result.getRelease()
		if release is not None:
			return release
		else:
			raise ResponseError("server didn't return release")


	def getReleases(self, filter):
		"""Returns releases matching given criteria.

		@param filter: a L{ReleaseFilter} object

		@return: a list of L{musicbrainz2.wsxml.ReleaseResult} objects

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResponseError: server returned invalid data
		"""
		result = self._getFromWebService('release', '', filter=filter)
		return result.getReleaseResults()
	
	def getReleaseGroupById(self, id_, include=None):
		"""Returns a release group.

		If no release group with that ID can be found, C{include}
		contains invalid tags, or there's a server problem, an
		exception is raised.

		@param id_: a string containing the release group's ID
		@param include: a L{ReleaseGroupIncludes} object, or None

		@return: a L{ReleaseGroup <musicbrainz2.model.ReleaseGroup>} object, or None

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResourceNotFoundError: release doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		uuid = mbutils.extractUuid(id_, 'release-group')
		result = self._getFromWebService('release-group', uuid, include)
		releaseGroup = result.getReleaseGroup()
		if releaseGroup is not None:
			return releaseGroup
		else:
			raise ResponseError("server didn't return releaseGroup")

	def getReleaseGroups(self, filter):
		"""Returns release groups matching the given criteria.
		
		@param filter: a L{ReleaseGroupFilter} object
		
		@return: a list of L{musicbrainz2.wsxml.ReleaseGroupResult} objects
		
		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResponseError: server returned invalid data
		"""
		result = self._getFromWebService('release-group', '', filter=filter)
		return result.getReleaseGroupResults()

	def getTrackById(self, id_, include=None):
		"""Returns a track.

		If no track with that ID can be found, C{include} contains
		invalid tags or there's a server problem, an exception is
		raised.

		@param id_: a string containing the track's ID
		@param include: a L{TrackIncludes} object, or None

		@return: a L{Track <musicbrainz2.model.Track>} object, or None

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResourceNotFoundError: track doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		uuid = mbutils.extractUuid(id_, 'track')
		result = self._getFromWebService('track', uuid, include)
		track = result.getTrack()
		if track is not None:
			return track
		else:
			raise ResponseError("server didn't return track")


	def getTracks(self, filter):
		"""Returns tracks matching given criteria.

		@param filter: a L{TrackFilter} object

		@return: a list of L{musicbrainz2.wsxml.TrackResult} objects

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise ResponseError: server returned invalid data
		"""
		result = self._getFromWebService('track', '', filter=filter)
		return result.getTrackResults()


	def getUserByName(self, name):
		"""Returns information about a MusicBrainz user.

		You can only request user data if you know the user name and
		password for that account. If username and/or password are
		incorrect, an L{AuthenticationError} is raised.

		See the example in L{Query} on how to supply user name and
		password.

		@param name: a unicode string containing the user's name

		@return: a L{User <musicbrainz2.model.User>} object

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or include tags
		@raise AuthenticationError: invalid user name and/or password
		@raise ResourceNotFoundError: track doesn't exist
		@raise ResponseError: server returned invalid data
		"""
		filter = UserFilter(name=name)
		result = self._getFromWebService('user', '', None, filter)

		if len(result.getUserList()) > 0:
			return result.getUserList()[0]
		else:
			raise ResponseError("response didn't contain user data")


	def _getFromWebService(self, entity, id_, include=None, filter=None):
		if filter is None:
			filterParams = [ ]
		else:
			filterParams = filter.createParameters()

		if include is None:
			includeParams = [ ]
		else:
			includeParams = include.createIncludeTags()

		stream = self._ws.get(entity, id_, includeParams, filterParams)
		try:
			parser = MbXmlParser()
			return parser.parse(stream)
		except ParseError, e:
			raise ResponseError(str(e), e)


	def submitPuids(self, tracks2puids):
		"""Submit track to PUID mappings.

		The C{tracks2puids} parameter has to be a dictionary, with the
		keys being MusicBrainz track IDs (either as absolute URIs or
		in their 36 character ASCII representation) and the values
		being PUIDs (ASCII, 36 characters).

		Note that this method only works if a valid user name and
		password have been set. See the example in L{Query} on how
		to supply authentication data.

		@param tracks2puids: a dictionary mapping track IDs to PUIDs

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid track or PUIDs
		@raise AuthenticationError: invalid user name and/or password
		"""
		assert self._clientId is not None, 'Please supply a client ID'
		params = [ ]
		params.append( ('client', self._clientId.encode('utf-8')) )

		for (trackId, puid) in tracks2puids.iteritems():
			trackId = mbutils.extractUuid(trackId, 'track')
			params.append( ('puid', trackId + ' ' + puid) )

		encodedStr = urllib.urlencode(params, True)

		self._ws.post('track', '', encodedStr)
	
	def submitISRCs(self, tracks2isrcs):
		"""Submit track to ISRC mappings.

		The C{tracks2isrcs} parameter has to be a dictionary, with the
		keys being MusicBrainz track IDs (either as absolute URIs or
		in their 36 character ASCII representation) and the values
		being ISRCs (ASCII, 12 characters).

		Note that this method only works if a valid user name and
		password have been set. See the example in L{Query} on how
		to supply authentication data.

		@param tracks2isrcs: a dictionary mapping track IDs to ISRCs

		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid track or ISRCs
		@raise AuthenticationError: invalid user name and/or password
		"""
		params = [ ]

		for (trackId, isrc) in tracks2isrcs.iteritems():
			trackId = mbutils.extractUuid(trackId, 'track')
			params.append( ('isrc', trackId + ' ' + isrc) )

		encodedStr = urllib.urlencode(params, True)

		self._ws.post('track', '', encodedStr)

	def addToUserCollection(self, releases):
		"""Add releases to a user's collection.

		The releases parameter must be a list. It can contain either L{Release}
		objects or a string representing a MusicBrainz release ID (either as
		absolute URIs or in their 36 character ASCII representation).

		Adding a release that is already in the collection has no effect.

		@param releases: a list of releases to add to the user collection

		@raise ConnectionError: couldn't connect to server
		@raise AuthenticationError: invalid user name and/or password
		"""
		rels = []
		for release in releases:
			if isinstance(release, Release):
				rels.append(mbutils.extractUuid(release.id))
			else:
				rels.append(mbutils.extractUuid(release))
		encodedStr = urllib.urlencode({'add': ",".join(rels)}, True)
		self._ws.post('collection', '', encodedStr)

	def removeFromUserCollection(self, releases):
		"""Remove releases from a user's collection.

		The releases parameter must be a list. It can contain either L{Release}
		objects or a string representing a MusicBrainz release ID (either as
		absolute URIs or in their 36 character ASCII representation).

		Removing a release that is not in the collection has no effect.

		@param releases: a list of releases to remove from the user collection

		@raise ConnectionError: couldn't connect to server
		@raise AuthenticationError: invalid user name and/or password
		"""
		rels = []
		for release in releases:
			if isinstance(release, Release):
				rels.append(mbutils.extractUuid(release.id))
			else:
				rels.append(mbutils.extractUuid(release))
		encodedStr = urllib.urlencode({'remove': ",".join(rels)}, True)
		self._ws.post('collection', '', encodedStr)

	def getUserCollection(self, offset=0, maxitems=100):
		"""Get the releases that are in a user's collection
		
		A maximum of 100 items will be returned for any one call
		to this method. To fetch more than 100 items, use the offset
		parameter.

		@param offset: the offset to start fetching results from
		@param maxitems: the upper limit on items to return

		@return: a list of L{musicbrainz2.wsxml.ReleaseResult} objects

		@raise ConnectionError: couldn't connect to server
		@raise AuthenticationError: invalid user name and/or password
		"""
		params = { 'offset': offset, 'maxitems': maxitems }
		
		stream = self._ws.get('collection', '', filter=params)
		print stream
		try:
			parser = MbXmlParser()
			result = parser.parse(stream)
		except ParseError, e:
			raise ResponseError(str(e), e)
		
		return result.getReleaseResults()

	def submitUserTags(self, entityUri, tags):
		"""Submit folksonomy tags for an entity.

		Note that all previously existing tags from the authenticated
		user are replaced with the ones given to this method. Other
		users' tags are not affected.
		
		@param entityUri: a string containing an absolute MB ID
		@param tags: A list of either L{Tag <musicbrainz2.model.Tag>} objects
		             or strings

		@raise ValueError: invalid entityUri
		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID, entity or tags
		@raise AuthenticationError: invalid user name and/or password
		"""
		entity = mbutils.extractEntityType(entityUri)
		uuid = mbutils.extractUuid(entityUri, entity)
		params = (
			('type', 'xml'),
			('entity', entity),
			('id', uuid),
			('tags', ','.join([unicode(tag).encode('utf-8') for tag in tags]))
		)

		encodedStr = urllib.urlencode(params)

		self._ws.post('tag', '', encodedStr)


	def getUserTags(self, entityUri):
		"""Returns a list of folksonomy tags a user has applied to an entity.

		The given parameter has to be a fully qualified MusicBrainz ID, as
		returned by other library functions.
		
		Note that this method only works if a valid user name and
		password have been set. Only the tags the authenticated user
		applied to the entity will be returned. If username and/or
		password are incorrect, an AuthenticationError is raised.
		
		This method will return a list of L{Tag <musicbrainz2.model.Tag>}
		objects.
		
		@param entityUri: a string containing an absolute MB ID
		
		@raise ValueError: invalid entityUri
  		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or entity
		@raise AuthenticationError: invalid user name and/or password
		"""
		entity = mbutils.extractEntityType(entityUri)
		uuid = mbutils.extractUuid(entityUri, entity)
		params = { 'entity': entity, 'id': uuid }
		
		stream = self._ws.get('tag', '', filter=params)
		try:
			parser = MbXmlParser()
			result = parser.parse(stream)
		except ParseError, e:
			raise ResponseError(str(e), e)
		
		return result.getTagList()

	def submitUserRating(self, entityUri, rating):
		"""Submit rating for an entity.

		Note that all previously existing rating from the authenticated
		user are replaced with the one given to this method. Other
		users' ratings are not affected.
		
		@param entityUri: a string containing an absolute MB ID
		@param rating: A L{Rating <musicbrainz2.model.Rating>} object
		             or integer

		@raise ValueError: invalid entityUri
		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID, entity or tags
		@raise AuthenticationError: invalid user name and/or password
		"""
		entity = mbutils.extractEntityType(entityUri)
		uuid = mbutils.extractUuid(entityUri, entity)
		params = (
			('type', 'xml'),
			('entity', entity),
			('id', uuid),
			('rating', unicode(rating).encode('utf-8'))
		)

		encodedStr = urllib.urlencode(params)

		self._ws.post('rating', '', encodedStr)


	def getUserRating(self, entityUri):
		"""Return the rating a user has applied to an entity.

		The given parameter has to be a fully qualified MusicBrainz
		ID, as returned by other library functions.
		
		Note that this method only works if a valid user name and
		password have been set. Only the rating the authenticated user
		applied to the entity will be returned. If username and/or
		password are incorrect, an AuthenticationError is raised.
		
		This method will return a L{Rating <musicbrainz2.model.Rating>}
		object.
		
		@param entityUri: a string containing an absolute MB ID
		
		@raise ValueError: invalid entityUri
  		@raise ConnectionError: couldn't connect to server
		@raise RequestError: invalid ID or entity
		@raise AuthenticationError: invalid user name and/or password
		"""
		entity = mbutils.extractEntityType(entityUri)
		uuid = mbutils.extractUuid(entityUri, entity)
		params = { 'entity': entity, 'id': uuid }
		
		stream = self._ws.get('rating', '', filter=params)
		try:
			parser = MbXmlParser()
			result = parser.parse(stream)
		except ParseError, e:
			raise ResponseError(str(e), e)
		
		return result.getRating()

	def submitCDStub(self, cdstub):
		"""Submit a CD Stub to the database.

		The number of tracks added to the CD Stub must match the TOC and DiscID
		otherwise the submission wil fail. The submission will also fail if 
		the Disc ID is already in the MusicBrainz database.

		This method will only work if no user name and password are set.

		@param cdstub: a L{CDStub} object to submit
		
		@raise RequestError: Missmatching TOC/Track information or the
		       the CD Stub already exists or the Disc ID already exists
		"""
		assert self._clientId is not None, 'Please supply a client ID'
		disc = cdstub._disc
		params = [ ]
		params.append( ('client', self._clientId.encode('utf-8')) )
		params.append( ('discid', disc.id) )
		params.append( ('title', cdstub.title) )
		params.append( ('artist', cdstub.artist) )
		if cdstub.barcode != "":
			params.append( ('barcode', cdstub.barcode) )
		if cdstub.comment != "":
			params.append( ('comment', cdstub.comment) )

		trackind = 0
		for track,artist in cdstub.tracks:
			params.append( ('track%d' % trackind, track) )
			if artist != "":
				params.append( ('artist%d' % trackind, artist) )

			trackind += 1

		toc = "%d %d %d " % (disc.firstTrackNum, disc.lastTrackNum, disc.sectors)
	        toc = toc + ' '.join( map(lambda x: str(x[0]), disc.getTracks()) )

		params.append( ('toc', toc) )

		encodedStr = urllib.urlencode(params)
		self._ws.post('release', '', encodedStr)

def _createIncludes(tagMap):
	selected = filter(lambda x: x[1] == True, tagMap.items())
	return map(lambda x: x[0], selected)

def _createParameters(params):
	"""Remove (x, None) tuples and encode (x, str/unicode) to utf-8."""
	ret = [ ]
	for p in params:
		if isinstance(p[1], (str, unicode)):
			ret.append( (p[0], p[1].encode('utf-8')) )
		elif p[1] is not None:
			ret.append(p)

	return ret

def _paramsValid(params):
	"""Check if the query parameter collides with other parameters."""
	tmp = [ ]
	for name, value in params:
		if value is not None and name not in ('offset', 'limit'):
			tmp.append(name)

	if 'query' in tmp and len(tmp) > 1:
		return False
	else:
		return True

if __name__ == '__main__':
	import doctest
	doctest.testmod()

# EOF
