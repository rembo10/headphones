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
from headphones import logger, db, helpers
from headphones.helpers import multikeysort, replace_all

import lib.musicbrainzngs as musicbrainzngs
from lib.musicbrainzngs import WebServiceError

mb_lock = threading.Lock()


# Quick fix to add mirror switching on the fly. Need to probably return the mbhost & mbport that's
# being used, so we can send those values to the log
def startmb():

    mbuser = None
    mbpass = None
    
    if headphones.MIRROR == "musicbrainz.org":
        mbhost = "musicbrainz.org"
        mbport = 80
        sleepytime = 1
    elif headphones.MIRROR == "custom":
        mbhost = headphones.CUSTOMHOST
        mbport = int(headphones.CUSTOMPORT)
        sleepytime = int(headphones.CUSTOMSLEEP)
    elif headphones.MIRROR == "headphones":
        mbhost = "144.76.94.239"
        mbport = 8181
        mbuser = headphones.HPUSER
        mbpass = headphones.HPPASS
        sleepytime = 0
    else:
        return False
    
    musicbrainzngs.set_useragent("headphones","0.0","https://github.com/rembo10/headphones")
    musicbrainzngs.set_hostname(mbhost + ":" + str(mbport))
    if sleepytime == 0:
        musicbrainzngs.set_rate_limit(False)
    else:
        #calling it with an it ends up blocking all requests after the first
        musicbrainzngs.set_rate_limit(limit_or_interval=float(sleepytime))

    # Add headphones credentials
    if headphones.MIRROR == "headphones":
        if not mbuser and mbpass:
            logger.warn("No username or password set for VIP server")
        else:
            musicbrainzngs.hpauth(mbuser,mbpass)
    
    logger.debug('Using the following server values: MBHost: %s, MBPort: %i, Sleep Interval: %i', mbhost, mbport, sleepytime)
    
    return True

def findArtist(name, limit=1):

    with mb_lock:       
        artistlist = []
        artistResults = None
        
        chars = set('!?*')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        try:
            artistResults = musicbrainzngs.search_artists(query='artist:'+name,limit=limit)['artist-list']
        except WebServiceError, e:
            logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
            time.sleep(5)
        
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
                        'uniquename':       uniquename,
                        'id':               unicode(result['id']),
                        'url':              unicode("http://musicbrainz.org/artist/" + result['id']),#probably needs to be changed
                        'score':            int(result['ext:score'])
                        })
        return artistlist
        
def findRelease(name, limit=1):

    with mb_lock:        
        releaselist = []
        releaseResults = None
        
        chars = set('!?')
        if any((c in chars) for c in name):
            name = '"'+name+'"'
            
        try:
            releaseResults = musicbrainzngs.search_releases(query=name,limit=limit)['release-list']
        except WebServiceError, e: #need to update exceptions
            logger.warn('Attempt to query MusicBrainz for "%s" failed: %s' % (name, str(e)))
            time.sleep(5)

        if not releaseResults:
            return False
        for result in releaseResults:
                        releaselist.append({
                        'uniquename':        unicode(result['artist-credit'][0]['artist']['name']),
                        'title':             unicode(result['title']),
                        'id':                unicode(result['artist-credit'][0]['artist']['id']),
                        'albumid':           unicode(result['id']),
                        'url':               unicode("http://musicbrainz.org/artist/" + result['artist-credit'][0]['artist']['id']),#probably needs to be changed
                        'albumurl':          unicode("http://musicbrainz.org/release/" + result['id']),#probably needs to be changed
                        'score':             int(result['ext:score'])
                        })            
        return releaselist

