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

import time

from headphones import logger, helpers, db, mb, lastfm, metacritic
from beets.mediafile import MediaFile
import headphones

blacklisted_special_artist_names = ['[anonymous]', '[data]', '[no artist]',
                                    '[traditional]', '[unknown]', 'Various Artists']
blacklisted_special_artists = ['f731ccc4-e22a-43af-a747-64213329e088',
                               '33cf029c-63b0-41a0-9855-be2a3665fb3b',
                               '314e1c25-dde7-4e4d-b2f4-0a7b9f7c56dc',
                               'eec63d3c-3b81-4ad4-b1e4-7c147d4d2b61',
                               '9be7f096-97ec-4615-8957-8d40b5dcbc41',
                               '125ec42a-7229-4250-afc5-e057484327fe',
                               '89ad4ac3-39f7-470e-963a-56509c546377']


def is_exists(artistid):
    myDB = db.DBConnection()

    # See if the artist is already in the database
    artistlist = myDB.select('SELECT ArtistID, ArtistName from artists WHERE ArtistID=?',
                             [artistid])

    if any(artistid in x for x in artistlist):
        logger.info(artistlist[0][
                        1] + u" is already in the database. Updating 'have tracks', but not artist information")
        return True
    else:
        return False


def artistlist_to_mbids(artistlist, forced=False):
    for artist in artistlist:

        if not artist and artist != ' ':
            continue

        # If adding artists through Manage New Artists, they're coming through as non-unicode (utf-8?)
        # and screwing everything up
        if not isinstance(artist, unicode):
            try:
                artist = artist.decode('utf-8', 'replace')
            except Exception:
                logger.warn("Unable to convert artist to unicode so cannot do a database lookup")
                continue

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
            bl_artist = myDB.action('SELECT * FROM blacklist WHERE ArtistID=?',
                                    [artistid]).fetchone()
            if bl_artist or artistid in blacklisted_special_artists:
                logger.info("Artist ID for '%s' is either blacklisted or Various Artists. To add artist, you must "
                            "do it manually (Artist ID: %s)" % (artist, artistid))
                continue

        # Add to database if it doesn't exist
        if not is_exists(artistid):
            addArtisttoDB(artistid)

        # Just update the tracks if it does

        # not sure this is correct and we're updating during scanning in librarysync
        # else:
        #     havetracks = len(
        #         myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=?', [artistid])) + len(
        #         myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist]))
        #     myDB.action('UPDATE artists SET HaveTracks=? WHERE ArtistID=?', [havetracks, artistid])

        # Delete it from the New Artists if the request came from there
        if forced:
            myDB.action('DELETE from newartists WHERE ArtistName=?', [artist])

    # Update the similar artist tag cloud:
    logger.info('Updating artist information from Last.fm')

    try:
        lastfm.getSimilar()
    except Exception as e:
        logger.warn('Failed to update artist information from Last.fm: %s' % e)


def addArtistIDListToDB(artistidlist):
    # Used to add a list of artist IDs to the database in a single thread
    logger.debug("Importer: Adding artist ids %s" % artistidlist)
    for artistid in artistidlist:
        addArtisttoDB(artistid)


