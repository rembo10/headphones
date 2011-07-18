from __future__ import with_statement

import time
import threading

import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u

from lib.musicbrainz2.webservice import WebServiceError

from headphones import logger
from headphones.helpers import multikeysort

q = ws.Query()
mb_lock = threading.Lock()

def findArtist(name, limit=1):

	with mb_lock:

		artistlist = []
		attempt = 0
		
		while attempt < 5:
		
			try:
				artistResults = q.getArtists(ws.ArtistFilter(query=name, limit=limit))
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz failed: %s' % e)
				attempt += 1
				time.sleep(1)
		
		time.sleep(1)
		
		for result in artistResults:
			
			artistlist.append({
					'name': 			result.artist.name,
					'uniquename':		result.artist.getUniqueName(),
					'id':				u.extractUuid(result.artist.id),
					'url': 				result.artist.id,
					'score':			result.score
					})
			
		return artistlist

def getArtist(artistid):

	with mb_lock:
	
		artist_dict = {}
	
		#Get all official release groups
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		
		attempt = 0
		
		while attempt < 5:
		
			try:
				artist = q.getArtistById(artistid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz failed: %s' % e)
				attempt += 1
				time.sleep(1)
				
		time.sleep(1)
				
		artist_dict['artist_name'] = artist.name
		artist_dict['artist_sortname'] = artist.sortName
		artist_dict['artist_uniquename'] = artist.getUniqueName()
		artist_dict['artist_type'] = u.extractFragment(artist.type)
		artist_dict['artist_begindate'] = artist.beginDate
		artist_dict['artist_enddate'] = artist.endDate
		
		releasegroups = []
		
		for rg in artist.getReleaseGroups():
			
			releasegroups.append({
						'title':		rg.title,
						'id':			u.extractUuid(rg.id),
						'url':			rg.id,
						'type':			u.getReleaseTypeName(rg.type)
				})
				
		artist_dict['releasegroups'] = releasegroups
		
		return artist_dict
	
def getReleaseGroup(rgid):
	"""
	Returns the best release out of any given release group
	"""
	with mb_lock:
	
		releaselist = []
		
		inc = ws.ReleaseGroupIncludes(releases=True)
		
		attempt = 0
		
		while attempt < 5:
		
			try:
				releaseGroup = q.getReleaseGroupById(rgid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz failed: %s' % e)
				attempt += 1
				time.sleep(1)
	
		time.sleep(1)
		# I think for now we have to make separate queries for each release, in order
		# to get more detailed release info (ASIN, track count, etc.)
		for release in releaseGroup.releases:
	
			inc = ws.ReleaseIncludes(tracks=True)		
	
			attempt = 0
			
			while attempt < 5:
			
				try:
					releaseResult = q.getReleaseById(release.id, inc)
					break
				except WebServiceError, e:
					logger.warn('Attempt to retrieve information for %s from MusicBrainz failed: %s' % (releaseResult.title, e))
					attempt += 1
					time.sleep(1)		
			
			if not releaseResult:
				continue
				
			time.sleep(1)
			
			release_dict = {
				'asin':			bool(releaseResult.asin),
				'tracks':		len(releaseResult.getTracks()),
				'releaseid':	u.extractUuid(releaseResult.id)
				}
			
			releaselist.append(release_dict)
	
		a = multikeysort(releaselist, ['-asin', '-tracks'])
	
		releaseid = a[0]['releaseid']
		
		return releaseid
	
def getRelease(releaseid):
	"""
	Deep release search to get track info
	"""
	with mb_lock:
	
		release = {}
	
		inc = ws.ReleaseIncludes(tracks=True, releaseEvents=True)
		
		attempt = 0
			
		while attempt < 5:
		
			try:
				results = q.getReleaseById(releaseid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz failed: %s' % e)
				attempt += 1
				time.sleep(1)	
		
		time.sleep(1)
		
		release['title'] = results.title
		release['id'] = u.extractUuid(results.id)
		release['asin'] = results.asin
		release['date'] = results.getEarliestReleaseDate()
		
		tracks = []
		
		i = 1
		for track in results.tracks:
			tracks.append({
					'number':		i,
					'title':		track.title,
					'id':			u.extractUuid(track.id),
					'url':			track.id,
					'duration':		track.duration
					})
			i += 1
			
		release['tracks'] = tracks
		
		return release
	

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
	