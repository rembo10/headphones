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

from lib.pyItunes import *
import time
import os
from lib.beets.mediafile import MediaFile

import headphones
from headphones import logger, helpers, db, mb, albumart, lastfm

various_artists_mbid = '89ad4ac3-39f7-470e-963a-56509c546377'
        
def is_exists(artistid):

    myDB = db.DBConnection()
    
    # See if the artist is already in the database
    artistlist = myDB.select('SELECT ArtistID, ArtistName from artists WHERE ArtistID=?', [artistid])

    if any(artistid in x for x in artistlist):
        logger.info(artistlist[0][1] + u" is already in the database. Updating 'have tracks', but not artist information")
        return True
    else:
        return False


def artistlist_to_mbids(artistlist, forced=False):

    for artist in artistlist:
            
        results = mb.findArtist(artist, limit=1)
        
        if not results:
            logger.info('No results found for: %s' % artist)
            continue
        
        try:    
            artistid = results[0]['id']
        
        except IndexError:
            logger.info('MusicBrainz query turned up no matches for: %s' % artist)
            continue
            
        # Check if it's blacklisted/various artists (only check if it's not forced, e.g. through library scan auto-add.)
        # Forced example = Adding an artist from Manage New Artists
        myDB = db.DBConnection()
        
        if not forced:
            bl_artist = myDB.action('SELECT * FROM blacklist WHERE ArtistID=?', [artistid]).fetchone()
            if bl_artist or artistid == various_artists_mbid:
                logger.info("Artist ID for '%s' is either blacklisted or Various Artists. To add artist, you must do it manually (Artist ID: %s)" % (artist, artistid))
                continue
        
        # Add to database if it doesn't exist
        if not is_exists(artistid):
            addArtisttoDB(artistid)
        
        # Just update the tracks if it does
        else:
            havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=?', [artistid])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist]))
            myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, artistid])
            
        # Delete it from the New Artists if the request came from there
        if forced:
            myDB.action('DELETE from newartists WHERE ArtistName=?', [artist])
            
    # Update the similar artist tag cloud:
    logger.info('Updating artist information from Last.fm')
    try:
        lastfm.getSimilar()
    except Exception, e:
        logger.warn('Failed to update arist information from Last.fm: %s' % e)
        
def addArtistIDListToDB(artistidlist):
    # Used to add a list of artist IDs to the database in a single thread
    logger.debug("Importer: Adding artist ids %s" % artistidlist)
    for artistid in artistidlist:
        addArtisttoDB(artistid)

