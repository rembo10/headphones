"""A parser for the Music Metadata XML Format (MMD).

This module contains L{MbXmlParser}, which parses the U{Music Metadata XML
Format (MMD) <http://musicbrainz.org/development/mmd/>} returned by the
MusicBrainz webservice. 

There are also DOM helper functions in this module used by the parser which
probably aren't useful to users.
"""
__revision__ = '$Id: wsxml.py 12028 2009-09-01 13:15:50Z matt $'

import re
import logging
import urlparse
import xml.dom.minidom
import xml.sax.saxutils as saxutils 
from xml.parsers.expat import ExpatError
from xml.dom import DOMException

import lib.musicbrainz2.utils as mbutils
import lib.musicbrainz2.model as model
from lib.musicbrainz2.model import NS_MMD_1, NS_REL_1, NS_EXT_1

__all__ = [
	'DefaultFactory', 'Metadata', 'ParseError',
	'MbXmlParser', 'MbXmlWriter',
	'AbstractResult',
	'ArtistResult', 'ReleaseResult', 'TrackResult', 'LabelResult',
	'ReleaseGroupResult'
]


class DefaultFactory(object):
	"""A factory to instantiate classes from the domain model. 

	This factory may be used to create objects from L{musicbrainz2.model}.
	"""
	def newArtist(self): return model.Artist()
	def newRelease(self): return model.Release()
	def newReleaseGroup(self): return model.ReleaseGroup()
	def newTrack(self): return model.Track()
	def newRelation(self): return model.Relation()
	def newReleaseEvent(self): return model.ReleaseEvent()
	def newDisc(self): return model.Disc()
	def newArtistAlias(self): return model.ArtistAlias()
	def newUser(self): return model.User()
	def newLabel(self): return model.Label()
	def newLabelAlias(self): return model.LabelAlias()
	def newTag(self): return model.Tag()
	def newRating(self): return model.Rating()


class ParseError(Exception):
	"""Exception to be thrown if a parse error occurs.

	The C{'msg'} attribute contains a printable error message, C{'reason'}
	is the lower level exception that was raised.
	"""

	def __init__(self, msg='Parse Error', reason=None):
		Exception.__init__(self)
		self.msg = msg
		self.reason = reason

	def __str__(self):
		return self.msg


