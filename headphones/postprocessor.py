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

import shutil
import uuid
import threading
import itertools

import os
import re
import beets
import headphones
from beets import autotag
from beets import config as beetsconfig
from beets import logging as beetslogging
from beets.mediafile import MediaFile, FileTypeError, UnreadableFileError
from beetsplug import lyrics as beetslyrics
from headphones import notifiers, utorrent, transmission, deluge, qbittorrent
from headphones import db, albumart, librarysync
from headphones import logger, helpers, mb, music_encoder
from headphones import metadata

postprocessor_lock = threading.Lock()


def checkFolder():
    logger.debug("Checking download folder for completed downloads (only snatched ones).")

    with postprocessor_lock:
        myDB = db.DBConnection()
        snatched = myDB.select('SELECT * from snatched WHERE Status="Snatched"')

        for album in snatched:
            if album['FolderName']:
                folder_name = album['FolderName']
                single = False
                if album['Kind'] == 'nzb':
                    download_dir = headphones.CONFIG.DOWNLOAD_DIR
                else:
                    if headphones.CONFIG.DELUGE_DONE_DIRECTORY and headphones.CONFIG.TORRENT_DOWNLOADER == 3:
                        download_dir = headphones.CONFIG.DELUGE_DONE_DIRECTORY
                    else:
                        download_dir = headphones.CONFIG.DOWNLOAD_TORRENT_DIR

                    # Get folder from torrent hash
                    if album['TorrentHash'] and headphones.CONFIG.TORRENT_DOWNLOADER:
                        torrent_folder_name = None
                        if headphones.CONFIG.TORRENT_DOWNLOADER == 1:
                            torrent_folder_name, single = transmission.getFolder(album['TorrentHash'])
                        elif headphones.CONFIG.TORRENT_DOWNLOADER == 4:
                            torrent_folder_name, single = qbittorrent.getFolder(album['TorrentHash'])
                        if torrent_folder_name:
                            folder_name = torrent_folder_name

                if folder_name:
                    album_path = os.path.join(download_dir, folder_name).encode(
                        headphones.SYS_ENCODING, 'replace')
                    logger.debug("Checking if %s exists" % album_path)

                    if os.path.exists(album_path):
                        logger.info('Found "' + folder_name + '" in ' + album[
                            'Kind'] + ' download folder. Verifying....')
                        verify(album['AlbumID'], album_path, album['Kind'], single=single)
            else:
                logger.info("No folder name found for " + album['Title'])

    logger.debug("Checking download folder finished.")