def addArtisttoDB(artistid, extrasonly=False):
    
    # Putting this here to get around the circular import. We're using this to update thumbnails for artist/albums
    from headphones import cache
    
    # Can't add various artists - throws an error from MB
    if artistid == various_artists_mbid:
        logger.warn('Cannot import Various Artists.')
        return
        
    myDB = db.DBConnection()
    
    # Delete from blacklist if it's on there
    myDB.action('DELETE from blacklist WHERE ArtistID=?', [artistid])

    # We need the current minimal info in the database instantly
    # so we don't throw a 500 error when we redirect to the artistPage

    controlValueDict = {"ArtistID":     artistid}

    # Don't replace a known artist name with an "Artist ID" placeholder

    dbartist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [artistid]).fetchone()
    if dbartist is None:
        newValueDict = {"ArtistName":   "Artist ID: %s" % (artistid),
                "Status":   "Loading"}
    else:
        newValueDict = {"Status":   "Loading"}

    myDB.upsert("artists", newValueDict, controlValueDict)
        
    artist = mb.getArtist(artistid, extrasonly)
    
    if not artist:
        logger.warn("Error fetching artist info. ID: " + artistid)
        if dbartist is None:
            newValueDict = {"ArtistName":   "Fetch failed, try refreshing. (%s)" % (artistid),
                    "Status":   "Active"}
        else:
            newValueDict = {"Status":   "Active"}
        myDB.upsert("artists", newValueDict, controlValueDict)
        return
    
    if artist['artist_name'].startswith('The '):
        sortname = artist['artist_name'][4:]
    else:
        sortname = artist['artist_name']
        

    logger.info(u"Now adding/updating: " + artist['artist_name'])
    controlValueDict = {"ArtistID":     artistid}
    newValueDict = {"ArtistName":       artist['artist_name'],
                    "ArtistSortName":   sortname,
                    "DateAdded":        helpers.today(),
                    "Status":           "Loading"}
    
    if headphones.INCLUDE_EXTRAS:
        newValueDict['IncludeExtras'] = 1
    
    myDB.upsert("artists", newValueDict, controlValueDict)

    for rg in artist['releasegroups']:
        
        rgid = rg['id']
        
        # check if the album already exists
        rg_exists = myDB.action("SELECT * from albums WHERE AlbumID=?", [rg['id']]).fetchone()
                    
        try:    
            releaselist = mb.getReleaseGroup(rgid)
        except Exception, e:
            logger.info('Unable to get release information for %s - there may not be any official releases in this release group' % rg['title'])
            continue
            
        if not releaselist:
            continue
        
        # This will be used later to build a hybrid release     
        fullreleaselist = []
            
        for release in releaselist:
            
            releaseid = release['id']
            
            try:
                releasedict = mb.getRelease(releaseid, include_artist_info=False)
            except Exception, e:
                logger.info('Unable to get release information for %s' % release['id'])
                continue
           
            if not releasedict:
                continue

            controlValueDict = {"ReleaseID":  release['id']}

            newValueDict = {"ArtistID":         artistid,
                            "ArtistName":       artist['artist_name'],
                            "AlbumTitle":       rg['title'],
                            "AlbumID":          rg['id'],
                            "AlbumASIN":        releasedict['asin'],
                            "ReleaseDate":      releasedict['date'],
                            "Type":             rg['type'],
                            "ReleaseCountry":   releasedict['country'],
                            "ReleaseFormat":    releasedict['format']
                        }
                        
            myDB.upsert("allalbums", newValueDict, controlValueDict)
            
            # Build the dictionary for the fullreleaselist
            newValueDict['ReleaseID'] = release['id']
            newValueDict['Tracks'] = releasedict['tracks']
            fullreleaselist.append(newValueDict)
            
            for track in releasedict['tracks']:

                cleanname = helpers.cleanName(artist['artist_name'] + ' ' + rg['title'] + ' ' + track['title'])
        
                controlValueDict = {"TrackID":      track['id'],
                                    "ReleaseID":    release['id']}

                newValueDict = {"ArtistID":         artistid,
                                "ArtistName":       artist['artist_name'],
                                "AlbumTitle":       rg['title'],
                                "AlbumASIN":        releasedict['asin'],
                                "AlbumID":          rg['id'],
                                "TrackTitle":       track['title'],
                                "TrackDuration":    track['duration'],
                                "TrackNumber":      track['number'],
                                "CleanName":        cleanname
                            }
                            
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE CleanName=?', [cleanname]).fetchone()
            
                if not match:
                    match = myDB.action('SELECT Location, BitRate, Format from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [artist['artist_name'], rg['title'], track['title']]).fetchone()
                if not match:
                    match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()         
                if match:
                    newValueDict['Location'] = match['Location']
                    newValueDict['BitRate'] = match['BitRate']
                    newValueDict['Format'] = match['Format']
                    myDB.action('UPDATE tracks SET Matched="True" WHERE Location=?', match['Location'])
                                
                myDB.upsert("alltracks", newValueDict, controlValueDict)

        # Basically just do the same thing again for the hybrid release
        hybridrelease = getHybridRelease(fullreleaselist)
        
        # Use the ReleaseGroupID as the ReleaseID for the hybrid release to differentiate it
        # We can then use the condition WHERE ReleaseID == ReleaseGroupID to select it
        # The hybrid won't have a country or a format
        controlValueDict = {"ReleaseID":  rg['id']}

        newValueDict = {"ArtistID":         artistid,
                        "ArtistName":       artist['artist_name'],
                        "AlbumTitle":       rg['title'],
                        "AlbumID":          rg['id'],
                        "AlbumASIN":        hybridrelease['AlbumASIN'],
                        "ReleaseDate":      hybridrelease['ReleaseDate'],
                        "Type":             rg['type']
                    }
                    
        myDB.upsert("allalbums", newValueDict, controlValueDict)
        
        for track in hybridrelease['Tracks']:

            cleanname = helpers.cleanName(artist['artist_name'] + ' ' + rg['title'] + ' ' + track['title'])
    
            controlValueDict = {"TrackID":      track['id'],
                                "ReleaseID":    rg['id']}

            newValueDict = {"ArtistID":         artistid,
                            "ArtistName":       artist['artist_name'],
                            "AlbumTitle":       rg['title'],
                            "AlbumASIN":        hybridrelease['AlbumASIN'],
                            "AlbumID":          rg['id'],
                            "TrackTitle":       track['title'],
                            "TrackDuration":    track['duration'],
                            "TrackNumber":      track['number'],
                            "CleanName":        cleanname
                        }
                        
            match = myDB.action('SELECT Location, BitRate, Format from have WHERE CleanName=?', [cleanname]).fetchone()
        
            if not match:
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [artist['artist_name'], rg['title'], track['title']]).fetchone()
            if not match:
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()         
            if match:
                newValueDict['Location'] = match['Location']
                newValueDict['BitRate'] = match['BitRate']
                newValueDict['Format'] = match['Format']
                myDB.action('UPDATE tracks SET Matched="True" WHERE Location=?', match['Location'])
                            
            myDB.upsert("alltracks", newValueDict, controlValueDict)
        
        # Delete matched tracks from the have table
        myDB.action('DELETE * from have WHERE Matched="True"')
        
        # If there's no release in the main albums tables, add the default (hybrid)
        # If there is a release, check the ReleaseID against the AlbumID to see if they differ (user updated)
        if not rg_exists:
            releaseid = rg['id']
        elif rg_exists and not rg_exists['ReleaseID']:
            releaseid = rg['id']
        else:
            releaseid = rg_exists['ReleaseID']
        
        album = myDB.select('SELECT * from allallbums WHERE ReleaseID=?', releaseid)

        controlValueDict = {"AlbumID":  rg['id']}

        newValueDict = {"ArtistID":         album['ArtistID'],
                        "ArtistName":       album['ArtistName'],
                        "AlbumTitle":       album['AlbumTitle'],
                        "ReleaseID":        album['ReleaseID'],
                        "AlbumASIN":        album['AlbumASIN'],
                        "ReleaseDate":      album['ReleaseDate'],
                        "Type":             album['Type'],
                        "ReleaseCountry":   album['ReleaseCountry'],
                        "ReleaseFormat":    album['ReleaseFormat']
                    }
            
        if not rg_exists:
            
            newValueDict['DateAdded']= helpers.today()
                            
            if headphones.AUTOWANT_ALL:
                newValueDict['Status'] = "Wanted"
            elif release_dict['releasedate'] > helpers.today() and headphones.AUTOWANT_UPCOMING:
                newValueDict['Status'] = "Wanted"
            else:
                newValueDict['Status'] = "Skipped"
        
        myDB.upsert("albums", newValueDict, controlValueDict)

        myDB.action('DELETE * from tracks WHERE AlbumID=?', rg['id'])
        tracks = myDB.select('SELECT * from alltracks WHERE ReleaseID=?', [releaseid])

        # This is used to see how many tracks you have from an album - to mark it as downloaded. Default is 80%, can be set in config as ALBUM_COMPLETION_PCT
        total_track_count = len(tracks)
        
        for track in tracks:
        
            controlValueDict = {"TrackID":  track['TrackID'],
                                "AlbumID":  rg['id']}

            newValueDict = {"ArtistID":     track['ArtistID'],
                        "ArtistName":       track['ArtistName'],
                        "AlbumTitle":       track['AlbumTitle'],
                        "AlbumASIN":        track['AlbumASIN'],
                        "ReleaseID":        track['ReleaseID'],
                        "TrackTitle":       track['TrackTitle'],
                        "TrackDuration":    track['TrackDuration'],
                        "TrackNumber":      track['TrackNumber'],
                        "CleanName":        track['CleanName'],
                        "Location":         track['Location'],
                        "Format":           track['Format'],
                        "BitRate":          track['BitRate']
                        }
                        
            myDB.upsert("tracks", newValueDict, controlValueDict)

        # Mark albums as downloaded if they have at least 80% (by default, configurable) of the album
        have_track_count = len(myDB.select('SELECT * from tracks WHERE AlbumID=? AND Location IS NOT NULL', [rg['id']]))
        
        if rg_exists:
            if rg_exists['Status'] == 'Skipped' and ((have_track_count/float(total_track_count)) >= (headphones.ALBUM_COMPLETION_PCT/100.0)):
                myDB.action('UPDATE albums SET Status=? WHERE AlbumID=?', ['Downloaded', rg['id']])
        else:
            if ((have_track_count/float(total_track_count)) >= (headphones.ALBUM_COMPLETION_PCT/100.0)):
                myDB.action('UPDATE albums SET Status=? WHERE AlbumID=?', ['Downloaded', rg['id']])

        logger.debug(u"Updating album cache for " + rg['title'])
        cache.getThumb(AlbumID=rg['id'])

    latestalbum = myDB.action('SELECT AlbumTitle, ReleaseDate, AlbumID from albums WHERE ArtistID=? order by ReleaseDate DESC', [artistid]).fetchone()
    totaltracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=?', [artistid]))
    havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL', [artistid])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['artist_name']]))

    controlValueDict = {"ArtistID":     artistid}
    
    if latestalbum:
        newValueDict = {"Status":           "Active",
                        "LatestAlbum":      latestalbum['AlbumTitle'],
                        "ReleaseDate":      latestalbum['ReleaseDate'],
                        "AlbumID":          latestalbum['AlbumID'],
                        "TotalTracks":      totaltracks,
                        "HaveTracks":       havetracks}
    else:
        newValueDict = {"Status":           "Active",
                        "TotalTracks":      totaltracks,
                        "HaveTracks":       havetracks}
                        
    newValueDict['LastUpdated'] = helpers.now()
    
    myDB.upsert("artists", newValueDict, controlValueDict)
    
    logger.debug(u"Updating cache for: " + artist['artist_name'])
    cache.getThumb(ArtistID=artistid)
    
    logger.info(u"Updating complete for: " + artist['artist_name'])
    