class Metadata(object):
	"""Represents a parsed Music Metadata XML document.

	The Music Metadata XML format is very flexible and may contain a
	diverse set of data (e.g. an artist, a release and a list of tracks),
	but usually only a small subset is used (either an artist, a release
	or a track, or a lists of objects from one class).

	@see: L{MbXmlParser} for reading, and L{MbXmlWriter} for writing
		Metadata objects
	"""
	def __init__(self):
		self._artist = None
		self._release = None
		self._track = None
		self._label = None
		self._releaseGroup = None
		self._artistResults = [ ]
		self._artistResultsOffset = None
		self._artistResultsCount = None
		self._releaseResults = [ ]
		self._releaseResultsOffset = None
		self._releaseResultsCount = None
		self._releaseGroupResults = [ ]
		self._releaseGroupResultsOffset = None
		self._releaseGroupResultsCount = None
		self._trackResults = [ ]
		self._trackResultsOffset = None
		self._trackResultsCount = None
		self._labelResults = [ ]
		self._labelResultsOffset = None
		self._labelResultsCount = None
		self._tagList = [ ]
		self._rating = None
		self._userList = [ ]

	def getArtist(self):
		return self._artist

	def setArtist(self, artist):
		self._artist = artist

	artist = property(getArtist, setArtist, doc='An Artist object.')
	
	def getLabel(self):
		return self._label
	
	def setLabel(self, label):
		self._label = label
	
	label = property(getLabel, setLabel, doc='A Label object.')

	def getRelease(self):
		return self._release

	def setRelease(self, release):
		self._release = release

	release = property(getRelease, setRelease, doc='A Release object.')

	def getReleaseGroup(self):
		return self._releaseGroup

	def setReleaseGroup(self, releaseGroup):
		self._releaseGroup = releaseGroup

	releaseGroup = property(getReleaseGroup, setReleaseGroup)

	def getTrack(self):
		return self._track

	def setTrack(self, track):
		self._track = track

	track = property(getTrack, setTrack, doc='A Track object.')

	def getArtistResults(self):
		"""Returns an artist result list. 

		@return: a list of L{ArtistResult} objects.
		"""
		return self._artistResults

	artistResults = property(getArtistResults,
		doc='A list of ArtistResult objects.')

	def getArtistResultsOffset(self):
		"""Returns the offset of the artist result list.

		The offset is used for paging through the result list. It
		is zero-based.

		@return: an integer containing the offset, or None

		@see: L{getArtistResults}, L{getArtistResultsCount}
		"""
		return self._artistResultsOffset

	def setArtistResultsOffset(self, value):
		"""Sets the offset of the artist result list.

		@param value: an integer containing the offset, or None

		@see: L{getArtistResultsOffset}
		"""
		self._artistResultsOffset = value

	artistResultsOffset = property(
		getArtistResultsOffset, setArtistResultsOffset,
		doc='The offset of the artist results.')

	def getArtistResultsCount(self):
		"""Returns the total number of results available.
	
		This may or may not match with the number of elements that
		L{getArtistResults} returns. If the count is higher than
		the list, it indicates that the list is incomplete.

		@return: an integer containing the count, or None

		@see: L{setArtistResultsCount}, L{getArtistResultsOffset}
		"""
		return self._artistResultsCount

	def setArtistResultsCount(self, value):
		"""Sets the total number of available results.

		@param value: an integer containing the count, or None

		@see: L{getArtistResults}, L{setArtistResultsOffset}
		"""
		self._artistResultsCount = value

	artistResultsCount = property(
		getArtistResultsCount, setArtistResultsCount,
		doc='The total number of artists results.')

	def getLabelResults(self):
		"""Returns a label result list.
		
		@return: a list of L{LabelResult} objects.
		"""
		return self._labelResults
	
	labelResults = property(getLabelResults,
		doc='A list of LabelResult objects')

	def getLabelResultsOffset(self):
		"""Returns the offset of the label result list.

		The offset is used for paging through the result list. It
		is zero-based.

		@return: an integer containing the offset, or None

		@see: L{getLabelResults}, L{getLabelResultsCount}
		"""
		return self._labelResultsOffset

	def setLabelResultsOffset(self, value):
		"""Sets the offset of the label result list.

		@param value: an integer containing the offset, or None

		@see: L{getLabelResultsOffset}
		"""
		self._labelResultsOffset = value

	labelResultsOffset = property(
		getLabelResultsOffset, setLabelResultsOffset,
		doc='The offset of the label results.')

	def getLabelResultsCount(self):
		"""Returns the total number of results available.
	
		This may or may not match with the number of elements that
		L{getLabelResults} returns. If the count is higher than
		the list, it indicates that the list is incomplete.

		@return: an integer containing the count, or None

		@see: L{setLabelResultsCount}, L{getLabelResultsOffset}
		"""
		return self._labelResultsCount

	def setLabelResultsCount(self, value):
		"""Sets the total number of available results.

		@param value: an integer containing the count, or None

		@see: L{getLabelResults}, L{setLabelResultsOffset}
		"""
		self._labelResultsCount = value

	labelResultsCount = property(
		getLabelResultsCount, setLabelResultsCount,
		doc='The total number of label results.')

	def getReleaseResults(self):
		"""Returns a release result list. 

		@return: a list of L{ReleaseResult} objects.
		"""
		return self._releaseResults

	releaseResults = property(getReleaseResults,
		doc='A list of ReleaseResult objects.')

	def getReleaseResultsOffset(self):
		"""Returns the offset of the release result list.

		The offset is used for paging through the result list. It
		is zero-based.

		@return: an integer containing the offset, or None

		@see: L{getReleaseResults}, L{getReleaseResultsCount}
		"""
		return self._releaseResultsOffset

	def setReleaseResultsOffset(self, value):
		"""Sets the offset of the release result list.

		@param value: an integer containing the offset, or None

		@see: L{getReleaseResultsOffset}
		"""
		self._releaseResultsOffset = value

	releaseResultsOffset = property(
		getReleaseResultsOffset, setReleaseResultsOffset,
		doc='The offset of the release results.')

	def getReleaseResultsCount(self):
		"""Returns the total number of results available.
	
		This may or may not match with the number of elements that
		L{getReleaseResults} returns. If the count is higher than
		the list, it indicates that the list is incomplete.

		@return: an integer containing the count, or None

		@see: L{setReleaseResultsCount}, L{getReleaseResultsOffset}
		"""
		return self._releaseResultsCount

	def setReleaseResultsCount(self, value):
		"""Sets the total number of available results.

		@param value: an integer containing the count, or None

		@see: L{getReleaseResults}, L{setReleaseResultsOffset}
		"""
		self._releaseResultsCount = value

	releaseResultsCount = property(
		getReleaseResultsCount, setReleaseResultsCount,
		doc='The total number of release results.')

	def getReleaseGroupResults(self):
		"""Returns a release group result list.

		@return: a list of L{ReleaseGroupResult} objects.
		"""
		return self._releaseGroupResults

	releaseGroupResults = property(getReleaseGroupResults,
		doc = 'A list of ReleaseGroupResult objects.')

	def getReleaseGroupResultsOffset(self):
		"""Returns the offset of the release group result list.

		The offset is used for paging through the result list.  It
		is zero-based.

		@return: an integer containing the offset, or None.

		@see: L{getReleaseGroupResults}, L{getReleaseGroupResultsCount}
		"""
		return self._releaseGroupResultsOffset

	def setReleaseGroupResultsOffset(self, value):
		"""Sets the offset of the release group result list.

		@param value: an integer containing the offset, or None

		@see: L{getReleaseGroupResultsOffset}
		"""
		self._releaseGroupResultsOffset = value

	releaseGroupResultsOffset = property(
		getReleaseGroupResultsOffset, setReleaseGroupResultsOffset,
		doc='The offset of the release group results.')

	def getReleaseGroupResultsCount(self):
		"""Returns the total number of results available.

		This may or may not match with the number of elements that
		L{getReleaseGroupResults} returns. If the count is higher than
		the list, it indicates that the list is incomplete.

		@return: an integer containing the count, or None

		@see: L{setReleaseGroupResultsCount}, L{getReleaseGroupResultsOffset}
		"""
		return self._releaseGroupResultsCount

	def setReleaseGroupResultsCount(self, value):
		"""Sets the total number of available results.

		@param value: an integer containing the count, or None

		@see: L{getReleaseGroupResults}, L{setReleaseGroupResultsOffset}
		"""
		self._releaseGroupResultsCount = value

	releaseGroupResultsCount = property(
		getReleaseGroupResultsCount, setReleaseGroupResultsCount,
		doc='The total number of release group results.')

	def getTrackResults(self):
		"""Returns a track result list. 

		@return: a list of L{TrackResult} objects.
		"""
		return self._trackResults

	trackResults = property(getTrackResults,
		doc='A list of TrackResult objects.')

	def getTrackResultsOffset(self):
		"""Returns the offset of the track result list.

		The offset is used for paging through the result list. It
		is zero-based.

		@return: an integer containing the offset, or None

		@see: L{getTrackResults}, L{getTrackResultsCount}
		"""
		return self._trackResultsOffset

	def setTrackResultsOffset(self, value):
		"""Sets the offset of the track result list.

		@param value: an integer containing the offset, or None

		@see: L{getTrackResultsOffset}
		"""
		self._trackResultsOffset = value

	trackResultsOffset = property(
		getTrackResultsOffset, setTrackResultsOffset,
		doc='The offset of the track results.')

	def getTrackResultsCount(self):
		"""Returns the total number of results available.
	
		This may or may not match with the number of elements that
		L{getTrackResults} returns. If the count is higher than
		the list, it indicates that the list is incomplete.

		@return: an integer containing the count, or None

		@see: L{setTrackResultsCount}, L{getTrackResultsOffset}
		"""
		return self._trackResultsCount

	def setTrackResultsCount(self, value):
		"""Sets the total number of available results.

		@param value: an integer containing the count, or None

		@see: L{getTrackResults}, L{setTrackResultsOffset}
		"""
		self._trackResultsCount = value

	trackResultsCount = property(
		getTrackResultsCount, setTrackResultsCount,
		doc='The total number of track results.')


	def getTagList(self):
		"""Returns a list of tags.

		@return: a list of L{model.Tag} objects
		"""
		return self._tagList

	tagResults = property(getTagList,
		doc='A list of Tag objects.')

	def getRating(self):
		"""Returns the rating.

		@return: rating object
		"""
		return self._rating

	def setRating(self, value):
		"""Sets the rating.

		@param value: a L{model.Rating} object
		"""
		self._rating = value

	rating = property(getRating, setRating, doc='A Rating object.')


	# MusicBrainz extension to the schema
	def getUserList(self):
		"""Returns a list of users.

		@return: a list of L{model.User} objects

		@note: This is a MusicBrainz extension.
		"""
		return self._userList

	userResults = property(getUserList,
		doc='A list of User objects.')


