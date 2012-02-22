from __future__ import with_statement

import time
import threading

import lib.musicbrainz2.webservice as ws
import lib.musicbrainz2.model as m
import lib.musicbrainz2.utils as u

from lib.musicbrainz2.webservice import WebServiceError

import headphones
from headphones import logger, db
from headphones.helpers import multikeysort, replace_all

mb_lock = threading.Lock()


# Quick fix to add mirror switching on the fly. Need to probably return the mbhost & mbport that's
# being used, so we can send those values to the log
def startmb():

	if headphones.MIRROR == "localhost":
		mbhost = "localhost"
		mbport = 7143
		sleepytime = 0
	elif headphones.MIRROR == "headphones":
		mbhost = "178.63.142.150"
		mbport = 5000
		sleepytime = 0
	elif headphones.MIRROR == "tbueter.com":
		mbhost = "tbueter.com"
		mbport = 3000
		sleepytime = 0
	else:
		mbhost = "musicbrainz.org"
		mbport = 80
		sleepytime = 1
	
	service = ws.WebService(host=mbhost, port=mbport)
	q = ws.Query(service)
	
	return (q, sleepytime)
	

def findArtist(name, limit=1):

	with mb_lock:
	
		artistlist = []
		attempt = 0
		artistResults = None
		
		chars = set('!?*')
		if any((c in chars) for c in name):
			name = '"'+name+'"'
			
		q, sleepytime = startmb()
		
		while attempt < 5:
		
			try:
				artistResults = q.getArtists(ws.ArtistFilter(query=name, limit=limit))
				break
			except WebServiceError, e:
				logger.warn('Attempt to query MusicBrainz for %s failed: %s [%s:%i]' % (name, e, mbhost, mbport))
				attempt += 1
				time.sleep(5)
		
		time.sleep(sleepytime)
		
		if not artistResults:
			return False		
		
		for result in artistResults:
		
			if result.artist.name != result.artist.getUniqueName() and limit == 1:
				
				logger.debug('Found an artist with a disambiguation: %s - doing an album based search' % name)
				artistdict = findArtistbyAlbum(name)
				
				if not artistdict:
					logger.debug('Cannot determine the best match from an artist/album search. Using top match instead')
					artistlist.append({
						'name': 			result.artist.name,
						'uniquename':		result.artist.getUniqueName(),
						'id':				u.extractUuid(result.artist.id),
						'url': 				result.artist.id,
						'score':			result.score
						})
					
				else:
					artistlist.append(artistdict)
			
			else:
				artistlist.append({
						'name': 			result.artist.name,
						'uniquename':		result.artist.getUniqueName(),
						'id':				u.extractUuid(result.artist.id),
						'url': 				result.artist.id,
						'score':			result.score
						})
			
		return artistlist
		
def findRelease(name, limit=1):

	with mb_lock:
	
		releaselist = []
		attempt = 0
		releaseResults = None
		
		chars = set('!?')
		if any((c in chars) for c in name):
			name = '"'+name+'"'
			
		q, sleepytime = startmb()
		
		while attempt < 5:
		
			try:
				releaseResults = q.getReleases(ws.ReleaseFilter(query=name, limit=limit))
				break
			except WebServiceError, e:
				logger.warn('Attempt to query MusicBrainz for %s failed: %s' % (name, e))
				attempt += 1
				time.sleep(5)
		
		time.sleep(sleepytime)
		
		if not releaseResults:
			return False		
		
		for result in releaseResults:
			
			releaselist.append({
						'uniquename':		result.release.artist.name,
						'title': 			result.release.title,
						'id':				u.extractUuid(result.release.artist.id),
						'albumid':			u.extractUuid(result.release.id),
						'url': 				result.release.artist.id,
						'albumurl':			result.release.id,
						'score':			result.score
						})
			
		return releaselist