def addReleaseById(rid):
    
    myDB = db.DBConnection()

    rgid = None
    artistid = None
    release_dict = None
    results = myDB.select("SELECT albums.ArtistID, releases.ReleaseGroupID from releases, albums WHERE releases.ReleaseID=? and releases.ReleaseGroupID=albums.AlbumID LIMIT 1", [rid])
    for result in results:
        rgid = result['ReleaseGroupID']
        artistid = result['ArtistID']
        logger.debug("Found a cached releaseid : releasegroupid relationship: " + rid + " : " + rgid)
    if not rgid:
        #didn't find it in the cache, get the information from MB
        logger.debug("Didn't find releaseID " + rid + " in the cache. Looking up its ReleaseGroupID")
        try:
            release_dict = mb.getRelease(rid)
        except Exception, e:
            logger.info('Unable to get release information for Release: ' + str(rid) + " " + str(e))
            return
        if not release_dict:
            logger.info('Unable to get release information for Release: ' + str(rid) + " no dict")
            return
        
        rgid = release_dict['rgid']
        artistid = release_dict['artist_id']
    
    #we don't want to make more calls to MB here unless we have to, could be happening quite a lot
    rg_exists = myDB.select("SELECT * from albums WHERE AlbumID=?", [rgid])
    
    #make sure the artist exists since I don't know what happens later if it doesn't
    artist_exists = myDB.select("SELECT * from artists WHERE ArtistID=?", [artistid])
    
    if not artist_exists and release_dict:
        if release_dict['artist_name'].startswith('The '):
            sortname = release_dict['artist_name'][4:]
        else:
            sortname = release_dict['artist_name']
            
    
        logger.info(u"Now manually adding: " + release_dict['artist_name'] + " - with status Paused")
        controlValueDict = {"ArtistID":     release_dict['artist_id']}
        newValueDict = {"ArtistName":       release_dict['artist_name'],
                        "ArtistSortName":   sortname,
                        "DateAdded":        helpers.today(),
                        "Status":           "Paused"}
        
        if headphones.INCLUDE_EXTRAS:
            newValueDict['IncludeExtras'] = 1
        
        myDB.upsert("artists", newValueDict, controlValueDict)
        
    elif not artist_exists and not release_dict:
        logger.error("Artist does not exist in the database and did not get a valid response from MB. Skipping release.")
        return
    
    if not rg_exists and release_dict:  #it should never be the case that we have an rg and not the artist
                                        #but if it is this will fail
        logger.info(u"Now adding-by-id album (" + release_dict['title'] + ") from id: " + rgid)
        controlValueDict = {"AlbumID":  rgid}

        newValueDict = {"ArtistID":         release_dict['artist_id'],
                        "ArtistName":       release_dict['artist_name'],
                        "AlbumTitle":       release_dict['rg_title'],
                        "AlbumASIN":        release_dict['asin'],
                        "ReleaseDate":      release_dict['date'],
                        "DateAdded":        helpers.today(),
                        "Status":           'Wanted',
                        "Type":             release_dict['rg_type']
                        }
        
        myDB.upsert("albums", newValueDict, controlValueDict)

        #keep a local cache of these so that external programs that are adding releasesByID don't hammer MB
        myDB.action('INSERT INTO releases VALUES( ?, ?)', [rid, release_dict['rgid']])
        
        for track in release_dict['tracks']:
        
            cleanname = helpers.cleanName(release_dict['artist_name'] + ' ' + release_dict['rg_title'] + ' ' + track['title'])
            
            controlValueDict = {"TrackID":  track['id'],
                                "AlbumID":  rgid}
            newValueDict = {"ArtistID":     release_dict['artist_id'],
                        "ArtistName":       release_dict['artist_name'],
                        "AlbumTitle":       release_dict['rg_title'],
                        "AlbumASIN":        release_dict['asin'],
                        "TrackTitle":       track['title'],
                        "TrackDuration":    track['duration'],
                        "TrackNumber":      track['number'],
                        "CleanName":        cleanname
                        }
            
            match = myDB.action('SELECT Location, BitRate, Format from have WHERE CleanName=?', [cleanname]).fetchone()
                        
            if not match:
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [release_dict['artist_name'], release_dict['rg_title'], track['title']]).fetchone()
            
            if not match:
                match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()
                    
            if match:
                newValueDict['Location'] = match['Location']
                newValueDict['BitRate'] = match['BitRate']
                newValueDict['Format'] = match['Format']
                myDB.action('DELETE from have WHERE Location=?', [match['Location']])
        
            myDB.upsert("tracks", newValueDict, controlValueDict)
                
        #start a search for the album
        import searcher
        searcher.searchNZB(rgid, False)
    elif not rg_exists and not release_dict:
        logger.error("ReleaseGroup does not exist in the database and did not get a valid response from MB. Skipping release.")
        return
    else:
        logger.info('Release ' + str(rid) + " already exists in the database!")