class AbstractResult(object):
	"""The abstract representation of a result.

	A result is an instance of some kind (Artist, Release, ...)
	associated with a score.
	"""

	def __init__(self, score):
		self._score = score

	def getScore(self):
		"""Returns the result score.

		The score indicates how good this result matches the search
		parameters. The higher the value, the better the match.

		@return: an int between 0 and 100 (both inclusive), or None
		"""
		return self._score

	def setScore(self, score):
		self._score = score

	score = property(getScore, setScore, doc='The relevance score.')


class ArtistResult(AbstractResult):
	"""Represents an artist result.

	An ArtistResult consists of a I{score} and an artist. The score is a
	number between 0 and 100, where a higher number indicates a better
	match.
	"""
	def __init__(self, artist, score):
		super(ArtistResult, self).__init__(score)
		self._artist = artist

	def getArtist(self):
		"""Returns an Artist object.

		@return: a L{musicbrainz2.model.Artist} object
		"""
		return self._artist

	def setArtist(self, artist):
		self._artist = artist

	artist = property(getArtist, setArtist, doc='An Artist object.')


class ReleaseResult(AbstractResult):
	"""Represents a release result.

	A ReleaseResult consists of a I{score} and a release. The score is a
	number between 0 and 100, where a higher number indicates a better
	match.
	"""
	def __init__(self, release, score):
		super(ReleaseResult, self).__init__(score)
		self._release = release

	def getRelease(self):
		"""Returns a Release object.

		@return: a L{musicbrainz2.model.Release} object
		"""
		return self._release

	def setRelease(self, release):
		self._release = release

	release = property(getRelease, setRelease, doc='A Release object.')

class ReleaseGroupResult(AbstractResult):
	"""Represents a release group result.

	A ReleaseGroupResult consists of a I{score} and a release group.  The
	score is a number between 0 and 100, where a higher number indicates
	a better match.
	"""
	def __init__(self, releaseGroup, score):
		super(ReleaseGroupResult, self).__init__(score)
		self._releaseGroup = releaseGroup

	def getReleaseGroup(self):
		"""Returns a ReleaseGroup object.

		@return: a L{musicbrainz2.model.ReleaseGroup} object
		"""
		return self._releaseGroup

	def setReleaseGroup(self, value):
		self._releaseGroup = value

	releaseGroup = property(getReleaseGroup, setReleaseGroup, doc='A ReleaseGroup object.')

class TrackResult(AbstractResult):
	"""Represents a track result.

	A TrackResult consists of a I{score} and a track. The score is a
	number between 0 and 100, where a higher number indicates a better
	match.
	"""
	def __init__(self, track, score):
		super(TrackResult, self).__init__(score)
		self._track = track

	def getTrack(self):
		"""Returns a Track object.

		@return: a L{musicbrainz2.model.Track} object
		"""
		return self._track

	def setTrack(self, track):
		self._track = track

	track = property(getTrack, setTrack, doc='A Track object.')


class LabelResult(AbstractResult):
	"""Represents a label result.

	An LabelResult consists of a I{score} and a label. The score is a
	number between 0 and 100, where a higher number indicates a better
	match.
	"""
	def __init__(self, label, score):
		super(LabelResult, self).__init__(score)
		self._label = label

	def getLabel(self):
		"""Returns a Label object.

		@return: a L{musicbrainz2.model.Label} object
		"""
		return self._label

	def setLabel(self, label):
		self._label = label

	label = property(getLabel, setLabel, doc='A Label object.')


