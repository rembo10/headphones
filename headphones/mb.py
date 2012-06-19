#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import time
import threading

import headphones
from headphones import logger, db
from headphones.helpers import multikeysort, replace_all

import lib.musicbrainzngs as musicbrainzngs
from lib.musicbrainzngs import WebServiceError

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
    
    musicbrainzngs.set_useragent("headphones","0.0","https://github.com/rembo10/headphones")
    musicbrainzngs.set_hostname(mbhost + ":" + str(mbport))
    if sleepytime == 0:
        musicbrainzngs.set_rate_limit(False)
    else:
        musicbrainzngs.set_rate_limit(True)

    # Add headphones credentials
    if headphones.MIRROR == "headphones":
        if not mbuser and mbpass:
            logger.warn("No username or password set for VIP server")
        else:
            musicbrainzngs.hpauth(mbuser,mbpass)

    # Don't really need to return q anymore since ngs, but maybe we can return an 'initialized=True' instead?
    q = musicbrainzngs
    
    logger.debug('Using the following server values:\nMBHost: %s ; MBPort: %i  ;  Sleep Interval: %i ' % (mbhost, mbport, sleepytime))
    
    return (q, sleepytime)

def findArtist(name, limit=1):

    with mb_lock:       
        artistlist = []
        artistResults = None
        
        chars = set('!?*')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        q, sleepytime = startmb(forcemb=True)

        try:
            artistResults = musicbrainzngs.search_artists(query=name,limit=limit)['artist-list']
        except WebServiceError, e:
            logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
            time.sleep(5)
        
        time.sleep(sleepytime)
        
        if not artistResults:
            return False        
        for result in artistResults:
            if 'disambiguation' in result:
                uniquename = unicode(result['sort-name'] + " (" + result['disambiguation'] + ")")
            else:
                uniquename = unicode(result['sort-name'])
            if result['name'] != uniquename and limit == 1:
                logger.info('Found an artist with a disambiguation: %s - doing an album based search' % name)
                artistdict = findArtistbyAlbum(name)                
                if not artistdict:
                    logger.info('Cannot determine the best match from an artist/album search. Using top match instead')
                    artistlist.append({
                    # Just need the artist id if the limit is 1
                    #    'name':             unicode(result['sort-name']),
                    #    'uniquename':        uniquename,
                        'id':                unicode(result['id']),
                    #    'url':                 unicode("http://musicbrainz.org/artist/" + result['id']),#probably needs to be changed
                    #    'score':            int(result['ext:score'])
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
        releaselistngs = []
        releaseResultsngs = None
        
        chars = set('!?')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        q, sleepytime = startmb(forcemb=True)
        
        try:
            releaseResultsngs = musicbrainzngs.search_releases(query=name,limit=limit)['release-list']
        except WebServiceError, e: #need to update exceptions
            logger.warn('Attempt to query MusicBrainz for "%s" failed: %s' % (name, str(e)))
            time.sleep(5)
        
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
        
        q, sleepytime = startmb()
        
        try:
            limit = 100
            artist = musicbrainzngs.get_artist_by_id(artistid)['artist']
            newRgs = None
            artist['release-group-list'] = []
            while newRgs == None or len(newRgs) >= limit:
                newRgs = musicbrainzngs.browse_release_groups(artistid,release_type="album",offset=len(artist['release-group-list']),limit=limit)['release-group-list'] 
                artist['release-group-list'] += newRgs
        except WebServiceError, e:
            logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s (%s)' % (artistid, str(e))) 
            time.sleep(5)
        except Exception,e:
            pass
        
        if not artist:
            return False
        
        time.sleep(sleepytime)
        
        #if 'disambiguation' in artist:
        #    uniquename = unicode(artist['sort-name'] + " (" + artist['disambiguation'] + ")")
        #else:
        #    uniquename = unicode(artist['sort-name'])
        
        artist_dict['artist_name'] = unicode(artist['name'])
        
        # Not using the following values anywhere yet so we don't need to grab them.
        # Was causing an exception to be raised if they didn't exist.
        # 
        #artist_dict['artist_sortname'] = unicode(artist['sort-name'])
        #artist_dict['artist_uniquename'] = uniquename
        #artist_dict['artist_type'] = unicode(artist['type'])

        #artist_dict['artist_begindate'] = None
        #artist_dict['artist_enddate'] = None
        #if 'life-span' in artist:
        #    if 'begin' in artist['life-span']:
        #        artist_dict['artist_begindate'] = unicode(artist['life-span']['begin'])
        #    if 'end' in artist['life-span']:
        #        artist_dict['artist_enddate'] = unicode(artist['life-span']['end'])      

                
        
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
            includes = ["single", "ep", "compilation", "soundtrack", "live", "remix", "spokenword", "audiobook"]
            for include in includes:
                
                artist = None
                
                try:
                    artist = musicbrainzngs.get_artist_by_id(artistid,includes=["releases","release-groups"],release_status=['official'],release_type=include)['artist']
                except WebServiceError, e:
                    logger.warn('Attempt to retrieve artist information from MusicBrainz failed for artistid: %s (%s)' % (artistid, str(e)))
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
        
        releaseGroup = None
        
        q, sleepytime = startmb()
        
        try:
            releaseGroup = musicbrainzngs.get_release_group_by_id(rgid,["artists","releases","media","discids",])['release-group']
        except WebServiceError, e:
            logger.warn('Attempt to retrieve information from MusicBrainz for release group "%s" failed (%s)' % (rgid, str(e)))
            time.sleep(5)
        
        if not releaseGroup:
            return False
        
            
        time.sleep(sleepytime)
        
        # I think for now we have to make separate queries for each release, in order
        # to get more detailed release info (ASIN, track count, etc.)
        for release in releaseGroup['release-list']:
            releaseResult = None
            
            try:
                releaseResult = musicbrainzngs.get_release_by_id(release['id'],["recordings","media"])['release']
            except WebServiceError, e:
                logger.warn('Attempt to retrieve release information for %s from MusicBrainz failed (%s)' % (releaseResult.title, str(e)))
                time.sleep(5) 

            if not releaseResult:
                continue               

            if releaseGroup['type'] == 'live' and releaseResult['status'] != 'Official':
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
                
            countries = {
                'US':    '0',

               'GB':    '1',
                'JP':    '2',
                }
            try:
                format = int(formats[releaseResult['medium-list'][0]['format']])
            except:
                format = 3
                
            try:
                country = int(countries[releaseResult['country']])                
            except:
                country = 3
            totalTracks = 0
            tracks = []
            for medium in releaseResult['medium-list']:                
                for track in medium['track-list']:
                    tracks.append({
                        'number':        totalTracks + 1,
                        'title':        unicode(track['recording']['title']),
                        'id':            unicode(track['recording']['id']),
                        'url':            u"http://musicbrainz.org/track/" + track['recording']['id'],
                        'duration':        int(track['recording']['length'] if 'length' in track['recording'] else track['length'] if 'length' in track else 0)
                        })
                    totalTracks += 1
                
            release_dict = {
                'hasasin':        bool(releaseResult.get('asin')),
                'asin':            unicode(releaseResult.get('asin')) if 'asin' in releaseResult else None,
                'trackscount':    totalTracks,
                'releaseid':      unicode(releaseResult.get('id')),
                'releasedate':    unicode(releaseResult.get('date')) if 'date' in releaseResult else None,
                'format':        format,
                'country':        country
                }
            release_dict['tracks'] = tracks
            releaselist.append(release_dict)
        #necessary to make dates that miss the month and/or day show up after full dates
        def getSortableReleaseDate(releaseDate):
            if releaseDate == None:
                return 'None';#change this value to change the sorting behaviour of none, returning 'None' will put it at the top 
                              #which was normal behaviour for pre-ngs versions
            if releaseDate.count('-') == 2:
                return releaseDate
            elif releaseDate.count('-') == 1:
                return releaseDate + '32'
            else:
                return releaseDate + '13-32'
        
        releaselist.sort(key=lambda x:getSortableReleaseDate(x['releasedate']))

        
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
                        'artist_name'    : unicode(releaseGroup['artist-credit'][0]['artist']['name']),
                        'artist_id'        : unicode(releaseGroup['artist-credit'][0]['artist']['id']),
                        'title'            : unicode(releaseGroup['title']),
                        'type'            : unicode(releaseGroup['type'])
                        }
        
        return release_dict
    
def getRelease(releaseid):
    """
    Deep release search to get track info
    """
    with mb_lock:
    
        release = {}
        results = None
        
        q, sleepytime = startmb()
        
        try:
            results = musicbrainzngs.get_release_by_id(releaseid,["artists","release-groups","media","recordings"]).get('release')
        except WebServiceError, e:
            logger.warn('Attempt to retrieve information from MusicBrainz for release "%s" failed (%s)' % (releaseid, str(e)))
            time.sleep(5)    
        
        if not results:
            return False
        
        time.sleep(sleepytime)

        release['title'] = unicode(results['title'])
        release['id'] = unicode(results['id']) 
        release['asin'] = unicode(results['asin']) if 'asin' in results else None 
        release['date'] = unicode(results['date'])

        if 'release-group' in results:
            release['rgid'] = unicode(results['release-group']['id'])
            release['rg_title'] = unicode(results['release-group']['title'])
            release['rg_type'] = unicode(results['release-group']['type'])
        else:
            logger.warn("Release " + releaseid + "had no ReleaseGroup associated")

        release['artist_name'] = unicode(results['artist-credit'][0]['artist']['name'])
        release['artist_id'] = unicode(results['artist-credit'][0]['artist']['id'])
                

        totalTracks = 0
        tracks = []
        for medium in results['medium-list']:                
            for track in medium['track-list']:
                tracks.append({
                        'number':        totalTracks + 1,
                        'title':        unicode(track['recording']['title']),
                        'id':            unicode(track['recording']['id']),
                        'url':            u"http://musicbrainz.org/track/" + track['recording']['id'],
                        'duration':        int(track['length']) if 'length' in track else 0
                        })
                totalTracks += 1       

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

    results = None
    
    q, sleepytime = startmb(forcemb=True)
    
    try:
        results = musicbrainzngs.search_release_groups(term).get('release-group-list')
    except WebServiceError, e:
        logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
        time.sleep(5)    
    
    time.sleep(sleepytime)
    
    if not results:
        return False

    artist_dict = {}
    for releaseGroup in results:
        newArtist = releaseGroup['artist-credit'][0]['artist']         
        # Only need the artist ID if we're doing an artist+album lookup
        #if 'disambiguation' in newArtist:
        #    uniquename = unicode(newArtist['sort-name'] + " (" + newArtist['disambiguation'] + ")")
        #else:
        #    uniquename = unicode(newArtist['sort-name'])
        #artist_dict['name'] = unicode(newArtist['sort-name'])
        #artist_dict['uniquename'] = uniquename
        artist_dict['id'] = unicode(newArtist['id'])
        #artist_dict['url'] = u'http://musicbrainz.org/artist/' + newArtist['id']
        #artist_dict['score'] = int(releaseGroup['ext:score'])

    
    
    return artist_dict
    
def findAlbumID(artist=None, album=None):

    results_ngs = None
    
    q, sleepytime = startmb(forcemb=True)
    
    try:
        term = '"'+album+'" AND artist:"'+artist+'"'
        results_ngs = musicbrainzngs.search_release_groups(term,1).get('release-group-list')
    except WebServiceError, e:
        logger.warn('Attempt to query MusicBrainz for %s - %s failed (%s)' % (artist, album, str(e)))
        time.sleep(5)
    
    time.sleep(sleepytime)
    
    if not results_ngs:
        return False

    if len(results_ngs) < 1:
        return False    
    rgid_ngs = unicode(results_ngs[0]['id'])
    return rgid_ngs