def verify(albumid, albumpath, Kind=None, forced=False, keep_original_folder=False, single=False):
    myDB = db.DBConnection()
    release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
    tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])

    if not release or not tracks:
        release_list = None

        # Fetch album information from MusicBrainz
        try:
            release_list = mb.getReleaseGroup(albumid)
        except Exception as e:
            logger.error(
                'Unable to get release information for manual album with rgid: %s. Error: %s',
                albumid, e)
            return

        if not release_list:
            logger.error('Unable to get release information for manual album with rgid: %s',
                         albumid)
            return

        # Since we're just using this to create the bare minimum information to
        # insert an artist/album combo, use the first release
        releaseid = release_list[0]['id']
        release_dict = mb.getRelease(releaseid)

        if not release_dict:
            logger.error(
                'Unable to get release information for manual album with rgid: %s. Cannot continue',
                albumid)
            return

        # Check if the artist is added to the database. In case the database is
        # frozen during post processing, new artists will not be processed. This
        # prevents new artists from appearing suddenly. In case forced is True,
        # this check is skipped, since it is assumed the user wants this.
        if headphones.CONFIG.FREEZE_DB and not forced:
            artist = myDB.select(
                "SELECT ArtistName, ArtistID FROM artists WHERE ArtistId=? OR ArtistName=?",
                [release_dict['artist_id'], release_dict['artist_name']])

            if not artist:
                logger.warn("Continuing would add new artist '%s' (ID %s), "
                            "but database is frozen. Will skip postprocessing for "
                            "album with rgid: %s", release_dict['artist_name'],
                            release_dict['artist_id'], albumid)

                myDB.action(
                    'UPDATE snatched SET status = "Frozen" WHERE status NOT LIKE "Seed%" and AlbumID=?',
                    [albumid])
                frozen = re.search(r' \(Frozen\)(?:\[\d+\])?', albumpath)
                if not frozen:
                    if headphones.CONFIG.RENAME_FROZEN:
                        renameUnprocessedFolder(albumpath, tag="Frozen")
                    else:
                        logger.warn(u"Won't rename %s to mark as 'Frozen', because it is disabled.",
                                    albumpath.decode(headphones.SYS_ENCODING, 'replace'))
                return

        logger.info(u"Now adding/updating artist: " + release_dict['artist_name'])

        if release_dict['artist_name'].startswith('The '):
            sortname = release_dict['artist_name'][4:]
        else:
            sortname = release_dict['artist_name']

        controlValueDict = {"ArtistID": release_dict['artist_id']}
        newValueDict = {"ArtistName": release_dict['artist_name'],
                        "ArtistSortName": sortname,
                        "DateAdded": helpers.today(),
                        "Status": "Paused"}

        logger.info("ArtistID: " + release_dict['artist_id'] + " , ArtistName: " + release_dict[
            'artist_name'])

        if headphones.CONFIG.INCLUDE_EXTRAS:
            newValueDict['IncludeExtras'] = 1
            newValueDict['Extras'] = headphones.CONFIG.EXTRAS

        myDB.upsert("artists", newValueDict, controlValueDict)

        logger.info(u"Now adding album: " + release_dict['title'])
        controlValueDict = {"AlbumID": albumid}

        newValueDict = {"ArtistID": release_dict['artist_id'],
                        "ReleaseID": albumid,
                        "ArtistName": release_dict['artist_name'],
                        "AlbumTitle": release_dict['title'],
                        "AlbumASIN": release_dict['asin'],
                        "ReleaseDate": release_dict['date'],
                        "DateAdded": helpers.today(),
                        "Type": release_dict['rg_type'],
                        "Status": "Snatched"
                        }

        myDB.upsert("albums", newValueDict, controlValueDict)

        # Delete existing tracks associated with this AlbumID since we're going to replace them and don't want any extras
        myDB.action('DELETE from tracks WHERE AlbumID=?', [albumid])
        for track in release_dict['tracks']:
            controlValueDict = {"TrackID": track['id'],
                                "AlbumID": albumid}

            clean_name = helpers.clean_name(
                release_dict['artist_name'] + ' ' + release_dict['title'] + ' ' + track['title'])

            newValueDict = {"ArtistID": release_dict['artist_id'],
                            "ArtistName": release_dict['artist_name'],
                            "AlbumTitle": release_dict['title'],
                            "AlbumASIN": release_dict['asin'],
                            "TrackTitle": track['title'],
                            "TrackDuration": track['duration'],
                            "TrackNumber": track['number'],
                            "CleanName": clean_name
                            }

            myDB.upsert("tracks", newValueDict, controlValueDict)

        controlValueDict = {"ArtistID": release_dict['artist_id']}
        newValueDict = {"Status": "Paused"}

        myDB.upsert("artists", newValueDict, controlValueDict)
        logger.info(u"Addition complete for: " + release_dict['title'] + " - " + release_dict[
            'artist_name'])

        release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])

    downloaded_track_list = []
    downloaded_cuecount = 0

    for r, d, f in os.walk(albumpath):
        for files in f:
            if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                downloaded_track_list.append(os.path.join(r, files))
            elif files.lower().endswith('.cue'):
                downloaded_cuecount += 1
            # if any of the files end in *.part, we know the torrent isn't done yet. Process if forced, though
            elif files.lower().endswith(('.part', '.utpart')) and not forced:
                logger.info(
                    "Looks like " + os.path.basename(albumpath).decode(headphones.SYS_ENCODING,
                                                                       'replace') + " isn't complete yet. Will try again on the next run")
                return

    # Force single file through
    if single and not downloaded_track_list:
        downloaded_track_list.append(albumpath)

    # Check to see if we're preserving the torrent dir
    if (headphones.CONFIG.KEEP_TORRENT_FILES and Kind == "torrent") or headphones.CONFIG.KEEP_ORIGINAL_FOLDER:
        keep_original_folder = True

    # Split cue before metadata check
    if headphones.CONFIG.CUE_SPLIT and downloaded_cuecount and downloaded_cuecount >= len(
            downloaded_track_list):
        new_folder = None
        new_albumpath = albumpath
        if keep_original_folder:
            temp_path = helpers.preserve_torrent_directory(new_albumpath, forced)
            if not temp_path:
                markAsUnprocessed(albumid, new_albumpath, keep_original_folder)
                return
            else:
                new_albumpath = temp_path
                new_folder = os.path.split(new_albumpath)[0]
                Kind = "cue_split"
        cuepath = helpers.cue_split(new_albumpath)
        if not cuepath:
            if new_folder:
                shutil.rmtree(new_folder)
            markAsUnprocessed(albumid, albumpath, keep_original_folder)
            return
        else:
            albumpath = cuepath
            downloaded_track_list = helpers.get_downloaded_track_list(albumpath)
            keep_original_folder = False

    # test #1: metadata - usually works
    logger.debug('Verifying metadata...')

    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
        except Exception as e:
            logger.info(
                u"Exception from MediaFile for: " + downloaded_track.decode(headphones.SYS_ENCODING,
                                                                            'replace') + u" : " + unicode(
                    e))
            continue

        if not f.artist:
            continue
        if not f.album:
            continue

        metaartist = helpers.latinToAscii(f.artist.lower()).encode('UTF-8')
        dbartist = helpers.latinToAscii(release['ArtistName'].lower()).encode('UTF-8')
        metaalbum = helpers.latinToAscii(f.album.lower()).encode('UTF-8')
        dbalbum = helpers.latinToAscii(release['AlbumTitle'].lower()).encode('UTF-8')

        logger.debug('Matching metadata artist: %s with artist name: %s' % (metaartist, dbartist))
        logger.debug('Matching metadata album: %s with album name: %s' % (metaalbum, dbalbum))

        if metaartist == dbartist and metaalbum == dbalbum:
            doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind,
                             keep_original_folder, forced, single)
            return

    # test #2: filenames
    logger.debug('Metadata check failed. Verifying filenames...')
    for downloaded_track in downloaded_track_list:
        track_name = os.path.splitext(downloaded_track)[0]
        split_track_name = re.sub('[\.\-\_]', ' ', track_name).lower()
        for track in tracks:

            if not track['TrackTitle']:
                continue

            dbtrack = helpers.latinToAscii(track['TrackTitle'].lower()).encode('UTF-8')
            filetrack = helpers.latinToAscii(split_track_name).encode('UTF-8')
            logger.debug('Checking if track title: %s is in file name: %s' % (dbtrack, filetrack))

            if dbtrack in filetrack:
                doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind,
                                 keep_original_folder, forced, single)
                return

    # test #3: number of songs and duration
    logger.debug('Filename check failed. Verifying album length...')
    db_track_duration = 0
    downloaded_track_duration = 0

    logger.debug('Total music files in %s: %i' % (albumpath, len(downloaded_track_list)))
    logger.debug('Total tracks for this album in the database: %i' % len(tracks))
    if len(tracks) == len(downloaded_track_list):

        for track in tracks:
            try:
                db_track_duration += track['TrackDuration'] / 1000
            except:
                downloaded_track_duration = False
                break

        for downloaded_track in downloaded_track_list:
            try:
                f = MediaFile(downloaded_track)
                downloaded_track_duration += f.length
            except:
                downloaded_track_duration = False
                break

        if downloaded_track_duration and db_track_duration:
            logger.debug('Downloaded album duration: %i' % downloaded_track_duration)
            logger.debug('Database track duration: %i' % db_track_duration)
            delta = abs(downloaded_track_duration - db_track_duration)
            if delta < 240:
                doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind,
                                 keep_original_folder, forced, single)
                return

    logger.warn(u'Could not identify album: %s. It may not be the intended album.',
                albumpath.decode(headphones.SYS_ENCODING, 'replace'))
    markAsUnprocessed(albumid, albumpath, keep_original_folder)


