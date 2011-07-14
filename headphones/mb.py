import time

import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u

from lib.musicbrainz2.webservice import WebServiceError

from headphones.helpers import multikeysort

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

def getExtras(artistid):

	types = [m.Release.TYPE_EP, m.Release.TYPE_SINGLE, m.Release.TYPE_LIVE, m.Release.TYPE_REMIX,
			m.Release.TYPE_COMPILATION]
			
	for type in types:
	
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, type), releaseGroups=True)
		artist = q.getArtistById(artistid, inc)
		
		for rg in artist.getReleaseGroups():
		
			rgid = u.extractUuid(rg.id)
			releaseid = getReleaseGroup(rgid)
			
			inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
			results = ws.Query().getReleaseById(releaseid, inc)
			
			print results.title
			print u.getReleaseTypeName(results.releaseGroup.type)
		