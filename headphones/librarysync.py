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
import math

import headphones
from mediafile import MediaFile, FileTypeError, UnreadableFileError
from headphones import db, logger, helpers, importer, lastfm


# You can scan a single directory and append it to the current library by
# specifying append=True, ArtistID and ArtistName.
def libraryScan(dir=None, append=False, ArtistID=None, ArtistName=None,
                cron=False, artistScan=False):
    if cron and not headphones.CONFIG.LIBRARYSCAN:
        return

    if not dir:
        if not headphones.CONFIG.MUSIC_DIR:
            logger.info(
                "No music directory configured. Add it under "
                "Manage -> Scan Music Library"
            )
            return
        else:
            dir = headphones.CONFIG.MUSIC_DIR

    if not os.path.isdir(dir):
        logger.warn(f"Cannot find music directory: {dir}")
        return

    myDB = db.DBConnection()
    new_artists = []

    logger.info(f"Scanning music directory: {dir}")

    if not append:

        # Clean up bad filepaths. Queries can take some time, ensure all results are loaded before processing
        if ArtistID:
            dbtracks = myDB.action(
                'SELECT Location FROM alltracks WHERE ArtistID = ? AND Location IS NOT NULL UNION SELECT Location FROM tracks WHERE ArtistID = ? AND Location '
                'IS NOT NULL',
                [ArtistID, ArtistID])
        else:
            dbtracks = myDB.action(
                'SELECT Location FROM alltracks WHERE Location IS NOT NULL UNION SELECT Location FROM tracks WHERE Location IS NOT NULL')

        for track in dbtracks:
            track_location = track['Location']
            if not os.path.isfile(track_location):
                myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE Location=?',
                            [None, None, None, track_location])
                myDB.action('UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE Location=?',
                            [None, None, None, track_location])

        if ArtistName:
            del_have_tracks = myDB.select('SELECT Location, Matched, ArtistName FROM have WHERE ArtistName = ? COLLATE NOCASE', [ArtistName])
        else:
            del_have_tracks = myDB.select('SELECT Location, Matched, ArtistName FROM have')

        for track in del_have_tracks:
            if not os.path.isfile(track['Location']):
                if track['ArtistName']:
                    # Make sure deleted files get accounted for when updating artist track counts
                    new_artists.append(track['ArtistName'])
                myDB.action('DELETE FROM have WHERE Location=?', [track['Location']])
                logger.info(
                    f"{track['Location']} removed from Headphones, as it "
                    f"is no longer on disk"
                )

    bitrates = []
    track_list = []
    latest_subdirectory = []

    new_track_count = 0
    file_count = 0

    for r, d, f in helpers.walk_directory(dir):
        # Filter paths based on config. Note that these methods work directly
        # on the inputs
        helpers.path_filter_patterns(d, headphones.CONFIG.IGNORED_FOLDERS, r)
        helpers.path_filter_patterns(f, headphones.CONFIG.IGNORED_FILES, r)

        for files in f:
            # MEDIA_FORMATS = music file extensions, e.g. mp3, flac, etc
            if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                subdirectory = r.replace(dir, '')
                latest_subdirectory.append(subdirectory)

                track_path = os.path.join(r, files)

                # Try to read the metadata
                try:
                    f = MediaFile(track_path)
                except (FileTypeError, UnreadableFileError):
                    logger.warning(f"Cannot read `{track_path}`. It may be corrupted or not a media file.")
                    continue
                except IOError:
                    logger.warning(f"Cannnot read `{track_path}`. Does the file exists?")
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

                # Add the track to our track list -
                # TODO: skip adding tracks without the minimum requisite information (just a matter of putting together the right if statements)

                if f_artist and f.album and f.title:
                    CleanName = helpers.clean_name(f_artist + ' ' + f.album + ' ' + f.title)
                else:
                    CleanName = None

                controlValueDict = {'Location': track_path}

                newValueDict = {'TrackID': f.mb_trackid,
                                # 'ReleaseID' : f.mb_albumid,
                                'ArtistName': f_artist,
                                'AlbumTitle': f.album,
                                'TrackNumber': f.track,
                                'TrackLength': f.length,
                                'Genre': f.genre,
                                'Date': f.date,
                                'TrackTitle': f.title,
                                'BitRate': f.bitrate,
                                'Format': f.format,
                                'CleanName': CleanName
                                }

                # track_list.append(track_dict)
                check_exist_track = myDB.action("SELECT * FROM have WHERE Location=?",
                                               [track_path]).fetchone()
                # Only attempt to match tracks that are new, haven't yet been matched, or metadata has changed.
                if not check_exist_track:
                    # This is a new track
                    if f_artist:
                        new_artists.append(f_artist)
                    myDB.upsert("have", newValueDict, controlValueDict)
                    new_track_count += 1
                else:
                    if check_exist_track['ArtistName'] != f_artist or check_exist_track[
                            'AlbumTitle'] != f.album or check_exist_track['TrackTitle'] != f.title:
                        # Important track metadata has been modified, need to run matcher again
                        if f_artist and f_artist != check_exist_track['ArtistName']:
                            new_artists.append(f_artist)
                        elif f_artist and f_artist == check_exist_track['ArtistName'] and \
                                        check_exist_track['Matched'] != "Ignored":
                            new_artists.append(f_artist)
                        else:
                            continue

                        newValueDict['Matched'] = None
                        myDB.upsert("have", newValueDict, controlValueDict)
                        myDB.action(
                            'UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE Location=?',
                            [None, None, None, track_path])
                        myDB.action(
                            'UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE Location=?',
                            [None, None, None, track_path])
                        new_track_count += 1
                    else:
                        # This track information hasn't changed
                        if f_artist and check_exist_track['Matched'] != "Ignored":
                            new_artists.append(f_artist)

                file_count += 1

    # Now we start track matching
    logger.info(f"{new_track_count} new/modified tracks found and added to the database")
    dbtracks = myDB.action(
            "SELECT * FROM have WHERE Matched IS NULL AND LOCATION LIKE ?",
            [f"{dir}%"]
        )
    dbtracks_count = myDB.action(
            "SELECT COUNT(*) FROM have WHERE Matched IS NULL AND LOCATION LIKE ?",
            [f"{dir}%"]
        ).fetchone()[0]
    logger.info(f"Found {dbtracks_count} new/modified tracks in `{dir}`")
    logger.info("Matching tracks to the appropriate releases....")



    # Sort the track_list by most vague (e.g. no trackid or releaseid)
    # to most specific (both trackid & releaseid)
    # When we insert into the database, the tracks with the most 
    # specific information will overwrite the more general matches

    sorted_dbtracks = helpers.multikeysort(dbtracks, ['ArtistName', 'AlbumTitle'])


    # We'll use this to give a % completion, just because the
    # track matching might take a while
    tracks_completed = 0
    latest_artist = None
    last_completion_percentage = 0
    prev_artist_name = None
    artistid = None

    for track in sorted_dbtracks:

        if latest_artist != track['ArtistName']:
            logger.info(f"Now matching tracks by {track['ArtistName']}")
            latest_artist = track['ArtistName']

        tracks_completed += 1
        completion_percentage = math.floor(
                float(tracks_completed) / dbtracks_count * 1000
            ) / 10

        if completion_percentage >= (last_completion_percentage + 10):
            logger.info("Track matching is " + str(completion_percentage) + "% complete")
            last_completion_percentage = completion_percentage

        # THE "MORE-SPECIFIC" CLAUSES HERE HAVE ALL BEEN REMOVED.  WHEN RUNNING A LIBRARY SCAN, THE ONLY CLAUSES THAT
        # EVER GOT HIT WERE [ARTIST/ALBUM/TRACK] OR CLEANNAME.  ARTISTID & RELEASEID ARE NEVER PASSED TO THIS FUNCTION,
        # ARE NEVER FOUND, AND THE OTHER CLAUSES WERE NEVER HIT.  FURTHERMORE, OTHER MATCHING FUNCTIONS IN THIS PROGRAM
        # (IMPORTER.PY, MB.PY) SIMPLY DO A [ARTIST/ALBUM/TRACK] OR CLEANNAME MATCH, SO IT'S ALL CONSISTENT.

        albumid = None

        if track['ArtistName'] and track['CleanName']:
            artist_name = track['ArtistName']
            clean_name = track['CleanName']

            # Only update if artist is in the db
            if artist_name != prev_artist_name:
                prev_artist_name = artist_name
                artistid = None

                artist_lookup = "\"" + artist_name.replace("\"", "\"\"") + "\""

                try:
                    dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM artists WHERE ArtistName LIKE ' + artist_lookup + '')
                except:
                    dbartist = None
                if not dbartist:
                    dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM tracks WHERE CleanName = ?', [clean_name])
                    if not dbartist:
                        dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM alltracks WHERE CleanName = ?', [clean_name])
                        if not dbartist:
                            clean_artist = helpers.clean_name(artist_name)
                            if clean_artist:
                                dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM tracks WHERE CleanName >= ? and CleanName < ?',
                                                       [clean_artist, clean_artist + '{'])
                                if not dbartist:
                                    dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM alltracks WHERE CleanName >= ? and CleanName < ?',
                                                           [clean_artist, clean_artist + '{'])

                if dbartist:
                    artistid = dbartist[0][0]

            if artistid:

                # This was previously using Artist, Album, Title with a SELECT LIKE ? and was not using an index
                # (Possible issue: https://stackoverflow.com/questions/37845854/python-sqlite3-not-using-index-with-like)
                # Now selects/updates using CleanName index (may have to revert if not working)

                # matching on CleanName should be enough, ensure it's the same artist just in case

                # Update tracks
                dbtrack = myDB.action('SELECT AlbumID, ArtistName FROM tracks WHERE CleanName = ? AND ArtistID = ?', [clean_name, artistid]).fetchone()
                if dbtrack:
                    albumid = dbtrack['AlbumID']
                    myDB.action(
                        'UPDATE tracks SET Location = ?, BitRate = ?, Format = ? WHERE CleanName = ? AND ArtistID = ?',
                        [track['Location'], track['BitRate'], track['Format'], clean_name, artistid])

                # Update alltracks
                alltrack = myDB.action('SELECT AlbumID, ArtistName FROM alltracks WHERE CleanName = ? AND ArtistID = ?', [clean_name, artistid]).fetchone()
                if alltrack:
                    albumid = alltrack['AlbumID']
                    myDB.action(
                        'UPDATE alltracks SET Location = ?, BitRate = ?, Format = ? WHERE CleanName = ? AND ArtistID = ?',
                        [track['Location'], track['BitRate'], track['Format'], clean_name, artistid])

        # Update have
        controlValueDict2 = {'Location': track['Location']}
        if albumid:
            newValueDict2 = {'Matched': albumid}
        else:
            newValueDict2 = {'Matched': "Failed"}
        myDB.upsert("have", newValueDict2, controlValueDict2)

        # myDB.action('INSERT INTO have (ArtistName, AlbumTitle, TrackNumber, TrackTitle, TrackLength, BitRate, Genre, Date, TrackID, Location, CleanName, Format) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [track['ArtistName'], track['AlbumTitle'], track['TrackNumber'], track['TrackTitle'], track['TrackLength'], track['BitRate'], track['Genre'], track['Date'], track['TrackID'], track['Location'], CleanName, track['Format']])

    logger.info(f"Completed matching tracks from `{dir}`")

    if not append or artistScan:
        logger.info('Updating scanned artist track counts')

        # Clean up the new artist list
        unique_artists = list({}.fromkeys(new_artists).keys())

        # # Don't think we need to do this, check the db instead below
        #
        # # artist scan
        # if ArtistName:
        #     current_artists = [[ArtistName]]
        # # directory scan
        # else:
        #     current_artists = myDB.select('SELECT ArtistName, ArtistID FROM artists WHERE ArtistName IS NOT NULL')
        #
        # # There was a bug where artists with special characters (-,') would show up in new artists.
        #
        # # artist_list = scanned artists not in the db
        # artist_list = [
        #     x for x in unique_artists
        #     if helpers.clean_name(x).lower() not in [
        #         helpers.clean_name(y[0]).lower()
        #         for y in current_artists
        #         ]
        #     ]
        #
        # # artists_checked = scanned artists that exist in the db
        # artists_checked = [
        #     x for x in unique_artists
        #     if helpers.clean_name(x).lower() in [
        #         helpers.clean_name(y[0]).lower()
        #         for y in current_artists
        #         ]
        #     ]

        new_artist_list = []

        for artist in unique_artists:

            if not artist:
                continue

            logger.info('Processing artist: %s' % artist)

            # check if artist is already in the db
            artist_lookup = "\"" + artist.replace("\"", "\"\"") + "\""

            try:
                dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM artists WHERE ArtistName LIKE ' + artist_lookup + '')
            except:
                dbartist = None
            if not dbartist:
                clean_artist = helpers.clean_name(artist)
                if clean_artist:
                    dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM tracks WHERE CleanName >= ? and CleanName < ?',
                                           [clean_artist, clean_artist + '{'])
                    if not dbartist:
                        dbartist = myDB.select('SELECT DISTINCT ArtistID, ArtistName FROM alltracks WHERE CleanName >= ? and CleanName < ?',
                                               [clean_artist, clean_artist + '{'])

            # new artist not in db, add to list
            if not dbartist:
                new_artist_list.append(artist)
            else:

                # artist in db, update have track counts
                artistid = dbartist[0][0]

                # Have tracks are selected from tracks table and not all tracks because of duplicates
                # We update the track count upon an album switch to compliment this

                # havetracks = (
                #     len(myDB.select(
                #         'SELECT TrackTitle from tracks WHERE ArtistName like ? AND Location IS NOT NULL',
                #         [artist])) + len(myDB.select(
                #             'SELECT TrackTitle from have WHERE ArtistName like ? AND Matched = "Failed"',
                #             [artist]))
                # )

                try:
                    havetracks = (
                        len(myDB.select(
                            'SELECT ArtistID From tracks WHERE ArtistID = ? AND Location IS NOT NULL',
                            [artistid])) + len(myDB.select(
                                'SELECT ArtistName FROM have WHERE ArtistName LIKE ' + artist_lookup + ' AND Matched = "Failed"'))
                    )
                except Exception as e:
                    logger.warn('Error updating counts for artist: %s: %s' % (artist, e))

                # Note: some people complain about having "artist have tracks" > # of tracks total in artist official releases
                # (can fix by getting rid of second len statement)

                if havetracks:
                    myDB.action('UPDATE artists SET HaveTracks = ? WHERE ArtistID = ?', [havetracks, artistid])

                    # Update albums to downloaded
                    update_album_status(ArtistID=artistid)

        logger.info('Found %i new artists' % len(new_artist_list))

        # Add scanned artists not in the db
        if new_artist_list:
            if headphones.CONFIG.AUTO_ADD_ARTISTS:
                logger.info('Importing %i new artists' % len(new_artist_list))
                importer.artistlist_to_mbids(new_artist_list)
            else:
                logger.info('To add these artists, go to Manage->Manage New Artists')
                # myDB.action('DELETE from newartists')
                for artist in new_artist_list:
                    myDB.action('INSERT OR IGNORE INTO newartists VALUES (?)', [artist])

        if headphones.CONFIG.DETECT_BITRATE and bitrates:
            headphones.CONFIG.PREFERRED_BITRATE = sum(bitrates) / len(bitrates) / 1000

    else:
        # If we're appending a new album to the database, update the artists total track counts
        logger.info('Updating artist track counts')

        artist_lookup = "\"" + ArtistName.replace("\"", "\"\"") + "\""
        try:
            havetracks = len(
                myDB.select('SELECT ArtistID FROM tracks WHERE ArtistID = ? AND Location IS NOT NULL',
                            [ArtistID])) + len(myDB.select(
                                'SELECT ArtistName FROM have WHERE ArtistName LIKE ' + artist_lookup + ' AND Matched = "Failed"'))
        except Exception as e:
            logger.warn('Error updating counts for artist: %s: %s' % (ArtistName, e))

        if havetracks:
            myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, ArtistID])

    # Moved above to call for each artist
    # if not append:
    #     update_album_status()

    # TODO: Fix last.fm api calls
    #if not append and not artistScan:
        #lastfm.getSimilar()

    if ArtistName:
        logger.info('Scanning complete for artist: %s', ArtistName)
    else:
        logger.info('Library scan complete')