def markAsUnprocessed(albumid, albumpath, keep_original_folder=False):
    myDB = db.DBConnection()
    myDB.action(
        'UPDATE snatched SET status = "Unprocessed" WHERE status NOT LIKE "Seed%" and AlbumID=?', [albumid])
    processed = re.search(r' \(Unprocessed\)(?:\[\d+\])?', albumpath)
    if not processed:
        if headphones.CONFIG.RENAME_UNPROCESSED and not keep_original_folder:
            renameUnprocessedFolder(albumpath, tag="Unprocessed")
        else:
            logger.warn(u"Won't rename %s to mark as 'Unprocessed', because it is disabled or folder is being kept.",
                        albumpath.decode(headphones.SYS_ENCODING, 'replace'))


def doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind=None,
                     keep_original_folder=False, forced=False, single=False):
    logger.info('Starting post-processing for: %s - %s' % (release['ArtistName'], release['AlbumTitle']))
    new_folder = None

    # Preserve the torrent dir
    if keep_original_folder or single:
        temp_path = helpers.preserve_torrent_directory(albumpath, forced, single)
        if not temp_path:
            markAsUnprocessed(albumid, albumpath, keep_original_folder)
            return
        else:
            albumpath = temp_path
            new_folder = os.path.split(albumpath)[0]
    elif Kind == "cue_split":
        new_folder = os.path.split(albumpath)[0]

    # Need to update the downloaded track list with the new location.
    # Could probably just throw in the "headphones-modified" folder,
    # but this is good to make sure we're not counting files that may have failed to move
    if new_folder:
        downloaded_track_list = []
        for r, d, f in os.walk(albumpath):
            for files in f:
                if any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                    downloaded_track_list.append(os.path.join(r, files))

    builder = metadata.AlbumMetadataBuilder()
    # Check if files are valid media files and are writable, before the steps
    # below are executed. This simplifies errors and prevents unfinished steps.
    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
            builder.add_media_file(f)
        except (FileTypeError, UnreadableFileError):
            logger.error("Track file is not a valid media file: %s. Not continuing.",
                         downloaded_track.decode(headphones.SYS_ENCODING, "replace"))
            return
        except IOError:
            logger.error("Unable to find media file: %s. Not continuing.", downloaded_track.decode(
                headphones.SYS_ENCODING, "replace"))
            if new_folder:
                shutil.rmtree(new_folder)
            return

        # If one of the options below is set, it will access/touch/modify the
        # files, which requires write permissions. This step just check this, so
        # it will not try and fail lateron, with strange exceptions.
        if headphones.CONFIG.EMBED_ALBUM_ART or headphones.CONFIG.CLEANUP_FILES or \
                headphones.CONFIG.ADD_ALBUM_ART or headphones.CONFIG.CORRECT_METADATA or \
                headphones.CONFIG.EMBED_LYRICS or headphones.CONFIG.RENAME_FILES or \
                headphones.CONFIG.MOVE_FILES:

            try:
                with open(downloaded_track, "a+b") as fp:
                    fp.seek(0)
            except IOError as e:
                logger.debug("Write check exact error: %s", e)
                logger.error("Track file is not writable. This is required "
                             "for some post processing steps: %s. Not continuing.",
                             downloaded_track.decode(headphones.SYS_ENCODING, "replace"))
                if new_folder:
                    shutil.rmtree(new_folder)
                return

    metadata_dict = builder.build()
    # start encoding
    if headphones.CONFIG.MUSIC_ENCODER:
        downloaded_track_list = music_encoder.encode(albumpath)

        if not downloaded_track_list:
            if new_folder:
                shutil.rmtree(new_folder)
            return

    # get artwork and path
    album_art_path = None
    artwork = None
    if headphones.CONFIG.EMBED_ALBUM_ART or headphones.CONFIG.ADD_ALBUM_ART or \
            (headphones.CONFIG.PLEX_ENABLED and headphones.CONFIG.PLEX_NOTIFY) or \
            (headphones.CONFIG.XBMC_ENABLED and headphones.CONFIG.XBMC_NOTIFY):
        album_art_path, artwork = albumart.getAlbumArt(albumid)

    if headphones.CONFIG.EMBED_ALBUM_ART and artwork:
        embedAlbumArt(artwork, downloaded_track_list)

    if headphones.CONFIG.CLEANUP_FILES:
        cleanupFiles(albumpath)

    if headphones.CONFIG.KEEP_NFO:
        renameNFO(albumpath)

    if headphones.CONFIG.ADD_ALBUM_ART and artwork:
        addAlbumArt(artwork, albumpath, release, metadata_dict)

    if headphones.CONFIG.CORRECT_METADATA:
        correctedMetadata = correctMetadata(albumid, release, downloaded_track_list)
        if not correctedMetadata and headphones.CONFIG.DO_NOT_PROCESS_UNMATCHED:
            if new_folder:
                shutil.rmtree(new_folder)
            return

    if headphones.CONFIG.EMBED_LYRICS:
        embedLyrics(downloaded_track_list)

    if headphones.CONFIG.RENAME_FILES:
        renameFiles(albumpath, downloaded_track_list, release)

    if headphones.CONFIG.MOVE_FILES and not headphones.CONFIG.DESTINATION_DIR:
        logger.error(
            'No DESTINATION_DIR has been set. Set "Destination Directory" to the parent directory you want to move the files to')
        albumpaths = [albumpath]
    elif headphones.CONFIG.MOVE_FILES and headphones.CONFIG.DESTINATION_DIR:
        albumpaths = moveFiles(albumpath, release, metadata_dict)
    else:
        albumpaths = [albumpath]

    updateFilePermissions(albumpaths)

    myDB = db.DBConnection()
    myDB.action('UPDATE albums SET status = "Downloaded" WHERE AlbumID=?', [albumid])
    myDB.action(
        'UPDATE snatched SET status = "Processed" WHERE Status NOT LIKE "Seed%" and AlbumID=?',
        [albumid])

    # Check if torrent has finished seeding
    if headphones.CONFIG.TORRENT_DOWNLOADER != 0:
        seed_snatched = myDB.action(
            'SELECT * from snatched WHERE Status="Seed_Snatched" and AlbumID=?',
            [albumid]).fetchone()
        if seed_snatched:
            hash = seed_snatched['TorrentHash']
            torrent_removed = False
            logger.info(u'%s - %s. Checking if torrent has finished seeding and can be removed' % (
                release['ArtistName'], release['AlbumTitle']))
            if headphones.CONFIG.TORRENT_DOWNLOADER == 1:
                torrent_removed = transmission.removeTorrent(hash, True)
            elif headphones.CONFIG.TORRENT_DOWNLOADER == 3:  # Deluge
                torrent_removed = deluge.removeTorrent(hash, True)
            elif headphones.CONFIG.TORRENT_DOWNLOADER == 2:
                torrent_removed = utorrent.removeTorrent(hash, True)
            else:
                torrent_removed = qbittorrent.removeTorrent(hash, True)

            # Torrent removed, delete the snatched record, else update Status for scheduled job to check
            if torrent_removed:
                myDB.action('DELETE from snatched WHERE status = "Seed_Snatched" and AlbumID=?',
                            [albumid])
            else:
                myDB.action(
                    'UPDATE snatched SET status = "Seed_Processed" WHERE status = "Seed_Snatched" and AlbumID=?',
                    [albumid])

    # Update the have tracks for all created dirs:
    for albumpath in albumpaths:
        librarysync.libraryScan(dir=albumpath, append=True, ArtistID=release['ArtistID'],
                                ArtistName=release['ArtistName'])

    logger.info(
        u'Post-processing for %s - %s complete' % (release['ArtistName'], release['AlbumTitle']))

    pushmessage = release['ArtistName'] + ' - ' + release['AlbumTitle']
    statusmessage = "Download and Postprocessing completed"

    if headphones.CONFIG.GROWL_ENABLED:
        logger.info(u"Growl request")
        growl = notifiers.GROWL()
        growl.notify(pushmessage, statusmessage)

    if headphones.CONFIG.PROWL_ENABLED:
        logger.info(u"Prowl request")
        prowl = notifiers.PROWL()
        prowl.notify(pushmessage, statusmessage)

    if headphones.CONFIG.XBMC_ENABLED:
        xbmc = notifiers.XBMC()
        if headphones.CONFIG.XBMC_UPDATE:
            xbmc.update()
        if headphones.CONFIG.XBMC_NOTIFY:
            xbmc.notify(release['ArtistName'],
                        release['AlbumTitle'],
                        album_art_path)

    if headphones.CONFIG.LMS_ENABLED:
        lms = notifiers.LMS()
        lms.update()

    if headphones.CONFIG.PLEX_ENABLED:
        plex = notifiers.Plex()
        if headphones.CONFIG.PLEX_UPDATE:
            plex.update()
        if headphones.CONFIG.PLEX_NOTIFY:
            plex.notify(release['ArtistName'],
                        release['AlbumTitle'],
                        album_art_path)

    if headphones.CONFIG.NMA_ENABLED:
        nma = notifiers.NMA()
        nma.notify(release['ArtistName'], release['AlbumTitle'])

    if headphones.CONFIG.PUSHALOT_ENABLED:
        logger.info(u"Pushalot request")
        pushalot = notifiers.PUSHALOT()
        pushalot.notify(pushmessage, statusmessage)

    if headphones.CONFIG.SYNOINDEX_ENABLED:
        syno = notifiers.Synoindex()
        for albumpath in albumpaths:
            syno.notify(albumpath)

    if headphones.CONFIG.PUSHOVER_ENABLED:
        logger.info(u"Pushover request")
        pushover = notifiers.PUSHOVER()
        pushover.notify(pushmessage, "Headphones")

    if headphones.CONFIG.PUSHBULLET_ENABLED:
        logger.info(u"PushBullet request")
        pushbullet = notifiers.PUSHBULLET()
        pushbullet.notify(pushmessage, statusmessage)

    if headphones.CONFIG.JOIN_ENABLED:
        logger.info(u"Join request")
        join = notifiers.JOIN()
        join.notify(pushmessage, statusmessage)

    if headphones.CONFIG.TELEGRAM_ENABLED:
        logger.info(u"Telegram request")
        telegram = notifiers.TELEGRAM()
        telegram.notify(statusmessage, pushmessage)

    if headphones.CONFIG.TWITTER_ENABLED:
        logger.info(u"Sending Twitter notification")
        twitter = notifiers.TwitterNotifier()
        twitter.notify_download(pushmessage)

    if headphones.CONFIG.OSX_NOTIFY_ENABLED:
        from headphones import cache
        c = cache.Cache()
        album_art = c.get_artwork_from_cache(None, release['AlbumID'])
        logger.info(u"Sending OS X notification")
        osx_notify = notifiers.OSX_NOTIFY()
        osx_notify.notify(release['ArtistName'],
                          release['AlbumTitle'],
                          statusmessage,
                          image=album_art)

    if headphones.CONFIG.BOXCAR_ENABLED:
        logger.info(u"Sending Boxcar2 notification")
        boxcar = notifiers.BOXCAR()
        boxcar.notify('Headphones processed: ' + pushmessage,
                      statusmessage, release['AlbumID'])

    if headphones.CONFIG.SUBSONIC_ENABLED:
        logger.info(u"Sending Subsonic update")
        subsonic = notifiers.SubSonicNotifier()
        subsonic.notify(albumpaths)

    if headphones.CONFIG.MPC_ENABLED:
        mpc = notifiers.MPC()
        mpc.notify()

    if headphones.CONFIG.EMAIL_ENABLED:
        logger.info(u"Sending Email notification")
        email = notifiers.Email()
        subject = release['ArtistName'] + ' - ' + release['AlbumTitle']
        email.notify(subject, "Download and Postprocessing completed")

    if new_folder:
        shutil.rmtree(new_folder)