def addArtisttoDB(artistid, extrasonly=False, forcefull=False, type="artist"):
    # Putting this here to get around the circular import. We're using this to update thumbnails for artist/albums
    from headphones import cache

    # Can't add various artists - throws an error from MB
    if artistid in blacklisted_special_artists:
        logger.warn('Cannot import blocked special purpose artist with id' + artistid)
        return

    # We'll use this to see if we should update the 'LastUpdated' time stamp
    errors = False

    myDB = db.DBConnection()

    # Delete from blacklist if it's on there
    myDB.action('DELETE from blacklist WHERE ArtistID=?', [artistid])

    # We need the current minimal info in the database instantly
    # so we don't throw a 500 error when we redirect to the artistPage
    controlValueDict = {"ArtistID": artistid}

    # Don't replace a known artist name with an "Artist ID" placeholder
    dbartist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [artistid]).fetchone()

    # Only modify the Include Extras stuff if it's a new artist. We need it early so we know what to fetch
    if not dbartist:
        newValueDict = {"ArtistName": "Artist ID: %s" % (artistid),
                        "Status": "Loading",
                        "IncludeExtras": headphones.CONFIG.INCLUDE_EXTRAS,
                        "Extras": headphones.CONFIG.EXTRAS}
        if type == "series":
            newValueDict['Type'] = "series"
    else:
        newValueDict = {"Status": "Loading"}
        if dbartist["Type"] == "series":
            type = "series"

    myDB.upsert("artists", newValueDict, controlValueDict)

    if type == "series":
        artist = mb.getSeries(artistid)
    else:
        artist = mb.getArtist(artistid, extrasonly)

    if artist and artist.get('artist_name') in blacklisted_special_artist_names:
        logger.warn('Cannot import blocked special purpose artist: %s' % artist.get('artist_name'))
        myDB.action('DELETE from artists WHERE ArtistID=?', [artistid])
        # in case it's already in the db
        myDB.action('DELETE from albums WHERE ArtistID=?', [artistid])
        myDB.action('DELETE from tracks WHERE ArtistID=?', [artistid])
        return

    if not artist:
        logger.warn("Error fetching artist info. ID: " + artistid)
        if dbartist is None:
            newValueDict = {"ArtistName": "Fetch failed, try refreshing. (%s)" % (artistid),
                            "Status": "Active"}
        else:
            newValueDict = {"Status": "Active"}
        myDB.upsert("artists", newValueDict, controlValueDict)
        return

    if artist['artist_name'].startswith('The '):
        sortname = artist['artist_name'][4:]
    else:
        sortname = artist['artist_name']

    logger.info(u"Now adding/updating: " + artist['artist_name'])
    controlValueDict = {"ArtistID": artistid}
    newValueDict = {"ArtistName": artist['artist_name'],
                    "ArtistSortName": sortname,
                    "DateAdded": helpers.today(),
                    "Status": "Loading"}

    myDB.upsert("artists", newValueDict, controlValueDict)

    # See if we need to grab extras. Artist specific extras take precedence
    # over global option. Global options are set when adding a new artist
    try:
        db_artist = myDB.action('SELECT IncludeExtras, Extras from artists WHERE ArtistID=?',
                                [artistid]).fetchone()
        includeExtras = db_artist['IncludeExtras']
    except IndexError:
        includeExtras = False

    # Clean all references to release group in dB that are no longer referenced
    # from the musicbrainz refresh
    group_list = []
    force_repackage = 0

    # Don't nuke the database if there's a MusicBrainz error
    if len(artist['releasegroups']) != 0:
        for groups in artist['releasegroups']:
            group_list.append(groups['id'])
        if not extrasonly:
            remove_missing_groups_from_albums = myDB.select(
                "SELECT AlbumID FROM albums WHERE ArtistID=?", [artistid])
        else:
            remove_missing_groups_from_albums = myDB.select(
                'SELECT AlbumID FROM albums WHERE ArtistID=? AND Status="Skipped" AND Type!="Album"',
                [artistid])
        for items in remove_missing_groups_from_albums:
            if items['AlbumID'] not in group_list:
                # Remove all from albums/tracks that aren't in release groups
                myDB.action("DELETE FROM albums WHERE AlbumID=?", [items['AlbumID']])
                myDB.action("DELETE FROM allalbums WHERE AlbumID=?", [items['AlbumID']])
                myDB.action("DELETE FROM tracks WHERE AlbumID=?", [items['AlbumID']])
                myDB.action("DELETE FROM alltracks WHERE AlbumID=?", [items['AlbumID']])
                myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [items['AlbumID']])
                logger.info("[%s] Removing all references to release group %s to reflect MusicBrainz refresh" % (
                            artist['artist_name'], items['AlbumID']))
                if not extrasonly:
                    force_repackage = 1
    else:
        if not extrasonly:
            logger.info(
                "[%s] There was either an error pulling data from MusicBrainz or there might not be any releases for this category" %
                artist['artist_name'])

    # Then search for releases within releasegroups, if releases don't exist, then remove from allalbums/alltracks
    album_searches = []

    for rg in artist['releasegroups']:
        al_title = rg['title']
        today = helpers.today()
        rgid = rg['id']
        skip_log = 0
        # Make a user configurable variable to skip update of albums with release dates older than this date (in days)
        pause_delta = headphones.CONFIG.MB_IGNORE_AGE

        rg_exists = myDB.action("SELECT * from albums WHERE AlbumID=?", [rg['id']]).fetchone()

        if not forcefull:
            new_release_group = False

            try:
                check_release_date = rg_exists['ReleaseDate']
            except TypeError:
                check_release_date = None
                new_release_group = True

            if new_release_group:
                logger.info("[%s] Now adding: %s (New Release Group)" % (artist['artist_name'], rg['title']))
                new_releases = mb.get_new_releases(rgid, includeExtras)

            else:
                if check_release_date is None or check_release_date == u"None":
                    if headphones.CONFIG.MB_IGNORE_AGE_MISSING is not 1:
                        logger.info("[%s] Now updating: %s (No Release Date)" % (artist['artist_name'], rg['title']))
                        new_releases = mb.get_new_releases(rgid, includeExtras, True)
                    else:
                        logger.info("[%s] Skipping update of: %s (No Release Date)" % (artist['artist_name'], rg['title']))
                        new_releases = 0
                else:
                    if len(check_release_date) == 10:
                        release_date = check_release_date
                    elif len(check_release_date) == 7:
                        release_date = check_release_date + "-31"
                    elif len(check_release_date) == 4:
                        release_date = check_release_date + "-12-31"
                    else:
                        release_date = today
                    if helpers.get_age(today) - helpers.get_age(release_date) < pause_delta:
                        logger.info("[%s] Now updating: %s (Release Date <%s Days)",
                                    artist['artist_name'], rg['title'], pause_delta)
                        new_releases = mb.get_new_releases(rgid, includeExtras, True)
                    else:
                        logger.info("[%s] Skipping: %s (Release Date >%s Days)",
                                    artist['artist_name'], rg['title'], pause_delta)
                        skip_log = 1
                        new_releases = 0

            if force_repackage == 1:
                new_releases = -1
                logger.info('[%s] Forcing repackage of %s (Release Group Removed)',
                            artist['artist_name'], al_title)
            else:
                new_releases = new_releases
        else:
            logger.info("[%s] Now adding/updating: %s (Comprehensive Force)", artist['artist_name'],
                        rg['title'])
            new_releases = mb.get_new_releases(rgid, includeExtras, forcefull)

        if new_releases != 0:
            # Dump existing hybrid release since we're repackaging/replacing it
            myDB.action("DELETE from albums WHERE ReleaseID=?", [rg['id']])
            myDB.action("DELETE from allalbums WHERE ReleaseID=?", [rg['id']])
            myDB.action("DELETE from tracks WHERE ReleaseID=?", [rg['id']])
            myDB.action("DELETE from alltracks WHERE ReleaseID=?", [rg['id']])
            myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rg['id']])

            # This will be used later to build a hybrid release
            fullreleaselist = []
            # Search for releases within a release group
            find_hybrid_releases = myDB.select("SELECT * from allalbums WHERE AlbumID=?",
                                               [rg['id']])

            # Build the dictionary for the fullreleaselist
            for items in find_hybrid_releases:
                # don't include hybrid information, since that's what we're replacing
                if items['ReleaseID'] != rg['id']:
                    hybrid_release_id = items['ReleaseID']
                    newValueDict = {"ArtistID": items['ArtistID'],
                                    "ArtistName": items['ArtistName'],
                                    "AlbumTitle": items['AlbumTitle'],
                                    "AlbumID": items['AlbumID'],
                                    "AlbumASIN": items['AlbumASIN'],
                                    "ReleaseDate": items['ReleaseDate'],
                                    "Type": items['Type'],
                                    "ReleaseCountry": items['ReleaseCountry'],
                                    "ReleaseFormat": items['ReleaseFormat']
                                    }
                    find_hybrid_tracks = myDB.action("SELECT * from alltracks WHERE ReleaseID=?",
                                                     [hybrid_release_id])
                    totalTracks = 1
                    hybrid_track_array = []
                    for hybrid_tracks in find_hybrid_tracks:
                        hybrid_track_array.append({
                            'number': hybrid_tracks['TrackNumber'],
                            'title': hybrid_tracks['TrackTitle'],
                            'id': hybrid_tracks['TrackID'],
                            # 'url':           hybrid_tracks['TrackURL'],
                            'duration': hybrid_tracks['TrackDuration']
                        })
                        totalTracks += 1
                    newValueDict['ReleaseID'] = hybrid_release_id
                    newValueDict['Tracks'] = hybrid_track_array
                    fullreleaselist.append(newValueDict)

            # Basically just do the same thing again for the hybrid release
            # This may end up being called with an empty fullreleaselist
            try:
                hybridrelease = getHybridRelease(fullreleaselist)
                logger.info('[%s] Packaging %s releases into hybrid title' % (
                            artist['artist_name'], rg['title']))
            except Exception as e:
                errors = True
                logger.warn('[%s] Unable to get hybrid release information for %s: %s' % (
                            artist['artist_name'], rg['title'], e))
                continue

            # Use the ReleaseGroupID as the ReleaseID for the hybrid release to differentiate it
            # We can then use the condition WHERE ReleaseID == ReleaseGroupID to select it
            # The hybrid won't have a country or a format
            controlValueDict = {"ReleaseID": rg['id']}

            newValueDict = {"ArtistID": artistid,
                            "ArtistName": artist['artist_name'],
                            "AlbumTitle": rg['title'],
                            "AlbumID": rg['id'],
                            "AlbumASIN": hybridrelease['AlbumASIN'],
                            "ReleaseDate": hybridrelease['ReleaseDate'],
                            "Type": rg['type']
                            }

            myDB.upsert("allalbums", newValueDict, controlValueDict)

            for track in hybridrelease['Tracks']:

                cleanname = helpers.clean_name(artist['artist_name'] + ' ' + rg['title'] + ' ' + track['title'])

                controlValueDict = {"TrackID": track['id'],
                                    "ReleaseID": rg['id']}

                newValueDict = {"ArtistID": artistid,
                                "ArtistName": artist['artist_name'],
                                "AlbumTitle": rg['title'],
                                "AlbumASIN": hybridrelease['AlbumASIN'],
                                "AlbumID": rg['id'],
                                "TrackTitle": track['title'],
                                "TrackDuration": track['duration'],
                                "TrackNumber": track['number'],
                                "CleanName": cleanname
                                }

                match = myDB.action('SELECT Location, BitRate, Format from have WHERE CleanName=?',
                                    [cleanname]).fetchone()

                if not match:
                    match = myDB.action(
                        'SELECT Location, BitRate, Format from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?',
                        [artist['artist_name'], rg['title'], track['title']]).fetchone()
                    # if not match:
                    # match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()
                if match:
                    newValueDict['Location'] = match['Location']
                    newValueDict['BitRate'] = match['BitRate']
                    newValueDict['Format'] = match['Format']
                    # myDB.action('UPDATE have SET Matched="True" WHERE Location=?', [match['Location']])
                    myDB.action('UPDATE have SET Matched=? WHERE Location=?',
                                (rg['id'], match['Location']))

                myDB.upsert("alltracks", newValueDict, controlValueDict)

            # Delete matched tracks from the have table
            # myDB.action('DELETE from have WHERE Matched="True"')

            # If there's no release in the main albums tables, add the default (hybrid)
            # If there is a release, check the ReleaseID against the AlbumID to see if they differ (user updated)
            # check if the album already exists
            if not rg_exists:
                releaseid = rg['id']
            else:
                releaseid = rg_exists['ReleaseID']
                if not releaseid:
                    releaseid = rg['id']

            album = myDB.action('SELECT * from allalbums WHERE ReleaseID=?', [releaseid]).fetchone()

            controlValueDict = {"AlbumID": rg['id']}

            newValueDict = {"ArtistID": album['ArtistID'],
                            "ArtistName": album['ArtistName'],
                            "AlbumTitle": album['AlbumTitle'],
                            "ReleaseID": album['ReleaseID'],
                            "AlbumASIN": album['AlbumASIN'],
                            "ReleaseDate": album['ReleaseDate'],
                            "Type": album['Type'],
                            "ReleaseCountry": album['ReleaseCountry'],
                            "ReleaseFormat": album['ReleaseFormat']
                            }

            if rg_exists:
                newValueDict['DateAdded'] = rg_exists['DateAdded']
                newValueDict['Status'] = rg_exists['Status']

            else:
                today = helpers.today()

                newValueDict['DateAdded'] = today

                if headphones.CONFIG.AUTOWANT_ALL:
                    newValueDict['Status'] = "Wanted"
                elif album['ReleaseDate'] > today and headphones.CONFIG.AUTOWANT_UPCOMING:
                    newValueDict['Status'] = "Wanted"
                # Sometimes "new" albums are added to musicbrainz after their release date, so let's try to catch these
                # The first test just makes sure we have year-month-day
                elif helpers.get_age(album['ReleaseDate']) and helpers.get_age(
                        today) - helpers.get_age(
                        album['ReleaseDate']) < 21 and headphones.CONFIG.AUTOWANT_UPCOMING:
                    newValueDict['Status'] = "Wanted"
                else:
                    newValueDict['Status'] = "Skipped"

            myDB.upsert("albums", newValueDict, controlValueDict)

            tracks = myDB.action('SELECT * from alltracks WHERE ReleaseID=?',
                                 [releaseid]).fetchall()

            # This is used to see how many tracks you have from an album - to
            # mark it as downloaded. Default is 80%, can be set in config as
            # ALBUM_COMPLETION_PCT
            total_track_count = len(tracks)

            if total_track_count == 0:
                logger.warning("Total track count is zero for Release ID " +
                               "'%s', skipping.", releaseid)
                continue

            for track in tracks:
                controlValueDict = {"TrackID": track['TrackID'],
                                    "AlbumID": rg['id']}

                newValueDict = {"ArtistID": track['ArtistID'],
                                "ArtistName": track['ArtistName'],
                                "AlbumTitle": track['AlbumTitle'],
                                "AlbumASIN": track['AlbumASIN'],
                                "ReleaseID": track['ReleaseID'],
                                "TrackTitle": track['TrackTitle'],
                                "TrackDuration": track['TrackDuration'],
                                "TrackNumber": track['TrackNumber'],
                                "CleanName": track['CleanName'],
                                "Location": track['Location'],
                                "Format": track['Format'],
                                "BitRate": track['BitRate']
                                }

                myDB.upsert("tracks", newValueDict, controlValueDict)

            # Mark albums as downloaded if they have at least 80% (by default, configurable) of the album
            have_track_count = len(
                myDB.select('SELECT * from tracks WHERE AlbumID=? AND Location IS NOT NULL',
                            [rg['id']]))
            marked_as_downloaded = False

            if rg_exists:
                if rg_exists['Status'] == 'Skipped' and (
                    (have_track_count / float(total_track_count)) >= (
                        headphones.CONFIG.ALBUM_COMPLETION_PCT / 100.0)):
                    myDB.action('UPDATE albums SET Status=? WHERE AlbumID=?',
                                ['Downloaded', rg['id']])
                    marked_as_downloaded = True
            else:
                if (have_track_count / float(total_track_count)) >= (
                        headphones.CONFIG.ALBUM_COMPLETION_PCT / 100.0):
                    myDB.action('UPDATE albums SET Status=? WHERE AlbumID=?',
                                ['Downloaded', rg['id']])
                    marked_as_downloaded = True

            logger.info(
                u"[%s] Seeing if we need album art for %s" % (artist['artist_name'], rg['title']))
            try:
                cache.getThumb(AlbumID=rg['id'])
            except Exception as e:
                logger.error("Error getting album art: %s", e)

            # Start a search for the album if it's new, hasn't been marked as
            # downloaded and autowant_all is selected. This search is deferred,
            # in case the search failes and the rest of the import will halt.
            if not rg_exists and not marked_as_downloaded and headphones.CONFIG.AUTOWANT_ALL:
                album_searches.append(rg['id'])
        else:
            if skip_log == 0:
                logger.info(u"[%s] No new releases, so no changes made to %s" % (
                            artist['artist_name'], rg['title']))

    time.sleep(3)
    finalize_update(artistid, artist['artist_name'], errors)

    logger.info(u"Seeing if we need album art for: %s" % artist['artist_name'])
    try:
        cache.getThumb(ArtistID=artistid)
    except Exception as e:
        logger.error("Error getting album art: %s", e)

    logger.info(u"Fetching Metacritic reviews for: %s" % artist['artist_name'])
    try:
        metacritic.update(artistid, artist['artist_name'], artist['releasegroups'])
    except Exception as e:
        logger.error("Error getting Metacritic reviews: %s", e)

    if errors:
        logger.info(
            "[%s] Finished updating artist: %s but with errors, so not marking it as updated in the database" % (
                artist['artist_name'], artist['artist_name']))
    else:
        myDB.action('DELETE FROM newartists WHERE ArtistName = ?', [artist['artist_name']])
        logger.info(u"Updating complete for: %s" % artist['artist_name'])

    # Start searching for newly added albums
    if album_searches:
        from headphones import searcher
        logger.info("Start searching for %d albums.", len(album_searches))

        for album_search in album_searches:
            searcher.searchforalbum(albumid=album_search)