class MbXmlParser(object):
	"""A parser for the Music Metadata XML format.

	This parser supports all basic features and extensions defined by
	MusicBrainz, including unlimited document nesting. By default it
	reads an XML document from a file-like object (stream) and returns
	an object tree representing the document using classes from
	L{musicbrainz2.model}.

	The implementation tries to be as permissive as possible. Invalid
	contents are skipped, but documents have to be well-formed and using
	the correct namespace. In case of unrecoverable errors, a L{ParseError}
	exception is raised.

	@see: U{The Music Metadata XML Format
		<http://musicbrainz.org/development/mmd/>}
	"""

	def __init__(self, factory=DefaultFactory()):
		"""Constructor.

		The C{factory} parameter has be an instance of L{DefaultFactory}
		or a subclass of it. It is used by L{parse} to obtain objects
		from L{musicbrainz2.model} to build resulting object tree.
		If you supply your own factory, you have to make sure all
		returned objects have the same interface as their counterparts
		from L{musicbrainz2.model}.

		@param factory: an object factory 
		"""
		self._log = logging.getLogger(str(self.__class__))
		self._factory = factory

	def parse(self, inStream):
		"""Parses the MusicBrainz web service XML.

		Returns a L{Metadata} object representing the parsed XML or
		raises a L{ParseError} exception if the data was malformed.
		The parser tries to be liberal and skips invalid content if
		possible.

		Note that an L{IOError} may be raised if there is a problem
		reading C{inStream}.

		@param inStream: a file-like object
		@return: a L{Metadata} object (never None)
		@raise ParseError: if the document is not valid
		@raise IOError: if reading from the stream failed
		"""

		try:
			doc = xml.dom.minidom.parse(inStream)

			# Try to find the root element. If this isn't an mmd
			# XML file or the namespace is wrong, this will fail.
			elems = doc.getElementsByTagNameNS(NS_MMD_1, 'metadata')

			if len(elems) != 0:
				md = self._createMetadata(elems[0])
			else:
				msg = 'cannot find root element mmd:metadata'
				self._log.debug('ParseError: ' + msg)
				raise ParseError(msg)

			doc.unlink()

			return md
		except ExpatError, e:
			self._log.debug('ExpatError: ' + str(e))
			raise ParseError(msg=str(e), reason=e)
		except DOMException, e:
			self._log.debug('DOMException: ' + str(e))
			raise ParseError(msg=str(e), reason=e)
			

	def _createMetadata(self, metadata):
		md = Metadata()

		for node in _getChildElements(metadata):
			if _matches(node, 'artist'):
				md.artist = self._createArtist(node)
			elif _matches(node, 'release'):
				md.release = self._createRelease(node)
			elif _matches(node, 'release-group'):
				md.releaseGroup = self._createReleaseGroup(node)
			elif _matches(node, 'track'):
				md.track = self._createTrack(node)
			elif _matches(node, 'label'):
				md.label = self._createLabel(node)
			elif _matches(node, 'artist-list'):
				(offset, count) = self._getListAttrs(node)
				md.artistResultsOffset = offset
				md.artistResultsCount = count
				self._addArtistResults(node, md.getArtistResults())
			elif _matches(node, 'release-list'):
				(offset, count) = self._getListAttrs(node)
				md.releaseResultsOffset = offset
				md.releaseResultsCount = count
				self._addReleaseResults(node, md.getReleaseResults())
			elif _matches(node, 'release-group-list'):
				(offset, count) = self._getListAttrs(node)
				md.releaseGroupResultsOffset = offset
				md.releaseGroupResultsCount = count
				self._addReleaseGroupResults(node, md.getReleaseGroupResults())
			elif _matches(node, 'track-list'):
				(offset, count) = self._getListAttrs(node)
				md.trackResultsOffset = offset
				md.trackResultsCount = count
				self._addTrackResults(node, md.getTrackResults())
			elif _matches(node, 'label-list'):
				(offset, count) = self._getListAttrs(node)
				md.labelResultsOffset = offset
				md.labelResultsCount = count
				self._addLabelResults(node, md.getLabelResults())
			elif _matches(node, 'tag-list'):
				self._addTagsToList(node, md.getTagList())
			elif _matches(node, 'user-list', NS_EXT_1):
				self._addUsersToList(node, md.getUserList())

		return md


	def _addArtistResults(self, listNode, resultList):
		for c in _getChildElements(listNode):
			artist = self._createArtist(c)
			score = _getIntAttr(c, 'score', 0, 100, ns=NS_EXT_1)
			if artist is not None:
				resultList.append(ArtistResult(artist, score))

	def _addReleaseResults(self, listNode, resultList):
		for c in _getChildElements(listNode):
			release = self._createRelease(c)
			score = _getIntAttr(c, 'score', 0, 100, ns=NS_EXT_1)
			if release is not None:
				resultList.append(ReleaseResult(release, score))

	def _addReleaseGroupResults(self, listNode, resultList):
		for c in _getChildElements(listNode):
			releaseGroup = self._createReleaseGroup(c)
			score = _getIntAttr(c, 'score', 0, 100, ns=NS_EXT_1)
			if releaseGroup is not None:
				resultList.append(ReleaseGroupResult(releaseGroup, score))

	def _addTrackResults(self, listNode, resultList):
		for c in _getChildElements(listNode):
			track = self._createTrack(c)
			score = _getIntAttr(c, 'score', 0, 100, ns=NS_EXT_1)
			if track is not None:
				resultList.append(TrackResult(track, score))

	def _addLabelResults(self, listNode, resultList):
		for c in _getChildElements(listNode):
			label = self._createLabel(c)
			score = _getIntAttr(c, 'score', 0, 100, ns=NS_EXT_1)
			if label is not None:
				resultList.append(LabelResult(label, score))

	def _addReleasesToList(self, listNode, resultList):
		self._addToList(listNode, resultList, self._createRelease)

	def _addReleaseGroupsToList(self, listNode, resultList):
		self._addToList(listNode, resultList, self._createReleaseGroup)

	def _addTracksToList(self, listNode, resultList):
		self._addToList(listNode, resultList, self._createTrack)

	def _addUsersToList(self, listNode, resultList):
		self._addToList(listNode, resultList, self._createUser)

	def _addTagsToList(self, listNode, resultList):
		self._addToList(listNode, resultList, self._createTag)

	def _addTagsToEntity(self, listNode, entity):
		for node in _getChildElements(listNode):
			tag = self._createTag(node)
			entity.addTag(tag)

	def _addRatingToEntity(self, attrNode, entity):
		rating = self._createRating(attrNode)
		entity.setRating(rating)

	def _addToList(self, listNode, resultList, creator):
		for c in _getChildElements(listNode):
			resultList.append(creator(c))

	def _getListAttrs(self, listNode):
		offset = _getIntAttr(listNode, 'offset')
		count = _getIntAttr(listNode, 'count')
		return (offset, count)


	def _createArtist(self, artistNode):
		artist = self._factory.newArtist()
		artist.setId(_getIdAttr(artistNode, 'id', 'artist'))
		artist.setType(_getUriAttr(artistNode, 'type'))
		
		for node in _getChildElements(artistNode):
			if _matches(node, 'name'):
				artist.setName(_getText(node))
			elif _matches(node, 'sort-name'):
				artist.setSortName(_getText(node))
			elif _matches(node, 'disambiguation'):
				artist.setDisambiguation(_getText(node))
			elif _matches(node, 'life-span'):
				artist.setBeginDate(_getDateAttr(node, 'begin'))
				artist.setEndDate(_getDateAttr(node, 'end'))
			elif _matches(node, 'alias-list'):
				self._addArtistAliases(node, artist)
			elif _matches(node, 'release-list'):
				(offset, count) = self._getListAttrs(node)
				artist.setReleasesOffset(offset)
				artist.setReleasesCount(count)
				self._addReleasesToList(node, artist.getReleases())
			elif _matches(node, 'release-group-list'):
				(offset, count) = self._getListAttrs(node)
				artist.setReleaseGroupsOffset(offset)
				artist.setReleaseGroupsCount(count)
				self._addReleaseGroupsToList(node, artist.getReleaseGroups())
			elif _matches(node, 'relation-list'):
				self._addRelationsToEntity(node, artist)
			elif _matches(node, 'tag-list'):
				self._addTagsToEntity(node, artist)
			elif _matches(node, 'rating'):
				self._addRatingToEntity(node, artist)

		return artist

	def _createLabel(self, labelNode):
		label = self._factory.newLabel()
		label.setId(_getIdAttr(labelNode, 'id', 'label'))
		label.setType(_getUriAttr(labelNode, 'type'))
		
		for node in _getChildElements(labelNode):
			if _matches(node, 'name'):
				label.setName(_getText(node))
			if _matches(node, 'sort-name'):
				label.setSortName(_getText(node))
			elif _matches(node, 'disambiguation'):
				label.setDisambiguation(_getText(node))
			elif _matches(node, 'label-code'):
				label.setCode(_getText(node))
			elif _matches(node, 'country'):
				country = _getText(node, '^[A-Z]{2}$')
				label.setCountry(country)
			elif _matches(node, 'life-span'):
				label.setBeginDate(_getDateAttr(node, 'begin'))
				label.setEndDate(_getDateAttr(node, 'end'))
			elif _matches(node, 'alias-list'):
				self._addLabelAliases(node, label)
			elif _matches(node, 'tag-list'):
				self._addTagsToEntity(node, label)
			elif _matches(node, 'rating'):
				self._addRatingToEntity(node, label)

		return label

	def _createRelease(self, releaseNode):
		release = self._factory.newRelease()
		release.setId(_getIdAttr(releaseNode, 'id', 'release'))
		for t in _getUriListAttr(releaseNode, 'type'):
			release.addType(t)

		for node in _getChildElements(releaseNode):
			if _matches(node, 'title'):
				release.setTitle(_getText(node))
			elif _matches(node, 'text-representation'):
				lang = _getAttr(node, 'language', '^[A-Z]{3}$')
				release.setTextLanguage(lang)
				script = _getAttr(node, 'script', '^[A-Z][a-z]{3}$')
				release.setTextScript(script)
			elif _matches(node, 'asin'):
				release.setAsin(_getText(node))
			elif _matches(node, 'artist'):
				release.setArtist(self._createArtist(node))
			elif _matches(node, 'release-event-list'):
				self._addReleaseEvents(node, release)
			elif _matches(node, 'release-group'):
				release.setReleaseGroup(self._createReleaseGroup(node))
			elif _matches(node, 'disc-list'):
				self._addDiscs(node, release)
			elif _matches(node, 'track-list'):
				(offset, count) = self._getListAttrs(node)
				release.setTracksOffset(offset)
				release.setTracksCount(count)
				self._addTracksToList(node, release.getTracks())
			elif _matches(node, 'relation-list'):
				self._addRelationsToEntity(node, release)
			elif _matches(node, 'tag-list'):
				self._addTagsToEntity(node, release)
			elif _matches(node, 'rating'):
				self._addRatingToEntity(node, release)

		return release

	def _createReleaseGroup(self, node):
		rg = self._factory.newReleaseGroup()
		rg.setId(_getIdAttr(node, 'id', 'release-group'))
		rg.setType(_getUriAttr(node, 'type'))

		for child in _getChildElements(node):
			if _matches(child, 'title'):
				rg.setTitle(_getText(child))
			elif _matches(child, 'artist'):
				rg.setArtist(self._createArtist(child))
			elif _matches(child, 'release-list'):
				(offset, count) = self._getListAttrs(child)
				rg.setReleasesOffset(offset)
				rg.setReleasesCount(count)
				self._addReleasesToList(child, rg.getReleases())

		return rg

	def _addReleaseEvents(self, releaseListNode, release):
		for node in _getChildElements(releaseListNode):
			if _matches(node, 'event'):
				country = _getAttr(node, 'country', '^[A-Z]{2}$')
				date = _getDateAttr(node, 'date')
				catalogNumber = _getAttr(node, 'catalog-number')
				barcode = _getAttr(node, 'barcode')
				format = _getUriAttr(node, 'format')

				# The date attribute is mandatory. If it isn't present,
				# we don't add anything from this release event.
				if date is not None:
					event = self._factory.newReleaseEvent()
					event.setCountry(country)
					event.setDate(date)
					event.setCatalogNumber(catalogNumber)
					event.setBarcode(barcode)
					event.setFormat(format)
					
					for subNode in _getChildElements(node):
						if _matches(subNode, 'label'):
							event.setLabel(self._createLabel(subNode))
					
					release.addReleaseEvent(event)


	def _addDiscs(self, discIdListNode, release):
		for node in _getChildElements(discIdListNode):
			if _matches(node, 'disc') and node.hasAttribute('id'):
				d = self._factory.newDisc()
				d.setId(node.getAttribute('id'))
				d.setSectors(_getIntAttr(node, 'sectors', 0))
				release.addDisc(d)


	def _addArtistAliases(self, aliasListNode, artist):
		for node in _getChildElements(aliasListNode):
			if _matches(node, 'alias'):
				alias = self._factory.newArtistAlias()
				self._initializeAlias(alias, node)
				artist.addAlias(alias)


	def _addLabelAliases(self, aliasListNode, label):
		for node in _getChildElements(aliasListNode):
			if _matches(node, 'alias'):
				alias = self._factory.newLabelAlias()
				self._initializeAlias(alias, node)
				label.addAlias(alias)


	def _initializeAlias(self, alias, node):
		alias.setValue(_getText(node))
		alias.setType(_getUriAttr(node, 'type'))
		alias.setScript(_getAttr(node, 'script',
			'^[A-Z][a-z]{3}$'))


	def _createTrack(self, trackNode):
		track = self._factory.newTrack()
		track.setId(_getIdAttr(trackNode, 'id', 'track'))

		for node in _getChildElements(trackNode):
			if _matches(node, 'title'):
				track.setTitle(_getText(node))
			elif _matches(node, 'artist'):
				track.setArtist(self._createArtist(node))
			elif _matches(node, 'duration'):
				track.setDuration(_getPositiveIntText(node))
			elif _matches(node, 'release-list'):
				self._addReleasesToList(node, track.getReleases())
			elif _matches(node, 'puid-list'):
				self._addPuids(node, track)
			elif _matches(node, 'isrc-list'):
				self._addISRCs(node, track)
			elif _matches(node, 'relation-list'):
				self._addRelationsToEntity(node, track)
			elif _matches(node, 'tag-list'):
				self._addTagsToEntity(node, track)
			elif _matches(node, 'rating'):
				self._addRatingToEntity(node, track)

		return track

	# MusicBrainz extension
	def _createUser(self, userNode):
		user = self._factory.newUser()
		for t in _getUriListAttr(userNode, 'type', NS_EXT_1):
			user.addType(t)

		for node in _getChildElements(userNode):
			if _matches(node, 'name'):
				user.setName(_getText(node))
			elif _matches(node, 'nag', NS_EXT_1):
				user.setShowNag(_getBooleanAttr(node, 'show'))

		return user

	def _createRating(self, ratingNode):
		rating = self._factory.newRating()
		rating.value = _getText(ratingNode)
		rating.count = _getIntAttr(ratingNode, 'votes-count')
		return rating

	def _createTag(self, tagNode):
		tag = self._factory.newTag()
		tag.value = _getText(tagNode)
		tag.count = _getIntAttr(tagNode, 'count')
		return tag

	
	def _addPuids(self, puidListNode, track):
		for node in _getChildElements(puidListNode):
			if _matches(node, 'puid') and node.hasAttribute('id'):
				track.addPuid(node.getAttribute('id'))

	def _addISRCs(self, isrcListNode, track):
		for node in _getChildElements(isrcListNode):
			if _matches(node, 'isrc') and node.hasAttribute('id'):
				track.addISRC(node.getAttribute('id'))

	def _addRelationsToEntity(self, relationListNode, entity):
		targetType = _getUriAttr(relationListNode, 'target-type', NS_REL_1)

		if targetType is None:
			return

		for node in _getChildElements(relationListNode):
			if _matches(node, 'relation'):
				rel = self._createRelation(node, targetType)
				if rel is not None:
					entity.addRelation(rel)


	def _createRelation(self, relationNode, targetType):
		relation = self._factory.newRelation()

		relation.setType(_getUriAttr(relationNode, 'type', NS_REL_1))
		relation.setTargetType(targetType)
		resType = _getResourceType(targetType)
		relation.setTargetId(_getIdAttr(relationNode, 'target', resType))

		if relation.getType() is None \
				or relation.getTargetType() is None \
				or relation.getTargetId() is None:
			return None

		relation.setDirection(_getDirectionAttr(relationNode, 'direction'))
		relation.setBeginDate(_getDateAttr(relationNode, 'begin'))
		relation.setEndDate(_getDateAttr(relationNode, 'end'))

		for a in _getUriListAttr(relationNode, 'attributes', NS_REL_1):
			relation.addAttribute(a)

		target = None
		children = _getChildElements(relationNode)
		if len(children) > 0:
			node = children[0]
			if _matches(node, 'artist'):
				target = self._createArtist(node)	
			elif _matches(node, 'release'):
				target = self._createRelease(node)	
			elif _matches(node, 'track'):
				target = self._createTrack(node)	

		relation.setTarget(target)

		return relation


