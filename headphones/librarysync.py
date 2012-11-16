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

import os
import glob

from lib.beets.mediafile import MediaFile

import headphones
from headphones import db, logger, helpers, importer

# You can scan a single directory and append it to the current library by specifying append=True, ArtistID & ArtistName
def libraryScan(dir=None, append=False, ArtistID=None, ArtistName=None, cron=False):

    if cron and not headphones.LIBRARYSCAN:
        return
        
    if not dir:
        dir = headphones.MUSIC_DIR
    
    # If we're appending a dir, it's coming from the post processor which is
    # already bytestring
    if not append and not isinstance(dir,unicode):
        dir = dir.encode(headphones.SYS_ENCODING)
        
    if not os.path.isdir(dir):
        logger.warn('Cannot find directory: %s. Not scanning' % dir.decode(headphones.SYS_ENCODING, 'replace'))
        return

    myDB = db.DBConnection()
    
    if not append:
        # Clean up bad filepaths
        tracks = myDB.select('SELECT Location, TrackID from tracks WHERE Location IS NOT NULL')
    
        for track in tracks:
            if not os.path.isfile(track['Location'].encode(headphones.SYS_ENCODING)):
                myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [None, None, None, track['TrackID']])

        myDB.action('DELETE from have')

    logger.info('Scanning music directory: %s' % dir.decode(headphones.SYS_ENCODING, 'replace'))

    new_artists = []
    bitrates = []
    
    song_list = []
    
    for r,d,f in os.walk(dir):
        #need to abuse slicing to get a copy of the list, doing it directly will skip the element after a deleted one
        #using a list comprehension will not work correctly for nested subdirectories (os.walk keeps its original list)
        for directory in d[:]:
            if directory.startswith("."):
                d.remove(directory)
        for files in f:
            # MEDIA_FORMATS = music file extensions, e.g. mp3, flac, etc
            if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):

                song = os.path.join(r, files)

                # We need the unicode path to use for logging, inserting into database
                if not isinstance(song,unicode):
                    unicode_song_path = song.decode(headphones.SYS_ENCODING, 'replace')
                else:
                    unicode_song_path = song
                # Try to read the metadata
                try:
                    f = MediaFile(song)

                except Exception as e:
                    logger.error('Cannot read file: ' + unicode_song_path + ' ' + e.message)
                    continue
                    
                # Grab the bitrates for the auto detect bit rate option
                if f.bitrate:
                    bitrates.append(f.bitrate)
                    
                # Use the album artist over the artist if available
                if f.albumartist:
                    f_artist = f.albumartist
                elif f.artist:
                    f_artist = f.artist
                else:
                    f_artist = None
                    
                # Add the song to our song list - 
                # TODO: skip adding songs without the minimum requisite information (just a matter of putting together the right if statements)

                song_dict = { 'TrackID' : f.mb_trackid,
                              'ReleaseID' : f.mb_albumid,
                              'ArtistName' : f_artist,
                              'AlbumTitle' : f.album,
                              'TrackNumber': f.track,
                              'TrackLength': f.length,
                              'Genre'      : f.genre,
                              'Date'       : f.date,
                              'TrackTitle' : f.title,
                              'BitRate'    : f.bitrate,
                              'Format'     : f.format,
                              'Location'   : unicode_song_path }
                              
                song_list.append(song_dict)

    # Now we start track matching
    total_number_of_songs = len(song_list)
    logger.info("Found " + str(total_number_of_songs) + " tracks in: '" + dir.decode(headphones.SYS_ENCODING, 'replace') + "'. Matching tracks to the appropriate releases....")
    
    # Sort the song_list by most vague (e.g. no trackid or releaseid) to most specific (both trackid & releaseid)
    # When we insert into the database, the tracks with the most specific information will overwrite the more general matches
    
    song_list = helpers.multikeysort(song_list, ['ReleaseID', 'TrackID'])
    
    # We'll use this to give a % completion, just because the track matching might take a while
    song_count = 0
    
    for song in song_list:
        
        song_count += 1
        completion_percentage = float(song_count)/total_number_of_songs * 100
        
        if completion_percentage%10 == 0:
            logger.info("Track matching is " + str(completion_percentage) + "% complete")
        
        # If the track has a trackid & releaseid (beets: albumid) that the most surefire way
        # of identifying a track to a specific release so we'll use that first
        if song['TrackID'] and song['ReleaseID']:

            # Check both the tracks table & alltracks table in case they haven't populated the alltracks table yet
            track = myDB.action('SELECT TrackID, ReleaseID, AlbumID from alltracks WHERE TrackID=? AND ReleaseID=?', [song['TrackID'], song['ReleaseID']]).fetchone()
            
            # It might be the case that the alltracks table isn't populated yet, so maybe we can only find a match in the tracks table
            if not track:
                track = myDB.action('SELECT TrackID, ReleaseID, AlbumID from tracks WHERE TrackID=? AND ReleaseID=?', [song['TrackID'], song['ReleaseID']]).fetchone()
    
            if track:
                # Use TrackID & ReleaseID here since there can only be one possible match with a TrackID & ReleaseID query combo
                controlValueDict = { 'TrackID'   : track['TrackID'],
                                     'ReleaseID' : track['ReleaseID'] }
                
                # Insert it into the Headphones hybrid release (ReleaseID == AlbumID)                   
                hybridControlValueDict = { 'TrackID'   : track['TrackID'],
                                           'ReleaseID' : track['AlbumID'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }
                                 
                # Update both the tracks table and the alltracks table using the controlValueDict and hybridControlValueDict
                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)
                
                myDB.upsert("alltracks", newValueDict, hybridControlValueDict)
                myDB.upsert("tracks", newValueDict, hybridControlValueDict)
                
                # Matched. Move on to the next one:
                continue
    
        # If we can't find it with TrackID & ReleaseID, next most specific will be 
        # releaseid + tracktitle, although perhaps less reliable due to a higher 
        # likelihood of variations in the song title (e.g. feat. artists)
        if song['ReleaseID'] and song['TrackTitle']:
    
            track = myDB.action('SELECT TrackID, ReleaseID, AlbumID from alltracks WHERE ReleaseID=? AND TrackTitle=?', [song['ReleaseID'], song['TrackTitle']]).fetchone()
    
            if not track:
                track = myDB.action('SELECT TrackID, ReleaseID, AlbumID from tracks WHERE ReleaseID=? AND TrackTitle=?', [song['ReleaseID'], song['TrackTitle']]).fetchone()
                
            if track:
                # There can also only be one match for this query as well (although it might be on both the tracks and alltracks table)
                # So use both TrackID & ReleaseID as the control values
                controlValueDict = { 'TrackID'   : track['TrackID'],
                                     'ReleaseID' : track['ReleaseID'] }
                                     
                hybridControlValueDict = { 'TrackID'   : track['TrackID'],
                                           'ReleaseID' : track['AlbumID'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }
                                 
                # Update both tables here as well
                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)
                
                myDB.upsert("alltracks", newValueDict, hybridControlValueDict)
                myDB.upsert("tracks", newValueDict, hybridControlValueDict)
                
                # Done
                continue
                
        # Next most specific will be the opposite: a TrackID and an AlbumTitle
        # TrackIDs span multiple releases so if something is on an official album
        # and a compilation, for example, this will match it to the right one
        # However - there may be multiple matches here
        if song['TrackID'] and song['AlbumTitle']:
    
            # Even though there might be multiple matches, we just need to grab one to confirm a match
            track = myDB.action('SELECT TrackID, AlbumTitle from alltracks WHERE TrackID=? AND AlbumTitle LIKE ?', [song['TrackID'], song['AlbumTitle']]).fetchone()
    
            if not track:
                track = myDB.action('SELECT TrackID, AlbumTitle from tracks WHERE TrackID=? AND AlbumTitle LIKE ?', [song['TrackID'], song['AlbumTitle']]).fetchone()
                
            if track:
                # Don't need the hybridControlValueDict here since ReleaseID is not unique
                controlValueDict = { 'TrackID'   : track['TrackID'],
                                     'AlbumTitle' : track['AlbumTitle'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }

                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)

                continue   
        
        # Next most specific is the ArtistName + AlbumTitle + TrackTitle combo (but probably 
        # even more unreliable than the previous queries, and might span multiple releases)
        if song['ArtistName'] and song['AlbumTitle'] and song['TrackTitle']:
            
            track = myDB.action('SELECT ArtistName, AlbumTitle, TrackTitle from alltracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [song['ArtistName'], song['AlbumTitle'], song['TrackTitle']]).fetchone()
    
            if not track:
                track = myDB.action('SELECT ArtistName, AlbumTitle, TrackTitle from tracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [song['ArtistName'], song['AlbumTitle'], song['TrackTitle']]).fetchone()
                
            if track:
                controlValueDict = { 'ArtistName' : track['ArtistName'],
                                     'AlbumTitle' : track['AlbumTitle'],
                                     'TrackTitle' : track['TrackTitle'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }

                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)

                continue
        
        # Use the "CleanName" (ArtistName + AlbumTitle + TrackTitle stripped of punctuation, capitalization, etc)
        # This is more reliable than the former but requires some string manipulation so we'll do it only
        # if we can't find a match with the original data
        if song['ArtistName'] and song['AlbumTitle'] and song['TrackTitle']:
            
            CleanName = helpers.cleanName(song['ArtistName'] +' '+ song['AlbumTitle'] +' '+song['TrackTitle'])
            
            track = myDB.action('SELECT CleanName from alltracks WHERE CleanName LIKE ?', [CleanName]).fetchone()
            
            if not track:
                track = myDB.action('SELECT CleanName from tracks WHERE CleanName LIKE ?', [CleanName]).fetchone()
    
            if track:
                controlValueDict = { 'CleanName' : track['CleanName'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }

                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)

                continue     
        
        # Match on TrackID alone if we can't find it using any of the above methods. This method is reliable
        # but spans multiple releases - but that's why we're putting at the beginning as a last resort. If a track
        # with more specific information exists in the library, it'll overwrite these values
        if song['TrackID']:
    
            track = myDB.action('SELECT TrackID from alltracks WHERE TrackID=?', [song['TrackID']]).fetchone()
            
            if not track:
                track = myDB.action('SELECT TrackID from tracks WHERE TrackID=?', [song['TrackID']]).fetchone()
    
            if track:
                controlValueDict = { 'TrackID' : track['TrackID'] }
                                     
                newValueDict = { 'Location' : song['Location'],
                                 'BitRate'  : song['BitRate'],
                                 'Format'   : song['Format'] }

                myDB.upsert("alltracks", newValueDict, controlValueDict)
                myDB.upsert("tracks", newValueDict, controlValueDict)

                continue          
        
        # if we can't find a match in the database on a track level, it might be a new artist or it might be on a non-mb release
        if song['ArtistName']:
            new_artists.append(song['ArtistName'])
        else:
            continue
        
        # The have table will become the new database for unmatched tracks (i.e. tracks with no associated links in the database                
        if song['ArtistName'] and song['AlbumTitle'] and song['TrackTitle']:
            CleanName = helpers.cleanName(song['ArtistName'] +' '+ song['AlbumTitle'] +' '+song['TrackTitle'])
        else:
            continue
        
        myDB.action('INSERT INTO have (ArtistName, AlbumTitle, TrackNumber, TrackTitle, TrackLength, BitRate, Genre, Date, TrackID, Location, CleanName, Format) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [song['ArtistName'], song['AlbumTitle'], song['TrackNumber'], song['TrackTitle'], song['TrackLength'], song['BitRate'], song['Genre'], song['Date'], song['TrackID'], song['Location'], CleanName, song['Format']])

    logger.info('Completed matching tracks from directory: %s' % dir.decode(headphones.SYS_ENCODING, 'replace'))
    
    
    if not append:
        # Clean up the new artist list
        unique_artists = {}.fromkeys(new_artists).keys()
        current_artists = myDB.select('SELECT ArtistName, ArtistID from artists')
        
        artist_list = [f for f in unique_artists if f.lower() not in [x[0].lower() for x in current_artists]]
        
        # Update track counts
        logger.info('Updating current artist track counts')
    
        for artist in current_artists:
            # Have tracks are selected from tracks table and not all tracks because of duplicates
            # We update the track count upon an album switch to compliment this
            havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL', [artist['ArtistID']])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['ArtistName']]))
            myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, artist['ArtistID']])
            
        logger.info('Found %i new artists' % len(artist_list))
    
        if len(artist_list):
            if headphones.ADD_ARTISTS:
                logger.info('Importing %i new artists' % len(artist_list))
                importer.artistlist_to_mbids(artist_list)
            else:
                logger.info('To add these artists, go to Manage->Manage New Artists')
                myDB.action('DELETE from newartists')
                for artist in artist_list:
                    myDB.action('INSERT into newartists VALUES (?)', [artist])
        
        if headphones.DETECT_BITRATE:
            headphones.PREFERRED_BITRATE = sum(bitrates)/len(bitrates)/1000
            
    else:
        # If we're appending a new album to the database, update the artists total track counts
        logger.info('Updating artist track counts')
        
        havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL', [ArtistID])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [ArtistName]))
        myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, ArtistID])