def getArtist(artistid, extrasonly=False):

	with mb_lock:
	
		artist_dict = {}
	
		#Get all official release groups
		inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), releaseGroups=True)
		artist = None
		attempt = 0
		
		q, sleepytime = startmb()
		
		while attempt < 5:
		
			try:
				artist = q.getArtistById(artistid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s. Sleeping 5 seconds' % artistid)
				attempt += 1
				time.sleep(5)
				
		if not artist:
			return False
		
		time.sleep(sleepytime)
				
		artist_dict['artist_name'] = artist.name
		artist_dict['artist_sortname'] = artist.sortName
		artist_dict['artist_uniquename'] = artist.getUniqueName()
		artist_dict['artist_type'] = u.extractFragment(artist.type)
		artist_dict['artist_begindate'] = artist.beginDate
		artist_dict['artist_enddate'] = artist.endDate
		
		releasegroups = []
		
		if not extrasonly:
		
			for rg in artist.getReleaseGroups():
				
				releasegroups.append({
							'title':		rg.title,
							'id':			u.extractUuid(rg.id),
							'url':			rg.id,
							'type':			u.getReleaseTypeName(rg.type)
					})
				
		# See if we need to grab extras
		myDB = db.DBConnection()

		try:
			includeExtras = myDB.select('SELECT IncludeExtras from artists WHERE ArtistID=?', [artistid])[0][0]
		except IndexError:
			includeExtras = False
		
		if includeExtras or headphones.INCLUDE_EXTRAS:
			includes = [m.Release.TYPE_COMPILATION, m.Release.TYPE_REMIX, m.Release.TYPE_SINGLE, m.Release.TYPE_LIVE, m.Release.TYPE_EP, m.Release.TYPE_SOUNDTRACK]
			for include in includes:
				inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, include), releaseGroups=True)
		
				artist = None
				attempt = 0
			
				while attempt < 5:
		
					try:
						artist = q.getArtistById(artistid, inc)
						break
					except WebServiceError, e:
						logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s. Sleeping 5 seconds' % artistid)
						attempt += 1
						time.sleep(5)
						
				if not artist:
					continue
					
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
	Returns a dictionary of the best stuff from a release group
	"""
	with mb_lock:
	
		releaselist = []
		
		inc = ws.ReleaseGroupIncludes(releases=True, artist=True)
		releaseGroup = None
		attempt = 0
		
		q, sleepytime = startmb()
		
		while attempt < 5:
		
			try:
				releaseGroup = q.getReleaseGroupById(rgid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz for release group "%s" failed. Sleeping 5 seconds' % rgid)
				attempt += 1
				time.sleep(5)
	
		if not releaseGroup:
			return False
			
		time.sleep(sleepytime)
		# I think for now we have to make separate queries for each release, in order
		# to get more detailed release info (ASIN, track count, etc.)
		for release in releaseGroup.releases:
	
			inc = ws.ReleaseIncludes(tracks=True, releaseEvents=True)	
			releaseResult = None
			attempt = 0
			
			while attempt < 5:
			
				try:
					releaseResult = q.getReleaseById(release.id, inc)
					break
				except WebServiceError, e:
					logger.warn('Attempt to retrieve release information for %s from MusicBrainz failed: %s. Sleeping 5 seconds' % (releaseResult.title, e))
					attempt += 1
					time.sleep(5)		
			
			if not releaseResult:
				continue
			
			# Release filter for non-official live albums
			types = releaseResult.getTypes()
			if any('Live' in type for type in types):
				if not any('Official' in type for type in types):
					logger.debug('%s is not an official live album. Skipping' % releaseResult.name)
					continue
				
			time.sleep(sleepytime)
			
			formats = {
				'2xVinyl':			'2',
				'Vinyl':			'2',
				'CD':				'0',
				'Cassette':			'3',			
				'2xCD':				'1',
				'Digital Media':	'0'
				}
				
			country = {
				'US':	'0',
				'GB':	'1',
				'JP':	'2',
				}

			
			try:
				format = int(replace_all(u.extractFragment(releaseResult.releaseEvents[0].format), formats))
			except:
				format = 3
				
			try:
				country = int(replace_all(releaseResult.releaseEvents[0].country, country))
			except:
				country = 3
			
			release_dict = {
				'hasasin':		bool(releaseResult.asin),
				'asin':			releaseResult.asin,
				'trackscount':	len(releaseResult.getTracks()),
				'releaseid':	u.extractUuid(releaseResult.id),
				'releasedate':	releaseResult.getEarliestReleaseDate(),
				'format':		format,
				'country':		country
				}
			
			tracks = []
			
			i = 1
			for track in releaseResult.tracks:
				
				tracks.append({
						'number':		i,
						'title':		track.title,
						'id':			u.extractUuid(track.id),
						'url':			track.id,
						'duration':		track.duration
						})
				i += 1
			
			release_dict['tracks'] = tracks		
			
			releaselist.append(release_dict)
		
		average_tracks = sum(x['trackscount'] for x in releaselist) / float(len(releaselist))
		
		for item in releaselist:
			item['trackscount_delta'] = abs(average_tracks - item['trackscount'])
			
		a = multikeysort(releaselist, ['-hasasin', 'country', 'format', 'trackscount_delta'])
		
		release_dict = {'releaseid' :a[0]['releaseid'],
						'releasedate'	: releaselist[0]['releasedate'],
						'trackcount'	: a[0]['trackscount'],
						'tracks'		: a[0]['tracks'],
						'asin'			: a[0]['asin'],
						'releaselist'	: releaselist,
						'artist_name'	: releaseGroup.artist.name,
						'artist_id'		: u.extractUuid(releaseGroup.artist.id),
						'title'			: releaseGroup.title,
						'type'			: u.extractFragment(releaseGroup.type)
						}
		
		return release_dict
	
def getRelease(releaseid):
	"""
	Deep release search to get track info
	"""
	with mb_lock:
	
		release = {}
	
		inc = ws.ReleaseIncludes(tracks=True, releaseEvents=True, releaseGroup=True, artist=True)
		results = None
		attempt = 0
		
		q, sleepytime = startmb()
			
		while attempt < 5:
		
			try:
				results = q.getReleaseById(releaseid, inc)
				break
			except WebServiceError, e:
				logger.warn('Attempt to retrieve information from MusicBrainz for release "%s" failed: %s. SLeeping 5 seconds' % (releaseid, e))
				attempt += 1
				time.sleep(5)	
		
		if not results:
			return False
		
		time.sleep(sleepytime)
		
		release['title'] = results.title
		release['id'] = u.extractUuid(results.id)
		release['asin'] = results.asin
		release['date'] = results.getEarliestReleaseDate()


		rg = results.getReleaseGroup()
		if rg:
			release['rgid'] = u.extractUuid(rg.id)
			release['rg_title'] = rg.title
			release['rg_type'] = u.extractFragment(rg.type)
		else:
			logger.warn("Release " + releaseid + "had no ReleaseGroup associated")
		#so we can start with a releaseID from anywhere and get the artist info
		#it looks like MB api v1 only returns 1 artist object - 2.0 returns more...
		release['artist_name'] = results.artist.name
		release['artist_id'] = u.extractUuid(results.artist.id)
		
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
		
def findArtistbyAlbum(name):

	myDB = db.DBConnection()
	
	artist = myDB.action('SELECT AlbumTitle from have WHERE ArtistName=? AND AlbumTitle IS NOT NULL ORDER BY RANDOM()', [name]).fetchone()
	
	if not artist:
		return False
		
	# Probably not neccessary but just want to double check
	if not artist['AlbumTitle']:
		return False
	
	term = '"'+artist['AlbumTitle']+'" AND artist:"'+name+'"'
	
	f = ws.ReleaseGroupFilter(query=term, limit=1)
	results = None
	attempt = 0
	
	q, sleepytime = startmb()
			
	while attempt < 5:
			
		try:
			results = q.getReleaseGroups(f)
			break
		except WebServiceError, e:
			logger.warn('Attempt to query MusicBrainz for %s failed: %s. Sleeping 5 seconds.' % (name, e))
			attempt += 1
			time.sleep(5)	
	
	time.sleep(sleepytime)
	
	if not results:
		return False

	artist_dict = {}
	
	for result in results:
		releaseGroup = result.releaseGroup
		artist_dict['name'] = releaseGroup.artist.name
		artist_dict['uniquename'] = releaseGroup.artist.getUniqueName()
		artist_dict['id'] = u.extractUuid(releaseGroup.artist.id)
		artist_dict['url'] = releaseGroup.artist.id
		artist_dict['score'] = result.score
	
	return artist_dict
	
def findAlbumID(artist=None, album=None):

	f = ws.ReleaseGroupFilter(title=album, artistName=artist, limit=1)
	results = None
	attempt = 0
	
	q, sleepytime = startmb()
			
	while attempt < 5:
			
		try:
			results = q.getReleaseGroups(f)
			break
		except Exception, e:
			logger.warn('Attempt to query MusicBrainz for %s - %s failed: %s. Sleeping 5 seconds.' % (artist, album, e))
			attempt += 1
			time.sleep(5)	
	
	time.sleep(sleepytime)
	
	if not results:
		return False
		
	rgid = u.extractUuid(results[0].releaseGroup.id)
	return rgid