def getArtist(artistid, extrasonly=False):

    with mb_lock:    
        artist_dict = {}
    
        artist = None
        
        try:
            limit = 200
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
                            'title':      unicode(rg['title']),
                            'id':         unicode(rg['id']),
                            'url':        u"http://musicbrainz.org/release-group/" + rg['id'],
                            'type':       unicode(rg['type'])
                    })               
                
        # See if we need to grab extras. Artist specific extras take precedence over global option
        # Global options are set when adding a new artist
        myDB = db.DBConnection()

        try:
            db_artist = myDB.action('SELECT IncludeExtras, Extras from artists WHERE ArtistID=?', [artistid]).fetchone()
            includeExtras = db_artist['IncludeExtras']
        except IndexError:
            includeExtras = False
        
        if includeExtras:
            
            # Need to convert extras string from something like '2,5.6' to ['ep','live','remix']
            extras = db_artist['Extras']
            extras_list = ["single", "ep", "compilation", "soundtrack", "live", "remix", "spokenword", "audiobook", "other"]
            includes = []
            
            i = 1
            for extra in extras_list:
                if str(i) in extras:
                    includes.append(extra)
                i += 1

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
                            'id':           unicode(rg['id']),
                            'url':          u"http://musicbrainz.org/release-group/" + rg['id'],
                            'type':         unicode(rg['type'])
                        })            
            
        artist_dict['releasegroups'] = releasegroups
        
        return artist_dict
        
def getReleaseGroup(rgid):
    """
    Returns a list of releases in a release group
    """
    with mb_lock:
    
        releaselist = []
        
        releaseGroup = None
               
        try:
            releaseGroup = musicbrainzngs.get_release_group_by_id(rgid,["artists","releases","media","discids",])['release-group']
        except WebServiceError, e:
            logger.warn('Attempt to retrieve information from MusicBrainz for release group "%s" failed (%s)' % (rgid, str(e)))
            time.sleep(5)
        
        if not releaseGroup:
            return False
        else:
            return releaseGroup['release-list']
    
def getRelease(releaseid, include_artist_info=True):
    """
    Deep release search to get track info
    """
    with mb_lock:
    
        release = {}
        results = None
        
        try:
            if include_artist_info:
                results = musicbrainzngs.get_release_by_id(releaseid,["artists","release-groups","media","recordings"]).get('release')
            else:
                results = musicbrainzngs.get_release_by_id(releaseid,["media","recordings"]).get('release')
        except WebServiceError, e:
            logger.warn('Attempt to retrieve information from MusicBrainz for release "%s" failed (%s)' % (releaseid, str(e)))
            time.sleep(5)    
        
        if not results:
            return False

        release['title'] = unicode(results['title'])
        release['id'] = unicode(results['id']) 
        release['asin'] = unicode(results['asin']) if 'asin' in results else None
        release['date'] = unicode(results['date']) if 'date' in results else None
        try:
            release['format'] = unicode(results['medium-list'][0]['format'])
        except:
            release['format'] = u'Unknown'
        
        try:
            release['country'] = unicode(results['country'])
        except:
            release['country'] = u'Unknown'
        

        if include_artist_info:
        
            if 'release-group' in results:
                release['rgid'] = unicode(results['release-group']['id'])
                release['rg_title'] = unicode(results['release-group']['title'])
                try:
                    release['rg_type'] = unicode(results['release-group']['type'])
                except KeyError:
                    release['rg_type'] = u'Unknown'
            else:
                logger.warn("Release " + releaseid + "had no ReleaseGroup associated")

            release['artist_name'] = unicode(results['artist-credit'][0]['artist']['name'])
            release['artist_id'] = unicode(results['artist-credit'][0]['artist']['id'])

        release['tracks'] = getTracksFromRelease(results)
        
        return release

