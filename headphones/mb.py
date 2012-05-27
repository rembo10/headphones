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

import lib.musicbrainzngs as musicbrainzngs

mb_lock = threading.Lock()


# Quick fix to add mirror switching on the fly. Need to probably return the mbhost & mbport that's
# being used, so we can send those values to the log
def startmb(forcemb=False):

    mbuser = None
    mbpass = None
    
    # Can use headphones mirror for queries
    if headphones.MIRROR == "headphones" or "custom":
        forcemb=False
    
    if forcemb or headphones.MIRROR == "musicbrainz.org":
        mbhost = "musicbrainz.org"
        mbport = 80
        sleepytime = 1
    elif headphones.MIRROR == "custom":
        mbhost = headphones.CUSTOMHOST
        mbport = int(headphones.CUSTOMPORT)
        sleepytime = int(headphones.CUSTOMSLEEP)
    elif headphones.MIRROR == "headphones":
        mbhost = "178.63.142.150"
        mbport = 8181
        mbuser = headphones.HPUSER
        mbpass = headphones.HPPASS
        sleepytime = 0
    else:
        mbhost = "tbueter.com"
        mbport = 5000
        sleepytime = 0
    
    musicbrainzngs.set_useragent("headphones","0.0","https://github.com/doskir/headphones")
    logger.info("set user agent")
    musicbrainzngs.set_hostname(mbhost + ":" + str(mbport))
    logger.info("set host and port")

    #q = musicbrainzngs
    service = ws.WebService(host=mbhost, port=mbport, username=mbuser, password=mbpass, mirror=headphones.MIRROR)
    q = ws.Query(service)
    
    logger.debug('Using the following server values:\nMBHost: %s ; MBPort: %i  ;  Sleep Interval: %i ' % (mbhost, mbport, sleepytime))
    
    return (q, sleepytime)

def findArtist(name, limit=1):

    with mb_lock:
        limit = 25
        artistlist = []
        attempt = 0
        artistResults = None
        
        chars = set('!?*')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        q, sleepytime = startmb(forcemb=True)
        
        while attempt < 5:        
            try:
                artistResults = musicbrainzngs.search_artists(query=name,limit=limit)['artist-list']
                break
            except WebServiceError, e:#need to update the exceptions
                logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
                attempt += 1
                time.sleep(10)
        
        time.sleep(sleepytime)
        
        if not artistResults:
            return False        
        for result in artistResults:
            if 'disambiguation' in result:
                uniquename = unicode(result['sort-name'] + " (" + result['disambiguation'] + ")")
            else:
                uniquename = unicode(result['sort-name'])
            if result['name'] != uniquename and limit == 1:
                logger.debug('Found an artist with a disambiguation: %s - doing an album based search' % name)
                artistdict = findArtistbyAlbum(name)                
                if not artistdict:
                    logger.debug('Cannot determine the best match from an artist/album search. Using top match instead')
                    artistlist.append({
                        'name':             unicode(result['sort-name']),
                        'uniquename':        uniquename,
                        'id':                unicode(result['id']),
                        'url':                 unicode("http://musicbrainz.org/artist/" + result['id']),#probably needs to be changed
                        'score':            int(result['ext:score'])
                        })                    
                else:
                    artistlist.append(artistdict)
            else:                
                artistlist.append({
                        'name':             unicode(result['sort-name']),
                        'uniquename':        uniquename,
                        'id':                unicode(result['id']),
                        'url':                 unicode("http://musicbrainz.org/artist/" + result['id']),#probably needs to be changed
                        'score':            int(result['ext:score'])
                        })
        return artistlist
        
def findRelease(name, limit=1):

    with mb_lock:
        limit=25
        releaselistngs = []
        attempt = 0
        releaseResultsngs = None
        
        chars = set('!?')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        q, sleepytime = startmb(forcemb=True)
        
        while attempt < 5:
        
            try:
                releaseResultsngs = musicbrainzngs.search_releases(query=name,limit=limit)['release-list']
                break
            except WebServiceError, e: #need to update exceptions
                logger.warn('Attempt to query MusicBrainz for "%s" failed: %s' % (name, str(e)))
                attempt += 1
                time.sleep(10)
        
        time.sleep(sleepytime)
        
        if not releaseResultsngs:
            return False
        for result in releaseResultsngs:
                        releaselistngs.append({
                        'uniquename':        unicode(result['artist-credit'][0]['artist']['name']),
                        'title':             unicode(result['title']),
                        'id':                unicode(result['artist-credit'][0]['artist']['id']),
                        'albumid':            unicode(result['id']),
                        'url':                 unicode("http://musicbrainz.org/artist/" + result['artist-credit'][0]['artist']['id']),#probably needs to be changed
                        'albumurl':            unicode("http://musicbrainz.org/release/" + result['id']),#probably needs to be changed
                        'score':            int(result['ext:score'])
                        })            
        return releaselistngs