#
# XML output
#

class _XmlWriter(object):
	def __init__(self, outStream, indentAmount='  ', newline="\n"):
		self._out = outStream
		self._indentAmount = indentAmount
		self._stack = [ ]
		self._newline = newline

	def prolog(self, encoding='UTF-8', version='1.0'):
		pi = '<?xml version="%s" encoding="%s"?>' % (version, encoding)
		self._out.write(pi + self._newline)

	def start(self, name, attrs={ }):
		indent = self._getIndention()
		self._stack.append(name)
		self._out.write(indent + self._makeTag(name, attrs) + self._newline)

	def end(self):
		name = self._stack.pop()
		indent = self._getIndention()
		self._out.write('%s</%s>\n' % (indent, name))

	def elem(self, name, value, attrs={ }):
		# delete attributes with an unset value
		for (k, v) in attrs.items():
			if v is None or v == '':
				del attrs[k]

		if value is None or value == '':
			if len(attrs) == 0:
				return
			self._out.write(self._getIndention())
			self._out.write(self._makeTag(name, attrs, True) + '\n')
		else:
			escValue = saxutils.escape(value or '')
			self._out.write(self._getIndention())
			self._out.write(self._makeTag(name, attrs))
			self._out.write(escValue)
			self._out.write('</%s>\n' % name)

	def _getIndention(self):
		return self._indentAmount * len(self._stack)

	def _makeTag(self, name, attrs={ }, close=False):
		ret = '<' + name

		for (k, v) in attrs.iteritems():
			if v is not None:
				v = saxutils.quoteattr(str(v))
				ret += ' %s=%s' % (k, v)

		if close:
			return ret + '/>'
		else:
			return ret + '>'