def embedAlbumArt(artwork, downloaded_track_list):
    logger.info('Embedding album art')

    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
        except:
            logger.error(u'Could not read %s. Not adding album art' % downloaded_track.decode(
                headphones.SYS_ENCODING, 'replace'))
            continue

        logger.debug('Adding album art to: %s' % downloaded_track)

        try:
            f.art = artwork
            f.save()
        except Exception as e:
            logger.error(u'Error embedding album art to: %s. Error: %s' % (
                downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), str(e)))
            continue


def addAlbumArt(artwork, albumpath, release, metadata_dict):
    logger.info('Adding album art to folder')
    md = metadata.album_metadata(albumpath, release, metadata_dict)

    ext = ".jpg"
    # PNGs are possibe here too
    if artwork[:4] == '\x89PNG':
        ext = ".png"

    album_art_name = helpers.pattern_substitute(
        headphones.CONFIG.ALBUM_ART_FORMAT.strip(), md) + ext

    album_art_name = helpers.replace_illegal_chars(album_art_name).encode(
        headphones.SYS_ENCODING, 'replace')

    if headphones.CONFIG.FILE_UNDERSCORES:
        album_art_name = album_art_name.replace(' ', '_')

    if album_art_name.startswith('.'):
        album_art_name = album_art_name.replace(".", "_", 1)

    try:
        with open(os.path.join(albumpath, album_art_name), 'wb') as f:
            f.write(artwork)
    except IOError as e:
        logger.error('Error saving album art: %s', e)
        return


