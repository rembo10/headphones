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

def libraryScan(dir=None):

    if not dir:
        dir = headphones.MUSIC_DIR
        
    dir = dir.encode(headphones.SYS_ENCODING)
        
    if not os.path.isdir(dir):
        logger.warn('Cannot find directory: %s. Not scanning' % dir.decode(headphones.SYS_ENCODING))
        return

    myDB = db.DBConnection()
    
    # Clean up bad filepaths
    tracks = myDB.select('SELECT Location, TrackID from tracks WHERE Location IS NOT NULL')
    
    for track in tracks:
        if not os.path.isfile(track['Location'].encode(headphones.SYS_ENCODING)):
            myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [None, None, None, track['TrackID']])

    logger.info('Scanning music directory: %s' % dir)

    new_artists = []
    bitrates = []

    myDB.action('DELETE from have')
    
    for r,d,f in os.walk(dir):
        for files in f:
            # MEDIA_FORMATS = music file extensions, e.g. mp3, flac, etc
            if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):

                song = os.path.join(r, files)

                # We need the unicode path to use for logging, inserting into database
                unicode_song_path = song.decode(headphones.SYS_ENCODING, errors='replace')

                # Try to read the metadata
                try:
                    f = MediaFile(song)

                except:
                    logger.error('Cannot read file: ' + unicode_song_path)
                    continue
                    
                # Grab the bitrates for the auto detect bit rate option
                if f.bitrate:
                    bitrates.append(f.bitrate)
                
                # Try to find a match based on artist/album/tracktitle
                if f.albumartist:
                    f_artist = f.albumartist
                elif f.artist:
                    f_artist = f.artist
                else:
                    continue
                
                if f_artist and f.album and f.title:

                    track = myDB.action('SELECT TrackID from tracks WHERE CleanName LIKE ?', [helpers.cleanName(f_artist +' '+f.album+' '+f.title)]).fetchone()
                        
                    if not track:
                        track = myDB.action('SELECT TrackID from tracks WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?', [f_artist, f.album, f.title]).fetchone()
                    
                    if track:
                        myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [unicode_song_path, f.bitrate, f.format, track['TrackID']])
                        continue        
                
                # Try to match on mbid if available and we couldn't find a match based on metadata
                if f.mb_trackid:

                    # Wondering if theres a better way to do this -> do one thing if the row exists,
                    # do something else if it doesn't
                    track = myDB.action('SELECT TrackID from tracks WHERE TrackID=?', [f.mb_trackid]).fetchone()
        
                    if track:
                        myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE TrackID=?', [unicode_song_path, f.bitrate, f.format, track['TrackID']])
                        continue                
                
                # if we can't find a match in the database on a track level, it might be a new artist or it might be on a non-mb release
                new_artists.append(f_artist)
                
                # The have table will become the new database for unmatched tracks (i.e. tracks with no associated links in the database                
                myDB.action('INSERT INTO have (ArtistName, AlbumTitle, TrackNumber, TrackTitle, TrackLength, BitRate, Genre, Date, TrackID, Location, CleanName, Format) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [f_artist, f.album, f.track, f.title, f.length, f.bitrate, f.genre, f.date, f.mb_trackid, unicode_song_path, helpers.cleanName(f_artist+' '+f.album+' '+f.title), f.format])

    logger.info('Completed scanning directory: %s' % dir)
    
    # Clean up the new artist list
    unique_artists = {}.fromkeys(new_artists).keys()
    current_artists = myDB.select('SELECT ArtistName, ArtistID from artists')
    
    artist_list = [f for f in unique_artists if f.lower() not in [x[0].lower() for x in current_artists]]
    
    # Update track counts
    logger.info('Updating track counts')

    for artist in current_artists:
        havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID like ? AND Location IS NOT NULL', [artist['ArtistID']])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['ArtistName']]))
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