# ADDED THIS SECTION TO MARK ALBUMS AS DOWNLOADED IF ARTISTS ARE ADDED EN MASSE BEFORE LIBRARY IS SCANNED

# Think the above comment relates to calling from Manage Unmatched

# This used to select and update all albums and would clobber the db, changed to run by ArtistID.

def update_album_status(AlbumID=None, ArtistID=None):
    myDB = db.DBConnection()
    # logger.info('Counting matched tracks to mark albums as skipped/downloaded')

    if AlbumID:
        album_status_updater = myDB.action(
            'SELECT'
            ' a.AlbumID, a.ArtistName, a.AlbumTitle, a.Status, AVG(t.Location IS NOT NULL) * 100 AS album_completion '
            'FROM'
            ' albums AS a '
            'JOIN tracks AS t ON t.AlbumID = a.AlbumID '
            'WHERE'
            ' a.AlbumID = ? AND a.Status != "Downloaded" '
            'GROUP BY'
            ' a.AlbumID '
            'HAVING'
            ' AVG(t.Location IS NOT NULL) * 100 >= ?',
            [AlbumID, headphones.CONFIG.ALBUM_COMPLETION_PCT]
        )
    else:
        album_status_updater = myDB.action(
            'SELECT'
            ' a.AlbumID, a.ArtistID, a.ArtistName, a.AlbumTitle, a.Status, AVG(t.Location IS NOT NULL) * 100 AS album_completion '
            'FROM'
            ' albums AS a '
            'JOIN tracks AS t ON t.AlbumID = a.AlbumID '
            'WHERE'
            ' a.ArtistID = ? AND a.Status != "Downloaded" '
            'GROUP BY'
            ' a.AlbumID '
            'HAVING'
            ' AVG(t.Location IS NOT NULL) * 100 >= ?',
            [ArtistID, headphones.CONFIG.ALBUM_COMPLETION_PCT]
        )

    new_album_status = "Downloaded"

    albums = []
    for album in album_status_updater:
        albums.append([album['AlbumID'], album['ArtistName'], album['AlbumTitle']])
    for album in albums:

        # I don't think we want to change Downloaded->Skipped.....
        # I think we can only automatically change Skipped->Downloaded when updating
        # There was a bug report where this was causing infinite downloads if the album was
        # recent, but matched to less than 80%. It would go Downloaded->Skipped->Wanted->Downloaded->Skipped->Wanted->etc....
        # else:
        #    if album['Status'] == "Skipped" or album['Status'] == "Downloaded":
        #        new_album_status = "Skipped"
        #    else:
        #        new_album_status = album['Status']
        #     else:
        #         new_album_status = album['Status']
        #
        #     myDB.upsert("albums", {'Status': new_album_status}, {'AlbumID': album['AlbumID']})
        #     if new_album_status != album['Status']:
        #         logger.info('Album %s changed to %s' % (album['AlbumTitle'], new_album_status))
        # logger.info('Album status update complete')

        myDB.action('UPDATE albums SET Status = ? WHERE AlbumID = ?', [new_album_status, album[0]])
        logger.info('Album: %s - %s. Status updated to %s' % (album[1], album[2], new_album_status))