def cleanupFiles(albumpath):
    logger.info('Cleaning up files')

    for r, d, f in os.walk(albumpath):
        for files in f:
            if not any(files.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                logger.debug('Removing: %s' % files)
                try:
                    os.remove(os.path.join(r, files))
                except Exception as e:
                    logger.error(u'Could not remove file: %s. Error: %s' % (
                        files.decode(headphones.SYS_ENCODING, 'replace'), e))


def renameNFO(albumpath):
    logger.info('Renaming NFO')

    for r, d, f in os.walk(albumpath):
        for file in f:
            if file.lower().endswith('.nfo'):
                if not file.lower().endswith('.orig.nfo'):
                    logger.debug('Renaming: "%s" to "%s"' % (
                        file.decode(headphones.SYS_ENCODING, 'replace'),
                        file.decode(headphones.SYS_ENCODING, 'replace') + '-orig'))
                    try:
                        new_file_name = os.path.join(r, file)[:-3] + 'orig.nfo'
                        os.rename(os.path.join(r, file), new_file_name)
                    except Exception as e:
                        logger.error(u'Could not rename file: %s. Error: %s' % (
                            os.path.join(r, file).decode(headphones.SYS_ENCODING, 'replace'), e))


def moveFiles(albumpath, release, metadata_dict):
    logger.info("Moving files: %s" % albumpath)

    md = metadata.album_metadata(albumpath, release, metadata_dict)
    folder = helpers.pattern_substitute(
        headphones.CONFIG.FOLDER_FORMAT.strip(), md, normalize=True)

    if headphones.CONFIG.FILE_UNDERSCORES:
        folder = folder.replace(' ', '_')

    folder = helpers.replace_illegal_chars(folder, type="folder")
    folder = folder.replace('./', '_/').replace('/.', '/_')

    if folder.endswith('.'):
        folder = folder[:-1] + '_'

    if folder.startswith('.'):
        folder = '_' + folder[1:]

    # Grab our list of files early on so we can determine if we need to create
    # the lossy_dest_dir, lossless_dest_dir, or both
    files_to_move = []
    lossy_media = False
    lossless_media = False

    for r, d, f in os.walk(albumpath):
        for files in f:
            files_to_move.append(os.path.join(r, files))
            if any(files.lower().endswith('.' + x.lower()) for x in headphones.LOSSY_MEDIA_FORMATS):
                lossy_media = True
            if any(files.lower().endswith('.' + x.lower()) for x in
                   headphones.LOSSLESS_MEDIA_FORMATS):
                lossless_media = True

    # Do some sanity checking to see what directories we need to create:
    make_lossy_folder = False
    make_lossless_folder = False

    lossy_destination_path = os.path.normpath(
        os.path.join(headphones.CONFIG.DESTINATION_DIR, folder)).encode(headphones.SYS_ENCODING,
                                                                        'replace')
    lossless_destination_path = os.path.normpath(
        os.path.join(headphones.CONFIG.LOSSLESS_DESTINATION_DIR, folder)).encode(
        headphones.SYS_ENCODING, 'replace')

    # If they set a destination dir for lossless media, only create the lossy folder if there is lossy media
    if headphones.CONFIG.LOSSLESS_DESTINATION_DIR:
        if lossy_media:
            make_lossy_folder = True
        if lossless_media:
            make_lossless_folder = True
    # If they haven't set a lossless dest_dir, just create the "lossy" folder
    else:
        make_lossy_folder = True

    last_folder = headphones.CONFIG.FOLDER_FORMAT.strip().split('/')[-1]

    if make_lossless_folder:
        # Only rename the folder if they use the album name, otherwise merge into existing folder
        if os.path.exists(lossless_destination_path) and 'album' in last_folder.lower():

            create_duplicate_folder = False

            if headphones.CONFIG.REPLACE_EXISTING_FOLDERS:
                try:
                    shutil.rmtree(lossless_destination_path)
                except Exception as e:
                    logger.error(
                        "Error deleting existing folder: %s. Creating duplicate folder. Error: %s" % (
                            lossless_destination_path.decode(headphones.SYS_ENCODING, 'replace'), e))
                    create_duplicate_folder = True

            if not headphones.CONFIG.REPLACE_EXISTING_FOLDERS or create_duplicate_folder:
                temp_folder = folder

                i = 1
                while True:
                    newfolder = temp_folder + '[%i]' % i
                    lossless_destination_path = os.path.normpath(
                        os.path.join(headphones.CONFIG.LOSSLESS_DESTINATION_DIR, newfolder)).encode(
                        headphones.SYS_ENCODING, 'replace')
                    if os.path.exists(lossless_destination_path):
                        i += 1
                    else:
                        temp_folder = newfolder
                        break

        if not os.path.exists(lossless_destination_path):
            try:
                os.makedirs(lossless_destination_path)
            except Exception as e:
                logger.error('Could not create lossless folder for %s. (Error: %s)' % (
                    release['AlbumTitle'], e))
                if not make_lossy_folder:
                    return [albumpath]

    if make_lossy_folder:
        if os.path.exists(lossy_destination_path) and 'album' in last_folder.lower():

            create_duplicate_folder = False

            if headphones.CONFIG.REPLACE_EXISTING_FOLDERS:
                try:
                    shutil.rmtree(lossy_destination_path)
                except Exception as e:
                    logger.error(
                        "Error deleting existing folder: %s. Creating duplicate folder. Error: %s" % (
                            lossy_destination_path.decode(headphones.SYS_ENCODING, 'replace'), e))
                    create_duplicate_folder = True

            if not headphones.CONFIG.REPLACE_EXISTING_FOLDERS or create_duplicate_folder:
                temp_folder = folder

                i = 1
                while True:
                    newfolder = temp_folder + '[%i]' % i
                    lossy_destination_path = os.path.normpath(
                        os.path.join(headphones.CONFIG.DESTINATION_DIR, newfolder)).encode(
                        headphones.SYS_ENCODING, 'replace')
                    if os.path.exists(lossy_destination_path):
                        i += 1
                    else:
                        temp_folder = newfolder
                        break

        if not os.path.exists(lossy_destination_path):
            try:
                os.makedirs(lossy_destination_path)
            except Exception as e:
                logger.error(
                    'Could not create folder for %s. Not moving: %s' % (release['AlbumTitle'], e))
                return [albumpath]

    logger.info('Checking which files we need to move.....')

    # Move files to the destination folder, renaming them if they already exist
    # If we have two desination_dirs, move non-music files to both
    if make_lossy_folder and make_lossless_folder:

        for file_to_move in files_to_move:

            if any(file_to_move.lower().endswith('.' + x.lower()) for x in
                   headphones.LOSSY_MEDIA_FORMATS):
                helpers.smartMove(file_to_move, lossy_destination_path)

            elif any(file_to_move.lower().endswith('.' + x.lower()) for x in
                     headphones.LOSSLESS_MEDIA_FORMATS):
                helpers.smartMove(file_to_move, lossless_destination_path)

            # If it's a non-music file, move it to both dirs
            # TODO: Move specific-to-lossless files to the lossless dir only
            else:

                moved_to_lossy_folder = helpers.smartMove(file_to_move, lossy_destination_path,
                                                          delete=False)
                moved_to_lossless_folder = helpers.smartMove(file_to_move,
                                                             lossless_destination_path,
                                                             delete=False)

                if moved_to_lossy_folder or moved_to_lossless_folder:
                    try:
                        os.remove(file_to_move)
                    except Exception as e:
                        logger.error(
                            "Error deleting file '" + file_to_move.decode(headphones.SYS_ENCODING,
                                                                          'replace') + "' from source directory")
                else:
                    logger.error("Error copying '" + file_to_move.decode(headphones.SYS_ENCODING,
                                                                         'replace') + "'. Not deleting from download directory")

    elif make_lossless_folder and not make_lossy_folder:

        for file_to_move in files_to_move:
            helpers.smartMove(file_to_move, lossless_destination_path)

    else:

        for file_to_move in files_to_move:
            helpers.smartMove(file_to_move, lossy_destination_path)

    # Chmod the directories using the folder_format (script courtesy of premiso!)
    folder_list = folder.split('/')
    temp_fs = []

    if make_lossless_folder:
        temp_fs.append(headphones.CONFIG.LOSSLESS_DESTINATION_DIR)

    if make_lossy_folder:
        temp_fs.append(headphones.CONFIG.DESTINATION_DIR)

    for temp_f in temp_fs:

        for f in folder_list:

            temp_f = os.path.join(temp_f, f)

            if headphones.CONFIG.FOLDER_PERMISSIONS_ENABLED:
                try:
                    os.chmod(os.path.normpath(temp_f).encode(headphones.SYS_ENCODING, 'replace'),
                             int(headphones.CONFIG.FOLDER_PERMISSIONS, 8))
                except Exception as e:
                    logger.error("Error trying to change permissions on folder: %s. %s",
                                 temp_f.decode(headphones.SYS_ENCODING, 'replace'), e)
            else:
                logger.debug("Not changing folder permissions, since it is disabled: %s",
                             temp_f.decode(headphones.SYS_ENCODING, 'replace'))

    # If we failed to move all the files out of the directory, this will fail too
    try:
        shutil.rmtree(albumpath)
    except Exception as e:
        logger.error('Could not remove directory: %s. %s', albumpath, e)

    destination_paths = []

    if make_lossy_folder:
        destination_paths.append(lossy_destination_path)
    if make_lossless_folder:
        destination_paths.append(lossless_destination_path)

    return destination_paths


def correctMetadata(albumid, release, downloaded_track_list):
    logger.info('Preparing to write metadata to tracks....')
    lossy_items = []
    lossless_items = []

    # Process lossless & lossy media formats separately
    for downloaded_track in downloaded_track_list:

        try:

            if any(downloaded_track.lower().endswith('.' + x.lower()) for x in
                   headphones.LOSSLESS_MEDIA_FORMATS):
                lossless_items.append(beets.library.Item.from_path(downloaded_track))
            elif any(downloaded_track.lower().endswith('.' + x.lower()) for x in
                     headphones.LOSSY_MEDIA_FORMATS):
                lossy_items.append(beets.library.Item.from_path(downloaded_track))
            else:
                logger.warn("Skipping: %s because it is not a mutagen friendly file format",
                            downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
        except Exception as e:
            logger.error("Beets couldn't create an Item from: %s - not a media file? %s",
                         downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), str(e))

    for items in [lossy_items, lossless_items]:

        if not items:
            continue

        search_ids = []
        logger.debug('Getting recommendation from beets. Artist: %s. Album: %s. Tracks: %s', release['ArtistName'],
                     release['AlbumTitle'], len(items))

        # Try with specific release, e.g. alternate release selected from albumPage
        if release['ReleaseID'] != release['AlbumID']:
            logger.debug('trying beets with specific Release ID: %s', release['ReleaseID'])
            search_ids = [release['ReleaseID']]

        try:
            beetslog = beetslogging.getLogger('beets')
            beetslog.set_global_level(beetslogging.DEBUG) if headphones.VERBOSE else beetslog.set_global_level(
                beetslogging.CRITICAL)
            with helpers.capture_beets_log() as logs:
                cur_artist, cur_album, prop = autotag.tag_album(items,
                                                                search_artist=release['ArtistName'],
                                                                search_album=release['AlbumTitle'],
                                                                search_ids=search_ids)
                candidates = prop.candidates
                rec = prop.recommendation
                for log in logs:
                    logger.debug('Beets: %s', log)
            beetslog.set_global_level(beetslogging.NOTSET)
        except Exception as e:
            logger.error('Error getting recommendation: %s. Not writing metadata', e)
            return False
        if str(rec) == 'Recommendation.none':
            logger.warn('No accurate album match found for %s, %s -  not writing metadata',
                        release['ArtistName'], release['AlbumTitle'])
            return False

        if candidates:
            dist, info, mapping, extra_items, extra_tracks = candidates[0]
        else:
            logger.warn('No accurate album match found for %s, %s -  not writing metadata',
                        release['ArtistName'], release['AlbumTitle'])
            return False

        logger.info('Beets recommendation for tagging items: %s' % rec)

        # TODO: Handle extra_items & extra_tracks

        autotag.apply_metadata(info, mapping)

        # Set ID3 tag version
        if headphones.CONFIG.IDTAG:
            beetsconfig['id3v23'] = True
            logger.debug("Using ID3v2.3")
        else:
            beetsconfig['id3v23'] = False
            logger.debug("Using ID3v2.4")

        for item in items:
            try:
                item.write()
                logger.info("Successfully applied metadata to: %s",
                            item.path.decode(headphones.SYS_ENCODING, 'replace'))
            except Exception as e:
                logger.warn("Error writing metadata to '%s': %s",
                            item.path.decode(headphones.SYS_ENCODING, 'replace'), str(e))
                return False

        return True


def embedLyrics(downloaded_track_list):
    logger.info('Adding lyrics')

    # TODO: If adding lyrics for flac & lossy, only fetch the lyrics once and apply it to both files
    # TODO: Get beets to add automatically by enabling the plugin

    lossy_items = []
    lossless_items = []
    lp = beetslyrics.LyricsPlugin()

    for downloaded_track in downloaded_track_list:

        try:
            if any(downloaded_track.lower().endswith('.' + x.lower()) for x in
                   headphones.LOSSLESS_MEDIA_FORMATS):
                lossless_items.append(beets.library.Item.from_path(downloaded_track))
            elif any(downloaded_track.lower().endswith('.' + x.lower()) for x in
                     headphones.LOSSY_MEDIA_FORMATS):
                lossy_items.append(beets.library.Item.from_path(downloaded_track))
            else:
                logger.warn("Skipping: %s because it is not a mutagen friendly file format",
                            downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
        except Exception as e:
            logger.error("Beets couldn't create an Item from: %s - not a media file? %s",
                         downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), str(e))

    for items in [lossy_items, lossless_items]:

        if not items:
            continue

        for item in items:

            lyrics = None
            for artist, titles in beetslyrics.search_pairs(item):
                lyrics = [lp.get_lyrics(artist, title) for title in titles]
                if any(lyrics):
                    break

            lyrics = u"\n\n---\n\n".join([l for l in lyrics if l])

            if lyrics:
                logger.debug('Adding lyrics to: %s', item.title)
                item.lyrics = lyrics
                try:
                    item.write()
                except Exception as e:
                    logger.error('Cannot save lyrics to: %s. Skipping', item.title)
            else:
                logger.debug('No lyrics found for track: %s', item.title)


def renameFiles(albumpath, downloaded_track_list, release):
    logger.info('Renaming files')
    # Until tagging works better I'm going to rely on the already provided metadata

    for downloaded_track in downloaded_track_list:
        md, from_metadata = metadata.file_metadata(downloaded_track, release)
        if md is None:
            # unable to parse media file, skip file
            continue

        ext = md[metadata.Vars.EXTENSION]
        if not from_metadata:
            title = md[metadata.Vars.TITLE]
            new_file_name = helpers.cleanTitle(title) + ext
        else:
            new_file_name = helpers.pattern_substitute(
                headphones.CONFIG.FILE_FORMAT.strip(), md
            ).replace('/', '_') + ext

        new_file_name = helpers.replace_illegal_chars(new_file_name).encode(
            headphones.SYS_ENCODING, 'replace')

        if headphones.CONFIG.FILE_UNDERSCORES:
            new_file_name = new_file_name.replace(' ', '_')

        if new_file_name.startswith('.'):
            new_file_name = new_file_name.replace(".", "_", 1)

        new_file = os.path.join(albumpath, new_file_name)

        if downloaded_track == new_file_name:
            logger.debug("Renaming for: " + downloaded_track.decode(
                headphones.SYS_ENCODING, 'replace') + " is not neccessary")
            continue

        logger.debug('Renaming %s ---> %s',
                     downloaded_track.decode(headphones.SYS_ENCODING, 'replace'),
                     new_file_name.decode(headphones.SYS_ENCODING, 'replace'))
        try:
            os.rename(downloaded_track, new_file)
        except Exception as e:
            logger.error('Error renaming file: %s. Error: %s',
                         downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), e)
            continue


