import time

import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u

from musicbrainz2.webservice import WebServiceError

from helpers import multikeysort

q = ws.Query()


def findArtist(name, limit=1):

	artistlist = []
	
	artistResults = q.getArtists(ws.ArtistFilter(name=name, limit=limit))
	
	for result in artistResults:
	
		artistid = u.extractUuid(result.artist.id)
		artistlist.append([result.artist.name, artistid])
		
	return artistlist

def getArtist(artistid):


	rglist = []

	#Get all official release groups
	inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=True)
	artist = q.getArtistById(artistid, inc)
	
	for rg in artist.getReleaseGroups():
		
		rgid = u.extractUuid(rg.id)
		rglist.append([rg.title, rgid])
	
	return rglist
	
def getReleaseGroup(rgid):

	releaselist = []
	
	inc = ws.ReleaseGroupIncludes(releases=True)
	releaseGroup = q.getReleaseGroupById(rgid, inc)
	
	# I think for now we have to make separate queries for each release, in order
	# to get more detailed release info (ASIN, track count, etc.)
	for release in releaseGroup.releases:
			
		releaseid = u.extractUuid(release.id)
		inc = ws.ReleaseIncludes(tracks=True)
		
		releaseResult = q.getReleaseById(releaseid, inc)
		
		release_dict = {
			'asin':			bool(releaseResult.asin),
			'tracks':		len(releaseResult.getTracks()),
			'releaseid':	u.extractUuid(releaseResult.id)
		}
		
		releaselist.append(release_dict)
		time.sleep(1)

	a = multikeysort(releaselist, ['-asin', '-tracks'])

	releaseid = a[0]['releaseid']
	
	return releaseid
	
def getRelease(releaseid):
	"""
	Given a release id, gather all the info and return it as a list
	"""
	inc = ws.ReleaseIncludes(artist=True, tracks=True, releaseGroup=True)
	release = q.getReleaseById(releaseid, inc)
	
	releasedetail = []
	
	releasedetail.append(release.id)

