"""Utilities for working with Audio CDs.

This module contains utilities for working with Audio CDs.

The functions in this module need both a working ctypes package (already
included in python-2.5) and an installed libdiscid. If you don't have
libdiscid, it can't be loaded, or your platform isn't supported by either
ctypes or this module, a C{NotImplementedError} is raised when using the
L{readDisc()} function.

@author: Matthias Friedrich <matt@mafr.de>
"""
__revision__ = '$Id: disc.py 11987 2009-08-22 11:57:51Z matt $'

import sys
import urllib
import urlparse
import ctypes
import ctypes.util
from musicbrainz2.model import Disc

__all__ = [ 'DiscError', 'readDisc', 'getSubmissionUrl' ]


class DiscError(IOError):
	"""The Audio CD could not be read.

	This may be simply because no disc was in the drive, the device name
	was wrong or the disc can't be read. Reading errors can occur in case
	of a damaged disc or a copy protection mechanism, for example.
	"""
	pass


def _openLibrary():
	"""Tries to open libdiscid.

	@return: a C{ctypes.CDLL} object, representing the opened library

	@raise NotImplementedError: if the library can't be opened
	"""
	# This only works for ctypes >= 0.9.9.3. Any libdiscid is found,
	# no matter how it's called on this platform.
	try:
		if hasattr(ctypes.cdll, 'find'):
			libDiscId = ctypes.cdll.find('discid')
			_setPrototypes(libDiscId)
			return libDiscId
	except OSError, e:
		raise NotImplementedError('Error opening library: ' + str(e))

	# Try to find the library using ctypes.util
	libName = ctypes.util.find_library('discid')
	if libName != None:
		try:
			libDiscId = ctypes.cdll.LoadLibrary(libName)
			_setPrototypes(libDiscId)
			return libDiscId
		except OSError, e:
			raise NotImplementedError('Error opening library: ' +
				str(e))

	# For compatibility with ctypes < 0.9.9.3 try to figure out the library
	# name without the help of ctypes. We use cdll.LoadLibrary() below,
	# which isn't available for ctypes == 0.9.9.3.
	#
	if sys.platform == 'linux2':
		libName = 'libdiscid.so.0'
	elif sys.platform == 'darwin':
		libName = 'libdiscid.0.dylib'
	elif sys.platform == 'win32':
		libName = 'discid.dll'
	else:
		# This should at least work for Un*x-style operating systems
		libName = 'libdiscid.so.0'

	try:
		libDiscId = ctypes.cdll.LoadLibrary(libName)
		_setPrototypes(libDiscId)
		return libDiscId
	except OSError, e:
		raise NotImplementedError('Error opening library: ' + str(e))

	assert False # not reached


def _setPrototypes(libDiscId):
	ct = ctypes
	libDiscId.discid_new.argtypes = ( )
	libDiscId.discid_new.restype = ct.c_void_p

	libDiscId.discid_free.argtypes = (ct.c_void_p, )

	libDiscId.discid_read.argtypes = (ct.c_void_p, ct.c_char_p)

	libDiscId.discid_get_error_msg.argtypes = (ct.c_void_p, )
	libDiscId.discid_get_error_msg.restype = ct.c_char_p

	libDiscId.discid_get_id.argtypes = (ct.c_void_p, )
	libDiscId.discid_get_id.restype = ct.c_char_p

	libDiscId.discid_get_first_track_num.argtypes = (ct.c_void_p, )
	libDiscId.discid_get_first_track_num.restype = ct.c_int

	libDiscId.discid_get_last_track_num.argtypes = (ct.c_void_p, )
	libDiscId.discid_get_last_track_num.restype = ct.c_int

	libDiscId.discid_get_sectors.argtypes = (ct.c_void_p, )
	libDiscId.discid_get_sectors.restype = ct.c_int

	libDiscId.discid_get_track_offset.argtypes = (ct.c_void_p, ct.c_int)
	libDiscId.discid_get_track_offset.restype = ct.c_int

	libDiscId.discid_get_track_length.argtypes = (ct.c_void_p, ct.c_int)
	libDiscId.discid_get_track_length.restype = ct.c_int


def getSubmissionUrl(disc, host='mm.musicbrainz.org', port=80):
	"""Returns a URL for adding a disc to the MusicBrainz database.

	A fully initialized L{musicbrainz2.model.Disc} object is needed, as
	returned by L{readDisc}. A disc object returned by the web service
	doesn't provide the necessary information.

	Note that the created URL is intended for interactive use and points
	to the MusicBrainz disc submission wizard by default. This method
	just returns a URL, no network connection is needed. The disc drive
	isn't used.

	@param disc: a fully initialized L{musicbrainz2.model.Disc} object
	@param host: a string containing a host name
	@param port: an integer containing a port number

	@return: a string containing the submission URL

	@see: L{readDisc}
	"""
	assert isinstance(disc, Disc), 'musicbrainz2.model.Disc expected'
	discid = disc.getId()
	first = disc.getFirstTrackNum()
	last = disc.getLastTrackNum()
	sectors = disc.getSectors()
	assert None not in (discid, first, last, sectors)

	tracks = last - first + 1
	toc = "%d %d %d " % (first, last, sectors)
	toc = toc + ' '.join( map(lambda x: str(x[0]), disc.getTracks()) )

	query = urllib.urlencode({ 'id': discid, 'toc': toc, 'tracks': tracks })

	if port == 80:
		netloc = host
	else:
		netloc = host + ':' + str(port)

	url = ('http', netloc, '/bare/cdlookup.html', '', query, '')
		
	return urlparse.urlunparse(url)


def readDisc(deviceName=None):
	"""Reads an Audio CD in the disc drive.

	This reads a CD's table of contents (TOC) and calculates the MusicBrainz
	DiscID, which is a 28 character ASCII string. This DiscID can be used
	to retrieve a list of matching releases from the web service (see
	L{musicbrainz2.webservice.Query}).

	Note that an Audio CD has to be in drive for this to work. The
	C{deviceName} argument may be used to set the device. The default
	depends on the operating system (on linux, it's C{'/dev/cdrom'}).
	No network connection is needed for this function.

	If the device doesn't exist or there's no valid Audio CD in the drive,
	a L{DiscError} exception is raised.

	@param deviceName: a string containing the CD drive's device name

	@return: a L{musicbrainz2.model.Disc} object

	@raise DiscError: if there was a problem reading the disc
	@raise NotImplementedError: if DiscID generation isn't supported
	"""
	libDiscId = _openLibrary()

	handle = libDiscId.discid_new()
	assert handle != 0, "libdiscid: discid_new() returned NULL"

	# Access the CD drive. This also works if deviceName is None because
	# ctypes passes a NULL pointer in this case.
	#
	res = libDiscId.discid_read(handle, deviceName)
	if res == 0:
		raise DiscError(libDiscId.discid_get_error_msg(handle))


	# Now extract the data from the result.
	#
	disc = Disc()

	disc.setId( libDiscId.discid_get_id(handle) )

	firstTrackNum = libDiscId.discid_get_first_track_num(handle)
	lastTrackNum = libDiscId.discid_get_last_track_num(handle)

	disc.setSectors(libDiscId.discid_get_sectors(handle))

	for i in range(firstTrackNum, lastTrackNum+1):
		trackOffset = libDiscId.discid_get_track_offset(handle, i)
		trackSectors = libDiscId.discid_get_track_length(handle, i)

		disc.addTrack( (trackOffset, trackSectors) )

	disc.setFirstTrackNum(firstTrackNum)
	disc.setLastTrackNum(lastTrackNum)

	libDiscId.discid_free(handle)

	return disc

# EOF