def updateFormat():
    myDB = db.DBConnection()
    tracks = myDB.select('SELECT * from tracks WHERE Location IS NOT NULL and Format IS NULL')
    if len(tracks) > 0:
        logger.info('Finding media format for %s files' % len(tracks))
        for track in tracks:
            try:
                f = MediaFile(track['Location'])
            except Exception, e:
                logger.info("Exception from MediaFile for: " + track['Location'] + " : " + str(e))
                continue
            controlValueDict = {"TrackID":  track['TrackID']}
            newValueDict = {"Format": f.format}
            myDB.upsert("tracks", newValueDict, controlValueDict)
        logger.info('Finished finding media format for %s files' % len(tracks))
    havetracks = myDB.select('SELECT * from have WHERE Location IS NOT NULL and Format IS NULL')
    if len(havetracks) > 0:
        logger.info('Finding media format for %s files' % len(havetracks))
        for track in havetracks:
            try:
                f = MediaFile(track['Location'])
            except Exception, e:
                logger.info("Exception from MediaFile for: " + track['Location'] + " : " + str(e))
                continue
            controlValueDict = {"TrackID":  track['TrackID']}
            newValueDict = {"Format": f.format}
            myDB.upsert("have", newValueDict, controlValueDict)
        logger.info('Finished finding media format for %s files' % len(havetracks))