def get_new_releases(rgid,includeExtras=False,forcefull=False):

    myDB = db.DBConnection()
    results = []
    try:
        limit = 100
        newResults = None
        while newResults == None or len(newResults) >= limit:
            newResults = musicbrainzngs.browse_releases(release_group=rgid,includes=['artist-credits','labels','recordings','release-groups','media'],limit=limit,offset=len(results))
            if 'release-list' not in newResults:
                break #may want to raise an exception here instead ?
            newResults = newResults['release-list']
            results += newResults
            
    except WebServiceError, e:
        logger.warn('Attempt to retrieve information from MusicBrainz for release group "%s" failed (%s)' % (rgid, str(e)))
        time.sleep(5)
        return False
        
    if not results or len(results) == 0:
        return False

    #Clean all references to releases in dB that are no longer referenced in musicbrainz
    release_list = []
    force_repackage1 = 0
    if len(results) != 0:
        for release_mark in results:
            release_list.append(unicode(release_mark['id']))
            release_title = release_mark['title']
        remove_missing_releases = myDB.action("SELECT ReleaseID FROM allalbums WHERE AlbumID=?", [rgid])
        if remove_missing_releases:
            for items in remove_missing_releases:
                if items['ReleaseID'] not in release_list and items['ReleaseID'] != rgid:
                    # Remove all from albums/tracks that aren't in release
                    myDB.action("DELETE FROM albums WHERE ReleaseID=?", [items['ReleaseID']])
                    myDB.action("DELETE FROM tracks WHERE ReleaseID=?", [items['ReleaseID']])
                    myDB.action("DELETE FROM allalbums WHERE ReleaseID=?", [items['ReleaseID']])
                    myDB.action("DELETE FROM alltracks WHERE ReleaseID=?", [items['ReleaseID']])
                    logger.info("Removing all references to release %s to reflect MusicBrainz" % items['ReleaseID'])
                    force_repackage1 = 1
    else:
        logger.info("There was either an error pulling data from MusicBrainz or there might not be any releases for this category")

    num_new_releases = 0

    for releasedata in results:
        #releasedata.get will return None if it doesn't have a status
        #all official releases should have the Official status included
        if not includeExtras and releasedata.get('status') != 'Official':
            continue
        
        release = {}
        rel_id_check = releasedata['id']
        artistid = unicode(releasedata['artist-credit'][0]['artist']['id'])

        album_checker = myDB.action('SELECT * from allalbums WHERE ReleaseID=?', [rel_id_check]).fetchone()
        if not album_checker or forcefull:
            #DELETE all references to this release since we're updating it anyway.
            myDB.action('DELETE from allalbums WHERE ReleaseID=?', [rel_id_check])
            myDB.action('DELETE from alltracks WHERE ReleaseID=?', [rel_id_check])
            release['AlbumTitle'] = unicode(releasedata['title'])
            release['AlbumID'] = unicode(rgid)
            release['AlbumASIN'] = unicode(releasedata['asin']) if 'asin' in releasedata else None
            release['ReleaseDate'] = unicode(releasedata['date']) if 'date' in releasedata else None      
            release['ReleaseID'] = releasedata['id']
            if 'release-group' not in releasedata:
                raise Exception('No release group associated with release id ' + releasedata['id'] + ' album id' + rgid)
            release['Type'] = unicode(releasedata['release-group']['type'])


            #making the assumption that the most important artist will be first in the list
            if 'artist-credit' in releasedata:
                release['ArtistID'] = unicode(releasedata['artist-credit'][0]['artist']['id'])
                release['ArtistName'] = unicode(releasedata['artist-credit-phrase'])
            else:
                logger.warn('Release ' + releasedata['id'] + ' has no Artists associated.')
                return False
                    

            release['ReleaseCountry'] = unicode(releasedata['country']) if 'country' in releasedata else u'Unknown'
            #assuming that the list will contain media and that the format will be consistent
            try:
                additional_medium=''
                for position in releasedata['medium-list']:
                    if position['format'] == releasedata['medium-list'][0]['format']:
                        medium_count = int(position['position'])
                    else:
                        additional_medium = additional_medium+' + '+position['format']
                if medium_count == 1:
                    disc_number = ''
                else:
                    disc_number = str(medium_count)+'x'
                packaged_medium = disc_number+releasedata['medium-list'][0]['format']+additional_medium
                release['ReleaseFormat'] = unicode(packaged_medium)
            except:
                release['ReleaseFormat'] = u'Unknown'
     
            release['Tracks'] = getTracksFromRelease(releasedata)

        # What we're doing here now is first updating the allalbums & alltracks table to the most
        # current info, then moving the appropriate release into the album table and its associated
        # tracks into the tracks table
            controlValueDict = {"ReleaseID" : release['ReleaseID']}

            newValueDict = {"ArtistID":         release['ArtistID'],
                            "ArtistName":       release['ArtistName'],
                            "AlbumTitle":       release['AlbumTitle'],
                            "AlbumID":          release['AlbumID'],
                            "AlbumASIN":        release['AlbumASIN'],
                            "ReleaseDate":      release['ReleaseDate'],
                            "Type":             release['Type'],
                            "ReleaseCountry":   release['ReleaseCountry'],
                            "ReleaseFormat":    release['ReleaseFormat']
                        }

            myDB.upsert("allalbums", newValueDict, controlValueDict)
            
            for track in release['Tracks']:

                cleanname = helpers.cleanName(release['ArtistName'] + ' ' + release['AlbumTitle'] + ' ' + track['title'])
        
                controlValueDict = {"TrackID":      track['id'],
                                    "ReleaseID":    release['ReleaseID']}

                newValueDict = {"ArtistID":         release['ArtistID'],
                                "ArtistName":       release['ArtistName'],
                                "AlbumTitle":       release['AlbumTitle'],
                                "AlbumID":          release['AlbumID'],
                                "AlbumASIN":        release['AlbumASIN'],
                                "TrackTitle":       track['title'],
                                "TrackDuration":    track['duration'],
                                "TrackNumber":      track['number'],
                                "CleanName":        cleanname
                            }
                            
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE CleanName=?', [cleanname]).fetchone()
            
                if not match:
                    match = myDB.action('SELECT Location, BitRate, Format from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [release['ArtistName'], release['AlbumTitle'], track['title']]).fetchone()
                #if not match:
                    #match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()         
                if match:
                    newValueDict['Location'] = match['Location']
                    newValueDict['BitRate'] = match['BitRate']
                    newValueDict['Format'] = match['Format']
                    #myDB.action('UPDATE have SET Matched="True" WHERE Location=?', [match['Location']])
                    myDB.action('UPDATE have SET Matched=? WHERE Location=?', (release['AlbumID'], match['Location']))
                                
                myDB.upsert("alltracks", newValueDict, controlValueDict)
            num_new_releases = num_new_releases + 1
            #print releasedata['title']
            #print num_new_releases
            if album_checker:
                logger.info('[%s] Existing release %s (%s) updated' % (release['ArtistName'], release['AlbumTitle'], rel_id_check))
            else:
                logger.info('[%s] New release %s (%s) added' % (release['ArtistName'], release['AlbumTitle'], rel_id_check))
    if force_repackage1 == 1:
        num_new_releases = -1
        logger.info('[%s] Forcing repackage of %s, since dB releases have been removed' % (release['ArtistName'], release_title))
    else:
        num_new_releases = num_new_releases

    return num_new_releases

def getTracksFromRelease(release):
    totalTracks = 1
    tracks = []
    for medium in release['medium-list']:
        for track in medium['track-list']:
            try:
                track_title = unicode(track['title'])
            except:
                track_title = unicode(track['recording']['title'])
            tracks.append({
                    'number':        totalTracks,
                    'title':         track_title,
                    'id':            unicode(track['recording']['id']),
                    'url':           u"http://musicbrainz.org/track/" + track['recording']['id'],
                    'duration':      int(track['length']) if 'length' in track else 0
                    })
            totalTracks += 1      
    return tracks

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
    
    try:
        results = musicbrainzngs.search_release_groups(term).get('release-group-list')
    except WebServiceError, e:
        logger.warn('Attempt to query MusicBrainz for %s failed (%s)' % (name, str(e)))
        time.sleep(5)    
    
    
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

    results = None
    
    try:
        if album and artist:
            term = '"'+album+'" AND artist:"'+artist+'"'
        else:
            term = album
        results = musicbrainzngs.search_release_groups(term,1).get('release-group-list')
    except WebServiceError, e:
        logger.warn('Attempt to query MusicBrainz for %s - %s failed (%s)' % (artist, album, str(e)))
        time.sleep(5)

    if not results:
        return False

    if len(results) < 1:
        return False    
    rgid = unicode(results[0]['id'])
    return rgid
