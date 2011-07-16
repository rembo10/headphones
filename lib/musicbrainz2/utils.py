"""Various utilities to simplify common tasks.

This module contains helper functions to make common tasks easier.

@author: Matthias Friedrich <matt@mafr.de>
"""
__revision__ = '$Id: utils.py 11853 2009-07-21 09:26:50Z luks $'

import re
import urlparse
import os.path

__all__ = [
	'extractUuid', 'extractFragment', 'extractEntityType',
	'getReleaseTypeName', 'getCountryName', 'getLanguageName',
	'getScriptName',
]


# A pattern to split the path part of an absolute MB URI.
PATH_PATTERN = '^/(artist|release|track|label|release-group)/([^/]*)$'


def extractUuid(uriStr, resType=None):
	"""Extract the UUID part from a MusicBrainz identifier.

	This function takes a MusicBrainz ID (an absolute URI) as the input
	and returns the UUID part of the URI, thus turning it into a relative
	URI. If C{uriStr} is None or a relative URI, then it is returned
	unchanged.

	The C{resType} parameter can be used for error checking. Set it to
	'artist', 'release', or 'track' to make sure C{uriStr} is a
	syntactically valid MusicBrainz identifier of the given resource
	type. If it isn't, a C{ValueError} exception is raised.
	This error checking only works if C{uriStr} is an absolute URI, of
	course.

	Example:

	>>> from musicbrainz2.utils import extractUuid
	>>>  extractUuid('http://musicbrainz.org/artist/c0b2500e-0cef-4130-869d-732b23ed9df5', 'artist')
	'c0b2500e-0cef-4130-869d-732b23ed9df5'
	>>>

	@param uriStr: a string containing a MusicBrainz ID (an URI), or None
	@param resType: a string containing a resource type

	@return: a string containing a relative URI, or None

	@raise ValueError: the given URI is no valid MusicBrainz ID
	"""
	if uriStr is None:
		return None

	(scheme, netloc, path) = urlparse.urlparse(uriStr)[:3]

	if scheme == '':
		return uriStr	# no URI, probably already the UUID

	if scheme != 'http' or netloc != 'musicbrainz.org':
		raise ValueError('%s is no MB ID.' % uriStr)

	m = re.match(PATH_PATTERN, path)

	if m:
		if resType is None:
			return m.group(2)
		else:
			if m.group(1) == resType:
				return m.group(2)
			else:
				raise ValueError('expected "%s" Id' % resType)
	else:
		raise ValueError('%s is no valid MB ID.' % uriStr)


def extractFragment(uriStr, uriPrefix=None):
	"""Extract the fragment part from a URI.

	If C{uriStr} is None or no absolute URI, then it is returned unchanged.

	The C{uriPrefix} parameter can be used for error checking. If C{uriStr}
	is an absolute URI, then the function checks if it starts with
	C{uriPrefix}. If it doesn't, a C{ValueError} exception is raised.

	@param uriStr: a string containing an absolute URI
	@param uriPrefix: a string containing an URI prefix

	@return: a string containing the fragment, or None

	@raise ValueError: the given URI doesn't start with C{uriPrefix}
	"""
	if uriStr is None:
		return None

	(scheme, netloc, path, params, query, frag) = urlparse.urlparse(uriStr)
	if scheme == '':
		return uriStr # this is no URI

	if uriPrefix is None or uriStr.startswith(uriPrefix):
		return frag
	else:
		raise ValueError("prefix doesn't match URI %s" % uriStr)


def extractEntityType(uriStr):
	"""Returns the entity type an entity URI is referring to.

	@param uriStr: a string containing an absolute entity URI

	@return: a string containing 'artist', 'release', 'track', or 'label'

	@raise ValueError: if the given URI is no valid MusicBrainz ID
	"""
	if uriStr is None:
		raise ValueError('None is no valid entity URI')

	(scheme, netloc, path) = urlparse.urlparse(uriStr)[:3]

	if scheme == '':
		raise ValueError('%s is no absolute MB ID.' % uriStr)

	if scheme != 'http' or netloc != 'musicbrainz.org':
		raise ValueError('%s is no MB ID.' % uriStr)

	m = re.match(PATH_PATTERN, path)

	if m:
		return m.group(1)
	else:
		raise ValueError('%s is no valid MB ID.' % uriStr)


def getReleaseTypeName(releaseType):
	"""Returns the name of a release type URI.

	@param releaseType: a string containing a release type URI

	@return: a string containing a printable name for the release type

	@see: L{musicbrainz2.model.Release}
	"""
	from lib.musicbrainz2.data.releasetypenames import releaseTypeNames
	return releaseTypeNames.get(releaseType)


def getCountryName(id_):
	"""Returns a country's name based on an ISO-3166 country code.

	The country table this function is based on has been modified for
	MusicBrainz purposes by using the extension mechanism defined in
	ISO-3166. All IDs are still valid ISO-3166 country codes, but some
	IDs have been added to include historic countries and some of the
	country names have been modified to make them better suited for
	display purposes.

	If the country ID is not found, None is returned. This may happen
	for example, when new countries are added to the MusicBrainz web
	service which aren't known to this library yet.

	@param id_: a two-letter upper case string containing an ISO-3166 code

	@return: a string containing the country's name, or None

	@see: L{musicbrainz2.model}
	"""
	from musicbrainz2.data.countrynames import countryNames
	return countryNames.get(id_)


def getLanguageName(id_):
	"""Returns a language name based on an ISO-639-2/T code.

	This function uses a subset of the ISO-639-2/T code table to map
	language IDs (terminologic, not bibliographic ones!) to names.

	@param id_: a three-letter upper case string containing an ISO-639-2/T code

	@return: a string containing the language's name, or None

	@see: L{musicbrainz2.model}
	"""
	from musicbrainz2.data.languagenames import languageNames
	return languageNames.get(id_)


def getScriptName(id_):
	"""Returns a script name based on an ISO-15924 code.

	This function uses a subset of the ISO-15924 code table to map
	script IDs to names.

	@param id_: a four-letter string containing an ISO-15924 script code

	@return: a string containing the script's name, or None

	@see: L{musicbrainz2.model}
	"""
	from musicbrainz2.data.scriptnames import scriptNames
	return scriptNames.get(id_)


# EOF