def finalize_update(artistid, artistname, errors=False):
    # Moving this little bit to it's own function so we can update have tracks & latest album when deleting extras

    myDB = db.DBConnection()

    latestalbum = myDB.action(
        'SELECT AlbumTitle, ReleaseDate, AlbumID from albums WHERE ArtistID=? order by ReleaseDate DESC',
        [artistid]).fetchone()
    totaltracks = len(myDB.select(
        'SELECT TrackTitle from tracks WHERE ArtistID=? AND AlbumID IN (SELECT AlbumID FROM albums WHERE Status != "Ignored")',
        [artistid]))
    # havetracks = len(myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL', [artistid])) + len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ?', [artist['artist_name']]))
    havetracks = len(
        myDB.select('SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL',
                    [artistid])) + len(
        myDB.select('SELECT TrackTitle from have WHERE ArtistName like ? AND Matched = "Failed"',
                    [artistname]))

    controlValueDict = {"ArtistID": artistid}

    if latestalbum:
        newValueDict = {"Status": "Active",
                        "LatestAlbum": latestalbum['AlbumTitle'],
                        "ReleaseDate": latestalbum['ReleaseDate'],
                        "AlbumID": latestalbum['AlbumID'],
                        "TotalTracks": totaltracks,
                        "HaveTracks": havetracks}
    else:
        newValueDict = {"Status": "Active",
                        "TotalTracks": totaltracks,
                        "HaveTracks": havetracks}

    if not errors:
        newValueDict['LastUpdated'] = helpers.now()

    myDB.upsert("artists", newValueDict, controlValueDict)