class MbXmlWriter(object):
	"""Write XML in the Music Metadata XML format."""

	def __init__(self, indentAmount='  ', newline="\n"):
		"""Constructor.

		@param indentAmount: the amount of whitespace to use per level
		"""
		self._indentAmount = indentAmount
		self._newline = newline


	def write(self, outStream, metadata):
		"""Writes the XML representation of a Metadata object to a file.

		@param outStream: an open file-like object
		@param metadata: a L{Metadata} object
		"""
		xml = _XmlWriter(outStream, self._indentAmount, self._newline)

		xml.prolog()
		xml.start('metadata', {
			'xmlns': NS_MMD_1,
			'xmlns:ext': NS_EXT_1,
		})

		self._writeArtist(xml, metadata.getArtist())
		self._writeRelease(xml, metadata.getRelease())
		self._writeReleaseGroup(xml, metadata.getReleaseGroup())
		self._writeTrack(xml, metadata.getTrack())
		self._writeLabel(xml, metadata.getLabel())

		if len(metadata.getArtistResults()) > 0:
			xml.start('artist-list', {
				'offset': metadata.artistResultsOffset,
				'count': metadata.artistResultsCount,
			})
			for result in metadata.getArtistResults():
				self._writeArtist(xml, result.getArtist(),
					result.getScore())
			xml.end()

		if len(metadata.getReleaseResults()) > 0:
			xml.start('release-list', {
				'offset': metadata.releaseResultsOffset,
				'count': metadata.releaseResultsCount,
			})
			for result in metadata.getReleaseResults():
				self._writeRelease(xml, result.getRelease(),
					result.getScore())
			xml.end()

		if len(metadata.getReleaseGroupResults()) > 0:
			xml.start('release-group-list', {
				'offset': metadata.releaseGroupResultsOffset,
				'count': metadata.releaseGroupResultsCount
			})
			for result in metadata.getReleaseGroupResults():
				self._writeReleaseGroup(xml, result.getReleaseGroup(),
					result.getScore())
			xml.end()

		if len(metadata.getTrackResults()) > 0:
			xml.start('track-list', {
				'offset': metadata.trackResultsOffset,
				'count': metadata.trackResultsCount,
			})
			for result in metadata.getTrackResults():
				self._writeTrack(xml, result.getTrack(),
					result.getScore())
			xml.end()

		if len(metadata.getLabelResults()) > 0:
			xml.start('label-list', {
				'offset': metadata.labelResultsOffset,
				'count': metadata.labelResultsCount,
			})
			for result in metadata.getLabelResults():
				self._writeLabel(xml, result.getLabel(),
					result.getScore())
			xml.end()

		xml.end()


	def _writeArtist(self, xml, artist, score=None):
		if artist is None:
			return

		xml.start('artist', {
			'id': mbutils.extractUuid(artist.getId()),
			'type': mbutils.extractFragment(artist.getType()),
			'ext:score': score,
		})

		xml.elem('name', artist.getName())
		xml.elem('sort-name', artist.getSortName())
		xml.elem('disambiguation', artist.getDisambiguation())
		xml.elem('life-span', None, {
			'begin': artist.getBeginDate(),
			'end': artist.getEndDate(),
		})

		if len(artist.getAliases()) > 0:
			xml.start('alias-list')
			for alias in artist.getAliases():
				xml.elem('alias', alias.getValue(), {
					'type': alias.getType(),
					'script': alias.getScript(),
				})
			xml.end()

		if len(artist.getReleases()) > 0:
			xml.start('release-list')
			for release in artist.getReleases():
				self._writeRelease(xml, release)
			xml.end()

		if len(artist.getReleaseGroups()) > 0:
			xml.start('release-group-list')
			for releaseGroup in artist.getReleaseGroups():
				self._writeReleaseGroup(xml, releaseGroup)
			xml.end()

		self._writeRelationList(xml, artist)
		# TODO: extensions

		xml.end()


	def _writeRelease(self, xml, release, score=None):
		if release is None:
			return

		types = [mbutils.extractFragment(t) for t in release.getTypes()]
		typesStr = None
		if len(types) > 0:
			typesStr = ' '.join(types)

		xml.start('release', {
			'id': mbutils.extractUuid(release.getId()),
			'type': typesStr,
			'ext:score': score,
		})

		xml.elem('title', release.getTitle())
		xml.elem('text-representation', None, {
			'language': release.getTextLanguage(),
			'script': release.getTextScript()
		})
		xml.elem('asin', release.getAsin())

		self._writeArtist(xml, release.getArtist())
		self._writeReleaseGroup(xml, release.getReleaseGroup())

		if len(release.getReleaseEvents()) > 0:
			xml.start('release-event-list')
			for event in release.getReleaseEvents():
				self._writeReleaseEvent(xml, event)
			xml.end()

		if len(release.getDiscs()) > 0:
			xml.start('disc-list')
			for disc in release.getDiscs():
				xml.elem('disc', None, { 'id': disc.getId() })
			xml.end()

		if len(release.getTracks()) > 0:
			# TODO: count attribute
			xml.start('track-list', {
				'offset': release.getTracksOffset()
			})
			for track in release.getTracks():
				self._writeTrack(xml, track)
			xml.end()
		
		self._writeRelationList(xml, release)
		# TODO: extensions

		xml.end()

	def _writeReleaseGroup(self, xml, rg, score = None):
		if rg is None:
			return

		xml.start('release-group', {
			'id': mbutils.extractUuid(rg.getId()),
			'type': mbutils.extractFragment(rg.getType()),
			'ext:score': score,
		})

		xml.elem('title', rg.getTitle())
		self._writeArtist(xml, rg.getArtist())

		if len(rg.getReleases()) > 0:
			xml.start('release-list')
			for rel in rg.getReleases():
				self._writeRelease(xml, rel)
			xml.end()

		xml.end()

	def _writeReleaseEvent(self, xml, event):
		xml.start('event', {
			'country': event.getCountry(),
			'date': event.getDate(),
			'catalog-number': event.getCatalogNumber(),
			'barcode': event.getBarcode(),
			'format': event.getFormat()
		})

		self._writeLabel(xml, event.getLabel())

		xml.end()


	def _writeTrack(self, xml, track, score=None):
		if track is None:
			return

		xml.start('track', {
			'id': mbutils.extractUuid(track.getId()),
			'ext:score': score,
		})
		
		xml.elem('title', track.getTitle())
		xml.elem('duration', str(track.getDuration()))
		self._writeArtist(xml, track.getArtist())

		if len(track.getReleases()) > 0:
			# TODO: offset + count
			xml.start('release-list')
			for release in track.getReleases():
				self._writeRelease(xml, release)
			xml.end()

		if len(track.getPuids()) > 0:
			xml.start('puid-list')
			for puid in track.getPuids():
				xml.elem('puid', None, { 'id': puid })
			xml.end()

		self._writeRelationList(xml, track)
		# TODO: extensions

		xml.end()


	def _writeLabel(self, xml, label, score=None):
		if label is None:
			return

		xml.start('label', {
			'id': mbutils.extractUuid(label.getId()),
			'type': mbutils.extractFragment(label.getType()),
			'ext:score': score,
		})

		xml.elem('name', label.getName())
		xml.elem('sort-name', label.getSortName())
		xml.elem('disambiguation', label.getDisambiguation())
		xml.elem('life-span', None, {
			'begin': label.getBeginDate(),
			'end': label.getEndDate(),
		})

		if len(label.getAliases()) > 0:
			xml.start('alias-list')
			for alias in label.getAliases():
				xml.elem('alias', alias.getValue(), {
					'type': alias.getType(),
					'script': alias.getScript(),
				})
			xml.end()

		# TODO: releases, artists

		self._writeRelationList(xml, label)
		# TODO: extensions

		xml.end()


	def _writeRelationList(self, xml, entity):
		for tt in entity.getRelationTargetTypes():
			xml.start('relation-list', {
				'target-type': mbutils.extractFragment(tt),
			})
			for rel in entity.getRelations(targetType=tt):
				self._writeRelation(xml, rel, tt)
			xml.end()


	def _writeRelation(self, xml, rel, targetType):
		relAttrs = ' '.join([mbutils.extractFragment(a) 
				for a in rel.getAttributes()])

		if relAttrs == '':
			relAttrs = None

		attrs = {
			'type': mbutils.extractFragment(rel.getType()),
			'target': rel.getTargetId(),
			'direction': rel.getDirection(),
			'begin': rel.getBeginDate(),
			'end': rel.getBeginDate(),
			'attributes': relAttrs,
		}

		if rel.getTarget() is None:
			xml.elem('relation', None, attrs)
		else:
			xml.start('relation', attrs)
			if targetType == NS_REL_1 + 'Artist':
				self._writeArtist(xml, rel.getTarget())
			elif targetType == NS_REL_1 + 'Release':
				self._writeRelease(xml, rel.getTarget())
			elif targetType == NS_REL_1 + 'Track':
				self._writeTrack(xml, rel.getTarget())
			xml.end()
			