def updateFilePermissions(albumpaths):
    for folder in albumpaths:
        logger.info("Updating file permissions in %s", folder)
        for r, d, f in os.walk(folder):
            for files in f:
                full_path = os.path.join(r, files)
                if headphones.CONFIG.FILE_PERMISSIONS_ENABLED:
                    try:
                        os.chmod(full_path, int(headphones.CONFIG.FILE_PERMISSIONS, 8))
                    except:
                        logger.error("Could not change permissions for file: %s", full_path)
                        continue
                else:
                    logger.debug("Not changing file permissions, since it is disabled: %s",
                                 full_path.decode(headphones.SYS_ENCODING, 'replace'))


def renameUnprocessedFolder(path, tag):
    """
    Rename a unprocessed folder to a new unique name to indicate a certain
    status.
    """

    for i in itertools.count():
        if i == 0:
            new_path = "%s (%s)" % (path, tag)
        else:
            new_path = "%s (%s[%d])" % (path, tag, i)

        if os.path.exists(new_path):
            i += 1
        else:
            os.rename(path, new_path)
            return


def forcePostProcess(dir=None, expand_subfolders=True, album_dir=None, keep_original_folder=False):
    logger.info('Force checking download folder for completed downloads')

    ignored = 0

    if album_dir:
        folders = [album_dir.encode(headphones.SYS_ENCODING, 'replace')]
    else:
        download_dirs = []

        if dir:
            download_dirs.append(dir.encode(headphones.SYS_ENCODING, 'replace'))
        if headphones.CONFIG.DOWNLOAD_DIR and not dir:
            download_dirs.append(
                headphones.CONFIG.DOWNLOAD_DIR.encode(headphones.SYS_ENCODING, 'replace'))
        if headphones.CONFIG.DOWNLOAD_TORRENT_DIR and not dir:
            download_dirs.append(
                headphones.CONFIG.DOWNLOAD_TORRENT_DIR.encode(headphones.SYS_ENCODING, 'replace'))

        # If DOWNLOAD_DIR and DOWNLOAD_TORRENT_DIR are the same, remove the duplicate to prevent us from trying to process the same folder twice.
        download_dirs = list(set(download_dirs))
        logger.debug('Post processing folders: %s', download_dirs)

        # Get a list of folders in the download_dir
        folders = []

        for download_dir in download_dirs:
            if not os.path.isdir(download_dir):
                logger.warn('Directory %s does not exist. Skipping', download_dir)
                continue

            # Scan for subfolders
            subfolders = os.listdir(download_dir)
            ignored += helpers.path_filter_patterns(subfolders,
                                                    headphones.CONFIG.IGNORED_FOLDERS,
                                                    root=download_dir)

            for folder in subfolders:
                path_to_folder = os.path.join(download_dir, folder)

                if os.path.isdir(path_to_folder):
                    subfolders = helpers.expand_subfolders(path_to_folder)

                    if expand_subfolders and subfolders is not None:
                        folders.extend(subfolders)
                    else:
                        folders.append(path_to_folder)

    # Log number of folders
    if folders:
        logger.debug('Expanded post processing folders: %s', folders)
        logger.info('Found %d folders to process (%d ignored).',
                    len(folders), ignored)
    else:
        logger.info('Found no folders to process. Aborting.')
        return

    # Parse the folder names to get artist album info
    myDB = db.DBConnection()

    for folder in folders:
        folder_basename = os.path.basename(folder).decode(headphones.SYS_ENCODING, 'replace')
        logger.info('Processing: %s', folder_basename)

        # Attempt 1: First try to see if there's a match in the snatched table,
        # then we'll try to parse the foldername.
        # TODO: Iterate through underscores -> spaces, spaces -> dots,
        # underscores -> dots (this might be hit or miss since it assumes all
        # spaces/underscores came from sab replacing values
        logger.debug('Attempting to find album in the snatched table')
        snatched = myDB.action(
            'SELECT AlbumID, Title, Kind, Status from snatched WHERE FolderName LIKE ?',
            [folder_basename]).fetchone()

        if snatched:
            if headphones.CONFIG.KEEP_TORRENT_FILES and snatched['Kind'] == 'torrent' and snatched[
                    'Status'] == 'Processed':
                logger.info(
                    '%s is a torrent folder being preserved for seeding and has already been processed. Skipping.',
                    folder_basename)
                continue
            else:
                logger.info(
                    'Found a match in the database: %s. Verifying to make sure it is the correct album',
                    snatched['Title'])
                verify(snatched['AlbumID'], folder, snatched['Kind'],
                       forced=True, keep_original_folder=keep_original_folder)
                continue

        # Attempt 2: strip release group id from filename
        logger.debug('Attempting to extract release group from folder name')

        try:
            possible_rgid = folder_basename[-36:]
            rgid = uuid.UUID(possible_rgid)
        except:
            rgid = possible_rgid = None

        if rgid:
            rgid = possible_rgid
            release = myDB.action(
                'SELECT ArtistName, AlbumTitle, AlbumID from albums WHERE AlbumID=?',
                [rgid]).fetchone()
            if release:
                logger.info(
                    'Found a match in the database: %s - %s. Verifying to make sure it is the correct album',
                    release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder, forced=True,
                       keep_original_folder=keep_original_folder)
                continue
            else:
                logger.info(
                    'Found a (possibly) valid Musicbrainz release group id in album folder name.')
                verify(rgid, folder, forced=True,
                       keep_original_folder=keep_original_folder)
                continue

        # Attempt 3a: parse the folder name into a valid format
        logger.debug('Attempting to extract name, album and year from folder name')

        try:
            name, album, year = helpers.extract_data(folder_basename)
        except Exception:
            name = album = year = None

        if name and album:
            release = myDB.action(
                'SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE ArtistName LIKE ? and AlbumTitle LIKE ?',
                [name, album]).fetchone()
            if release:
                logger.info(
                    'Found a match in the database: %s - %s. Verifying to make sure it is the correct album',
                    release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder, forced=True, keep_original_folder=keep_original_folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s - %s', name,
                            album)
                try:
                    rgid = mb.findAlbumID(helpers.latinToAscii(name), helpers.latinToAscii(album))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder, forced=True, keep_original_folder=keep_original_folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)

        # Attempt 3b: deduce meta data into a valid format
        logger.debug('Attempting to extract name, album and year from metadata')

        try:
            name, album, year = helpers.extract_metadata(folder)
        except Exception:
            name = album = None

        # Not found from meta data, check if there's a cue to split and try meta data again
        kind = None
        if headphones.CONFIG.CUE_SPLIT and not name and not album:
            cue_folder = helpers.cue_split(folder, keep_original_folder=keep_original_folder)
            if cue_folder:
                try:
                    name, album, year = helpers.extract_metadata(cue_folder)
                except Exception:
                    name = album = None
                if name:
                    folder = cue_folder
                    if keep_original_folder:
                        keep_original_folder = False
                        kind = "cue_split"
                elif folder != cue_folder:
                    cue_folder = os.path.split(cue_folder)[0]
                    shutil.rmtree(cue_folder)

        if name and album:
            release = myDB.action(
                'SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE ArtistName LIKE ? and AlbumTitle LIKE ?',
                [name, album]).fetchone()
            if release:
                logger.info(
                    'Found a match in the database: %s - %s. Verifying to make sure it is the correct album',
                    release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder, Kind=kind, forced=True, keep_original_folder=keep_original_folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s - %s', name,
                            album)
                try:
                    rgid = mb.findAlbumID(helpers.latinToAscii(name), helpers.latinToAscii(album))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder, Kind=kind, forced=True, keep_original_folder=keep_original_folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)

        # Attempt 4: Hail mary. Just assume the folder name is the album name
        # if it doesn't have a separator in it
        logger.debug('Attempt to extract album name by assuming it is the folder name')

        if '-' not in folder_basename:
            release = myDB.action(
                'SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE AlbumTitle LIKE ?',
                [folder_basename]).fetchone()
            if release:
                logger.info(
                    'Found a match in the database: %s - %s. Verifying to make sure it is the correct album',
                    release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder, forced=True, keep_original_folder=keep_original_folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s',
                            folder_basename)
                try:
                    rgid = mb.findAlbumID(album=helpers.latinToAscii(folder_basename))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder, forced=True, keep_original_folder=keep_original_folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)

        # Fail here
        logger.info("Couldn't parse '%s' into any valid format. If adding "
                    "albums from another source, they must be in an 'Artist - Album "
                    "[Year]' format, or end with the musicbrainz release group id.",
                    folder_basename)