def addReleaseById(rid, rgid=None):
    myDB = db.DBConnection()

    # Create minimum info upfront if added from searchresults
    status = ''
    if rgid:
        dbalbum = myDB.select("SELECT * from albums WHERE AlbumID=?", [rgid])
        if not dbalbum:
            status = 'Loading'
            controlValueDict = {"AlbumID": rgid}
            newValueDict = {"AlbumTitle": rgid,
                            "ArtistName": status,
                            "Status": status}
            myDB.upsert("albums", newValueDict, controlValueDict)
            time.sleep(1)

    rgid = None
    artistid = None
    release_dict = None
    results = myDB.select(
        "SELECT albums.ArtistID, releases.ReleaseGroupID from releases, albums WHERE releases.ReleaseID=? and releases.ReleaseGroupID=albums.AlbumID LIMIT 1",
        [rid])
    for result in results:
        rgid = result['ReleaseGroupID']
        artistid = result['ArtistID']
        logger.debug(
            "Found a cached releaseid : releasegroupid relationship: " + rid + " : " + rgid)
    if not rgid:
        # didn't find it in the cache, get the information from MB
        logger.debug(
            "Didn't find releaseID " + rid + " in the cache. Looking up its ReleaseGroupID")
        try:
            release_dict = mb.getRelease(rid)
        except Exception as e:
            logger.info('Unable to get release information for Release %s: %s', rid, e)
            if status == 'Loading':
                myDB.action("DELETE FROM albums WHERE AlbumID=?", [rgid])
            return
        if not release_dict:
            logger.info('Unable to get release information for Release %s: no dict', rid)
            if status == 'Loading':
                myDB.action("DELETE FROM albums WHERE AlbumID=?", [rgid])
            return

        rgid = release_dict['rgid']
        artistid = release_dict['artist_id']

    # we don't want to make more calls to MB here unless we have to, could be happening quite a lot
    rg_exists = myDB.select("SELECT * from albums WHERE AlbumID=?", [rgid])

    # make sure the artist exists since I don't know what happens later if it doesn't
    artist_exists = myDB.select("SELECT * from artists WHERE ArtistID=?", [artistid])

    if not artist_exists and release_dict:
        if release_dict['artist_name'].startswith('The '):
            sortname = release_dict['artist_name'][4:]
        else:
            sortname = release_dict['artist_name']

        logger.info(
            u"Now manually adding: " + release_dict['artist_name'] + " - with status Paused")
        controlValueDict = {"ArtistID": release_dict['artist_id']}
        newValueDict = {"ArtistName": release_dict['artist_name'],
                        "ArtistSortName": sortname,
                        "DateAdded": helpers.today(),
                        "Status": "Paused"}

        if headphones.CONFIG.INCLUDE_EXTRAS:
            newValueDict['IncludeExtras'] = 1
            newValueDict['Extras'] = headphones.CONFIG.EXTRAS

        if 'title' in release_dict:
            newValueDict['LatestAlbum'] = release_dict['title']
        elif 'rg_title' in release_dict:
            newValueDict['LatestAlbum'] = release_dict['rg_title']

        if 'date' in release_dict:
            newValueDict['ReleaseDate'] = release_dict['date']

        if rgid:
            newValueDict['AlbumID'] = rgid

        myDB.upsert("artists", newValueDict, controlValueDict)

    elif not artist_exists and not release_dict:
        logger.error(
            "Artist does not exist in the database and did not get a valid response from MB. Skipping release.")
        if status == 'Loading':
            myDB.action("DELETE FROM albums WHERE AlbumID=?", [rgid])
        return

    if not rg_exists and release_dict or status == 'Loading' and release_dict:  # it should never be the case that we have an rg and not the artist
        # but if it is this will fail
        logger.info(u"Now adding-by-id album (" + release_dict['title'] + ") from id: " + rgid)
        controlValueDict = {"AlbumID": rgid}
        if status != 'Loading':
            status = 'Wanted'

        newValueDict = {"ArtistID": release_dict['artist_id'],
                        "ReleaseID": rgid,
                        "ArtistName": release_dict['artist_name'],
                        "AlbumTitle": release_dict['title'] if 'title' in release_dict else
                        release_dict['rg_title'],
                        "AlbumASIN": release_dict['asin'],
                        "ReleaseDate": release_dict['date'],
                        "DateAdded": helpers.today(),
                        "Status": status,
                        "Type": release_dict['rg_type'],
                        "ReleaseID": rid
                        }

        myDB.upsert("albums", newValueDict, controlValueDict)

        # keep a local cache of these so that external programs that are adding releasesByID don't hammer MB
        myDB.action('INSERT INTO releases VALUES( ?, ?)', [rid, release_dict['rgid']])

        for track in release_dict['tracks']:
            cleanname = helpers.clean_name(
                release_dict['artist_name'] + ' ' + release_dict['rg_title'] + ' ' + track['title'])

            controlValueDict = {"TrackID": track['id'],
                                "AlbumID": rgid}
            newValueDict = {"ArtistID": release_dict['artist_id'],
                            "ArtistName": release_dict['artist_name'],
                            "AlbumTitle": release_dict['rg_title'],
                            "AlbumASIN": release_dict['asin'],
                            "TrackTitle": track['title'],
                            "TrackDuration": track['duration'],
                            "TrackNumber": track['number'],
                            "CleanName": cleanname
                            }

            match = myDB.action(
                'SELECT Location, BitRate, Format, Matched from have WHERE CleanName=?',
                [cleanname]).fetchone()

            if not match:
                match = myDB.action(
                    'SELECT Location, BitRate, Format, Matched from have WHERE ArtistName LIKE ? AND AlbumTitle LIKE ? AND TrackTitle LIKE ?',
                    [release_dict['artist_name'], release_dict['rg_title'],
                     track['title']]).fetchone()

                # if not match:
                # match = myDB.action('SELECT Location, BitRate, Format from have WHERE TrackID=?', [track['id']]).fetchone()

            if match:
                newValueDict['Location'] = match['Location']
                newValueDict['BitRate'] = match['BitRate']
                newValueDict['Format'] = match['Format']
                # myDB.action('DELETE from have WHERE Location=?', [match['Location']])

                # If the album has been scanned before adding the release it will be unmatched, update to matched
                if match['Matched'] == 'Failed':
                    myDB.action('UPDATE have SET Matched=? WHERE Location=?',
                                (release_dict['rgid'], match['Location']))

            myDB.upsert("tracks", newValueDict, controlValueDict)

        # Reset status
        if status == 'Loading':
            controlValueDict = {"AlbumID": rgid}
            if headphones.CONFIG.AUTOWANT_MANUALLY_ADDED:
                newValueDict = {"Status": "Wanted"}
            else:
                newValueDict = {"Status": "Skipped"}
            myDB.upsert("albums", newValueDict, controlValueDict)

        # Start a search for the album
        if headphones.CONFIG.AUTOWANT_MANUALLY_ADDED:
            import searcher
            searcher.searchforalbum(rgid, False)

    elif not rg_exists and not release_dict:
        logger.error(
            "ReleaseGroup does not exist in the database and did not get a valid response from MB. Skipping release.")
        if status == 'Loading':
            myDB.action("DELETE FROM albums WHERE AlbumID=?", [rgid])
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
            except Exception as e:
                logger.info("Exception from MediaFile for: " + track['Location'] + " : " + str(e))
                continue
            controlValueDict = {"TrackID": track['TrackID']}
            newValueDict = {"Format": f.format}
            myDB.upsert("tracks", newValueDict, controlValueDict)
        logger.info('Finished finding media format for %s files' % len(tracks))
    havetracks = myDB.select('SELECT * from have WHERE Location IS NOT NULL and Format IS NULL')
    if len(havetracks) > 0:
        logger.info('Finding media format for %s files' % len(havetracks))
        for track in havetracks:
            try:
                f = MediaFile(track['Location'])
            except Exception as e:
                logger.info("Exception from MediaFile for: " + track['Location'] + " : " + str(e))
                continue
            controlValueDict = {"TrackID": track['TrackID']}
            newValueDict = {"Format": f.format}
            myDB.upsert("have", newValueDict, controlValueDict)
        logger.info('Finished finding media format for %s files' % len(havetracks))