#
# DOM Utilities
#

def _matches(node, name, namespace=NS_MMD_1):
	"""Checks if an xml.dom.Node and a given name and namespace match."""

	if node.localName == name and node.namespaceURI == namespace:
		return True
	else:
		return False


def _getChildElements(parentNode):
	"""Returns all direct child elements of the given xml.dom.Node."""

	children = [ ]
	for node in parentNode.childNodes:
		if node.nodeType == node.ELEMENT_NODE:
			children.append(node)

	return children


def _getText(element, regex=None, default=None):
	"""Returns the text content of the given xml.dom.Element.

	This function simply fetches all contained text nodes, so the element
	should not contain child elements.
	"""
	res = ''
	for node in element.childNodes:
		if node.nodeType == node.TEXT_NODE:
			res += node.data

	if regex is None or re.match(regex, res):
		return res
	else:
		return default


def _getPositiveIntText(element):
	"""Returns the text content of the given xml.dom.Element as an int."""

	res = _getText(element)

	if res is None:
		return None

	try:
		return int(res)
	except ValueError:
		return None


def _getAttr(element, attrName, regex=None, default=None, ns=None):
	"""Returns an attribute of the given element.

	If there is no attribute with that name or the attribute doesn't
	match the regular expression, default is returned.
	"""
	if element.hasAttributeNS(ns, attrName):
		content = element.getAttributeNS(ns, attrName)

		if regex is None or re.match(regex, content):
			return content
		else:
			return default
	else:
		return default