def getArtist(artistid, extrasonly=False):

    with mb_lock:    
        artist_dict = {}
    
        artist = None
        attempt = 0
        
        q, sleepytime = startmb()
        
        while attempt < 5:
        
            try:
                artist = musicbrainzngs.get_artist_by_id(artistid,includes=["releases","release-groups"],release_status="official",release_type="album")['artist']
                break
            except WebServiceError, e:
                logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s (%s)' % (artistid, str(e))) 
                attempt += 1
                time.sleep(5)
            except Exception,e:
                pass
        
        
        if not artist:
            return False
        
        time.sleep(sleepytime)
        
        if 'disambiguation' in artist:
            uniquename = unicode(artist['sort-name'] + " (" + artist['disambiguation'] + ")")
        else:
            uniquename = unicode(artist['sort-name'])
        artist_dict['artist_name'] = unicode(artist['name'])
        artist_dict['artist_sortname'] = unicode(artist['sort-name'])
        artist_dict['artist_uniquename'] = uniquename
        artist_dict['artist_type'] = unicode(artist['type'])

        artist_dict['artist_begindate'] = None
        artist_dict['artist_enddate'] = None
        if 'life-span' in artist:
            if 'begin' in artist['life-span']:
                artist_dict['artist_begindate'] = unicode(artist['life-span']['begin'])
            if 'end' in artist['life-span']:
                artist_dict['artist_enddate'] = unicode(artist['life-span']['end'])      

                
        
        releasegroups = []
        
        if not extrasonly:
            for rg in artist['release-group-list']:
                if rg['type'] != 'Album': #only add releases without a secondary type
                    continue
                releasegroups.append({
                            'title':        unicode(rg['title']),
                            'id':            unicode(rg['id']),
                            'url':            u"http://musicbrainz.org/release-group/" + rg['id'],
                            'type':            unicode(rg['type'])
                    })               
                
        # See if we need to grab extras
        myDB = db.DBConnection()

        try:
            includeExtras = myDB.select('SELECT IncludeExtras from artists WHERE ArtistID=?', [artistid])[0][0]
        except IndexError:
            includeExtras = False
        
        if includeExtras or headphones.INCLUDE_EXTRAS:
            includes = ["single", "ep", "compilation", "soundtrack", "live", "remix"]
            for include in includes:
                artist = None
                attempt = 0
                while attempt < 5:#this may be redundant with musicbrainzngs, it seems to retry and wait by itself, i will leave it in for rembo to review
                    try:
                        artist = musicbrainzngs.get_artist_by_id(artistid,includes=["releases","release-groups"],release_status=['official'],release_type=include)['artist']
                        break
                    except WebServiceError, e:#update exceptions
                        logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s (%s)' % (artistid, str(e)))
                        attempt += 1
                        time.sleep(5)
                if not artist:
                    continue
                for rg in artist['release-group-list']:
                    releasegroups.append({
                            'title':        unicode(rg['title']),
                            'id':            unicode(rg['id']),
                            'url':            u"http://musicbrainz.org/release-group/" + rg['id'],
                            'type':            unicode(rg['type'])
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
                logger.warn('Attempt to retrieve information from MusicBrainz for release group "%s" failed (%s)' % (rgid, str(e)))
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
                    logger.warn('Attempt to retrieve release information for %s from MusicBrainz failed (%s)' % (releaseResult.title, str(e)))
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
                '2xVinyl':            '2',
                'Vinyl':            '2',
                'CD':                '0',
                'Cassette':            '3',            
                '2xCD':                '1',
                'Digital Media':    '0'
                }
                
            country = {
                'US':    '0',
                'GB':    '1',
                'JP':    '2',
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
                'hasasin':        bool(releaseResult.asin),
                'asin':            releaseResult.asin,
                'trackscount':    len(releaseResult.getTracks()),
                'releaseid':    u.extractUuid(releaseResult.id),
                'releasedate':    releaseResult.getEarliestReleaseDate(),
                'format':        format,
                'country':        country
                }
            
            tracks = []
            
            i = 1
            for track in releaseResult.tracks:
                
                tracks.append({
                        'number':        i,
                        'title':        track.title,
                        'id':            u.extractUuid(track.id),
                        'url':            track.id,
                        'duration':        track.duration
                        })
                i += 1
            
            release_dict['tracks'] = tracks        
            
            releaselist.append(release_dict)
        
        average_tracks = sum(x['trackscount'] for x in releaselist) / float(len(releaselist))
        
        for item in releaselist:
            item['trackscount_delta'] = abs(average_tracks - item['trackscount'])
            
        a = multikeysort(releaselist, ['-hasasin', 'country', 'format', 'trackscount_delta'])
        
        release_dict = {'releaseid' :a[0]['releaseid'],
                        'releasedate'    : releaselist[0]['releasedate'],
                        'trackcount'    : a[0]['trackscount'],
                        'tracks'        : a[0]['tracks'],
                        'asin'            : a[0]['asin'],
                        'releaselist'    : releaselist,
                        'artist_name'    : releaseGroup.artist.name,
                        'artist_id'        : u.extractUuid(releaseGroup.artist.id),
                        'title'            : releaseGroup.title,
                        'type'            : u.extractFragment(releaseGroup.type)
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
                logger.warn('Attempt to retrieve information from MusicBrainz for release "%s" failed (%s)' % (releaseid, str(e)))
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
                    'number':        i,
                    'title':        track.title,
                    'id':            u.extractUuid(track.id),
                    'url':            track.id,
                    'duration':        track.duration
                    })
            i += 1
            
        release['tracks'] = tracks
        
        return release

# Used when there is a disambiguation
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
    
    q, sleepytime = startmb(forcemb=True)
            
    while attempt < 5:
            
        try:
            results = q.getReleaseGroups(f)
            break
        except WebServiceError, e:
            logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
            attempt += 1
            time.sleep(10)    
    
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
    
    q, sleepytime = startmb(forcemb=True)
            
    while attempt < 5:
            
        try:
            results = q.getReleaseGroups(f)
            break
        except WebServiceError, e:
            logger.warn('Attempt to query MusicBrainz for %s - %s failed (%s)' % (artist, album, str(e)))
            attempt += 1
            time.sleep(10)    
    
    time.sleep(sleepytime)
    
    if not results:
        return False
        
    rgid = u.extractUuid(results[0].releaseGroup.id)
    return rgid