def getHybridRelease(fullreleaselist):
    """
    Returns a dictionary of best group of tracks from the list of releases and
    earliest release date
    """

    if len(fullreleaselist) == 0:
        raise ValueError("Empty fullreleaselist")

    sortable_release_list = []

    formats = {
        '2xVinyl': '2',
        'Vinyl': '2',
        'CD': '0',
        'Cassette': '3',
        '2xCD': '1',
        'Digital Media': '0'
    }

    countries = {
        'US': '0',
        'GB': '1',
        'JP': '2',
    }

    for release in fullreleaselist:
        # Find values for format and country
        try:
            format = int(formats[release['Format']])
        except (ValueError, KeyError):
            format = 3

        try:
            country = int(countries[release['Country']])
        except (ValueError, KeyError):
            country = 3

        # Create record
        release_dict = {
            'hasasin': bool(release['AlbumASIN']),
            'asin': release['AlbumASIN'],
            'trackscount': len(release['Tracks']),
            'releaseid': release['ReleaseID'],
            'releasedate': release['ReleaseDate'],
            'format': format,
            'country': country,
            'tracks': release['Tracks']
        }

        sortable_release_list.append(release_dict)

    # Necessary to make dates that miss the month and/or day show up after full
    # dates
    def getSortableReleaseDate(releaseDate):
        # Change this value to change the sorting behaviour of none, returning
        # 'None' will put it at the top which was normal behaviour for pre-ngs
        # versions
        if releaseDate is None:
            return 'None'

        if releaseDate.count('-') == 2:
            return releaseDate
        elif releaseDate.count('-') == 1:
            return releaseDate + '32'
        else:
            return releaseDate + '13-32'

    sortable_release_list.sort(key=lambda x: getSortableReleaseDate(x['releasedate']))

    average_tracks = sum(x['trackscount'] for x in sortable_release_list) / float(
        len(sortable_release_list))
    for item in sortable_release_list:
        item['trackscount_delta'] = abs(average_tracks - item['trackscount'])

    a = helpers.multikeysort(sortable_release_list,
                             ['-hasasin', 'country', 'format', 'trackscount_delta'])

    release_dict = {'ReleaseDate': sortable_release_list[0]['releasedate'],
                    'Tracks': a[0]['tracks'],
                    'AlbumASIN': a[0]['asin']
                    }

    return release_dict