def getHybridRelease(fullreleaselist):
    """
    Returns a dictionary of best group of tracks from the list of releases & earliest release date
    """
    sortable_release_list = []
        
    for release in fullreleaselist:

        formats = {
            '2xVinyl':          '2',
            'Vinyl':            '2',
            'CD':               '0',
            'Cassette':         '3',            
            '2xCD':             '1',
            'Digital Media':    '0'
            }
            
        countries = {
            'US':    '0',
            'GB':    '1',
            'JP':    '2',
            }
        
        try:
            format = int(formats[release['Format']])
        except:
            format = 3
            
        try:
            country = int(countries[release['Country']])                
        except:
            country = 3
        
        release_dict = {
            'hasasin':        bool(release['AlbumASIN']),
            'asin':           release['AlbumASIN'],
            'trackscount':    len(release['Tracks']),
            'releaseid':      release['ReleaseID'],
            'releasedate':    release['ReleaseDate'],
            'format':         format,
            'country':        country,
            'tracks':         release['Tracks']
            }

        sortable_release_list.append(release_dict)
        
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

    sortable_release_list.sort(key=lambda x:getSortableReleaseDate(x['releasedate']))

    average_tracks = sum(x['trackscount'] for x in sortable_release_list) / float(len(sortable_release_list))
    for item in sortable_release_list:
        item['trackscount_delta'] = abs(average_tracks - item['trackscount'])
    
    a = multikeysort(sortable_release_list, ['-hasasin', 'country', 'format', 'trackscount_delta'])

    release_dict = {'ReleaseDate'    : sortable_release_list[0]['releasedate'],
                    'Tracks'         : a[0]['tracks'],
                    'AlbumASIN'      : a[0]['asin']
                    }
                
    return release_dict