def _getDateAttr(element, attrName):
	"""Gets an incomplete date from an attribute."""
	return _getAttr(element, attrName, '^\d+(-\d\d)?(-\d\d)?$')


def _getIdAttr(element, attrName, typeName):
	"""Gets an ID from an attribute and turns it into an absolute URI."""
	value = _getAttr(element, attrName)

	return _makeAbsoluteUri('http://musicbrainz.org/' + typeName + '/', value)

	

def _getIntAttr(element, attrName, min=0, max=None, ns=None):
	"""Gets an int from an attribute, or None."""
	try:
		val = int(_getAttr(element, attrName, ns=ns))

		if max is None:
			max = val

		if min <= val <= max:
			return val
		else:
			return None
	except ValueError:
		return None # raised if conversion to int fails
	except TypeError:
		return None # raised if no such attribute exists


def _getUriListAttr(element, attrName, prefix=NS_MMD_1):
	"""Gets a list of URIs from an attribute."""
	if not element.hasAttribute(attrName):
		return [ ]

	f = lambda x: x != ''
	uris = filter(f, re.split('\s+', element.getAttribute(attrName)))

	m = lambda x: _makeAbsoluteUri(prefix, x)
	uris = map(m, uris)

	return uris


def _getUriAttr(element, attrName, prefix=NS_MMD_1):
	"""Gets a URI from an attribute.

	This also works for space-separated URI lists. In this case, the
	first URI is returned.
	"""
	uris = _getUriListAttr(element, attrName, prefix)
	if len(uris) > 0:
		return uris[0]
	else:
		return None


def _getBooleanAttr(element, attrName):
	"""Gets a boolean value from an attribute."""
	value = _getAttr(element, attrName)
	if value == 'true':
		return True
	elif value == 'false':	
		return False
	else:
		return None


def _getDirectionAttr(element, attrName):
	"""Gets the Relation reading direction from an attribute."""
	regex = '^\s*(' + '|'.join((
				model.Relation.DIR_FORWARD,
				model.Relation.DIR_BACKWARD)) + ')\s*$'
	return _getAttr(element, 'direction', regex, model.Relation.DIR_NONE)


def _makeAbsoluteUri(prefix, uriStr):
	"""Creates an absolute URI adding prefix, if necessary."""
	if uriStr is None:
		return None

	(scheme, netloc, path, params, query, frag) = urlparse.urlparse(uriStr)

	if scheme == '' and netloc == '':
		return prefix + uriStr
	else:
		return uriStr
 
 
def _getResourceType(uri):
	"""Gets the resource type from a URI.

	The resource type is the basename of the URI's path.
	"""
	m = re.match('^' + NS_REL_1 + '(.*)$', uri)
	
	if m:
		return m.group(1).lower()
	else:
		return None

# EOF
