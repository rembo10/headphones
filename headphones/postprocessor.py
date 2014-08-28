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
import re
import shutil
import uuid
import beets
import threading
import headphones

from beets import autotag
from beets.mediafile import MediaFile, FileTypeError, UnreadableFileError

from headphones import notifiers, utorrent, transmission
from headphones import db, albumart, librarysync, lyrics
from headphones import logger, helpers, request, mb, music_encoder

postprocessor_lock = threading.Lock()

<<<<<<< HEAD

def find_in_path(albumpath, extra_formats=None, use_MF=True):
    """ Takes a path and optionally extra formats.
        Finds files matching the MEDIA_FORMATS and returns them as a list.
        If use_MF is disabled MEDIA_FORMATS will be ignored.
    """
    if not os.path.isdir(albumpath):
        return False
    found_tracks = []
    if extra_formats:
        if type(extra_formats) is not list:
            extra_formats = [extra_formats]
        if not use_MF:
            mf = extra_formats
        else:
            mf = headphones.MEDIA_FORMATS + extra_formats
    else:
        if not use_MF:
            # if not using MF then extra_formats must be set
            return False
        mf = headphones.MEDIA_FORMATS
    for r, d, f in os.walk(albumpath):
        for _file in f:
            if any(_file.lower().endswith('.' + x.lower()) for x in mf):
                found_tracks.append(os.path.join(r, _file))
    return found_tracks


def count_matches(track_list, match, inverted=False):
    """ Takes a list of tracks and a pattern to match.
        Returns the number of matched items and a list of the matches.
        If inverted is set to True the returned list will be inverted and only
        contain the NON-matches.
    """
    if not track_list or not match:
        return False, False
    new_list = [x for x in track_list if x.lower().endswith(match)]
    nr_of_matches = len(new_list)
    if inverted:
        new_list = [x for x in track_list if not x.lower().endswith(match)]
    return nr_of_matches, new_list


=======
>>>>>>> parent of 59b4cef... Creating two functions from duplicated code
def checkFolder():

    with postprocessor_lock:

        myDB = db.DBConnection()
        snatched = myDB.select('SELECT * from snatched WHERE Status="Snatched"')

        for album in snatched:

            if album['FolderName']:

                if album['Kind'] == 'nzb':
                    download_dir = headphones.DOWNLOAD_DIR
                else:
                    download_dir = headphones.DOWNLOAD_TORRENT_DIR

                album_path = os.path.join(download_dir, album['FolderName']).encode(headphones.SYS_ENCODING,'replace')
                logger.info("Checking if %s exists" % album_path)
                if os.path.exists(album_path):
                    logger.info('Found "' + album['FolderName'] + '" in ' + album['Kind'] + ' download folder. Verifying....')
                    verify(album['AlbumID'], album_path, album['Kind'])

            else:
                logger.info("No folder name found for " + album['Title'])

def verify(albumid, albumpath, Kind=None, forced=False):

    myDB = db.DBConnection()
    release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
    tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])

    if not release or not tracks:
        #the result of a manual post-process on an album that hasn't been inserted
        #from an RSS feed or etc
        #TODO: This should be a call to a class method.. copied it out of importer with only minor changes
        #TODO: odd things can happen when there are diacritic characters in the folder name, need to translate them?
        release_list = None

        try:
            release_list = mb.getReleaseGroup(albumid)
        except Exception, e:
            logger.error('Unable to get release information for manual album with rgid: %s. Error: %s' % (albumid, e))
            return

        if not release_list:
            logger.error('Unable to get release information for manual album with rgid: %s' % albumid)
            return

        # Since we're just using this to create the bare minimum information to insert an artist/album combo, use the first release
        releaseid = release_list[0]['id']

        release_dict = mb.getRelease(releaseid)

        if not release_dict:
            logger.error('Unable to get release information for manual album with rgid: %s. Cannot continue' % albumid)
            return

        logger.info(u"Now adding/updating artist: " + release_dict['artist_name'])

        if release_dict['artist_name'].startswith('The '):
            sortname = release_dict['artist_name'][4:]
        else:
            sortname = release_dict['artist_name']


        controlValueDict = {"ArtistID":     release_dict['artist_id']}
        newValueDict = {"ArtistName":       release_dict['artist_name'],
                        "ArtistSortName":   sortname,
                        "DateAdded":        helpers.today(),
                        "Status":           "Paused"}

        logger.info("ArtistID: " + release_dict['artist_id'] + " , ArtistName: " + release_dict['artist_name'])

        if headphones.INCLUDE_EXTRAS:
            newValueDict['IncludeExtras'] = 1
            newValueDict['Extras'] = headphones.EXTRAS

        myDB.upsert("artists", newValueDict, controlValueDict)

        logger.info(u"Now adding album: " + release_dict['title'])
        controlValueDict = {"AlbumID":  albumid}

        newValueDict = {"ArtistID":         release_dict['artist_id'],
                        "ReleaseID":        albumid,
                        "ArtistName":       release_dict['artist_name'],
                        "AlbumTitle":       release_dict['title'],
                        "AlbumASIN":        release_dict['asin'],
                        "ReleaseDate":      release_dict['date'],
                        "DateAdded":        helpers.today(),
                        "Type":             release_dict['rg_type'],
                        "Status":           "Snatched"
                        }

        myDB.upsert("albums", newValueDict, controlValueDict)

        # Delete existing tracks associated with this AlbumID since we're going to replace them and don't want any extras
        myDB.action('DELETE from tracks WHERE AlbumID=?', [albumid])
        for track in release_dict['tracks']:

            controlValueDict = {"TrackID":  track['id'],
                                "AlbumID":  albumid}

            newValueDict = {"ArtistID":     release_dict['artist_id'],
                        "ArtistName":       release_dict['artist_name'],
                        "AlbumTitle":       release_dict['title'],
                        "AlbumASIN":        release_dict['asin'],
                        "TrackTitle":       track['title'],
                        "TrackDuration":    track['duration'],
                        "TrackNumber":      track['number']
                        }

            myDB.upsert("tracks", newValueDict, controlValueDict)

        controlValueDict = {"ArtistID":     release_dict['artist_id']}
        newValueDict = {"Status":           "Paused"}

        myDB.upsert("artists", newValueDict, controlValueDict)
        logger.info(u"Addition complete for: " + release_dict['title'] + " - " + release_dict['artist_name'])

        release = myDB.action('SELECT * from albums WHERE AlbumID=?', [albumid]).fetchone()
        tracks = myDB.select('SELECT * from tracks WHERE AlbumID=?', [albumid])

    all_matched = find_in_path(albumpath, ["cue", "part", "upart"])
    incomplete_matches, remaining_matches = count_matches(all_matched,
                                                          (".part", ".upart"),
                                                          inverted = True)
    if incomplete_matches and not forced:
        _a = os.path.basename(albumpath).decode(headphones.SYS_ENCODING,
                                                'replace')
        logger.info("Looks like " + _a + " isn't complete yet. Will try again on the next run")
        return

    downloaded_cuecount, downloaded_track_list = count_matches(remaining_matches,
                                                               ".cue",
                                                               inverted = True)

    # use xld to split cue

    if headphones.ENCODER == 'xld' and headphones.MUSIC_ENCODER and downloaded_cuecount and downloaded_cuecount >= len(downloaded_track_list):

        import getXldProfile

        (xldProfile, xldFormat, xldBitrate) = getXldProfile.getXldProfile(headphones.XLDPROFILE)
        if not xldFormat:
            logger.info(u'Details for xld profile "%s" not found, cannot split cue' % (xldProfile))
        else:
            if headphones.ENCODERFOLDER:
                xldencoder = os.path.join(headphones.ENCODERFOLDER, 'xld')
            else:
                xldencoder = os.path.join('/Applications','xld')

            for r,d,f in os.walk(albumpath):
                xldfolder = r
                xldfile = ''
                xldcue = ''
                for file in f:
                    if any(file.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS) and not xldfile:
                        xldfile = os.path.join(r, file)
                    elif file.lower().endswith('.cue') and not xldcue:
                        xldcue = os.path.join(r, file)

                if xldfile and xldcue and xldfolder:
                    xldcmd = xldencoder
                    xldcmd = xldcmd + ' "' + xldfile + '"'
                    xldcmd = xldcmd + ' -c'
                    xldcmd = xldcmd + ' "' + xldcue + '"'
                    xldcmd = xldcmd + ' --profile'
                    xldcmd = xldcmd + ' "' + xldProfile + '"'
                    xldcmd = xldcmd + ' -o'
                    xldcmd = xldcmd + ' "' + xldfolder + '"'
                    logger.info(u"Cue found, splitting file " + xldfile.decode(headphones.SYS_ENCODING, 'replace'))
                    logger.debug(xldcmd)
                    os.system(xldcmd)

            # count files, should now be more than original if xld successfully split

            new_downloaded_track_list_count = len(find_in_path(albumpath))

            if new_downloaded_track_list_count > len(downloaded_track_list):

                # rename original unsplit files
                for downloaded_track in downloaded_track_list:
                    os.rename(downloaded_track, downloaded_track + '.original')

                #reload
                downloaded_track_list = find_in_path(albumpath)


    # test #1: metadata - usually works
    logger.debug('Verifying metadata...')

    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
        except Exception, e:
            logger.info(u"Exception from MediaFile for: " + downloaded_track.decode(headphones.SYS_ENCODING, 'replace') + u" : " + unicode(e))
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
            doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind)
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
                doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind)
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
                db_track_duration += track['TrackDuration']/1000
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
                doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind)
                return

    logger.warn(u'Could not identify album: %s. It may not be the intended album.' % albumpath.decode(headphones.SYS_ENCODING, 'replace'))
    myDB.action('UPDATE snatched SET status = "Unprocessed" WHERE status NOT LIKE "Seed%" and AlbumID=?', [albumid])
    processed = re.search(r' \(Unprocessed\)(?:\[\d+\])?', albumpath)
    if not processed:
        renameUnprocessedFolder(albumpath)
    else:
        logger.info(u"Already marked as unprocessed: " + albumpath.decode(headphones.SYS_ENCODING, 'replace'))

def doPostProcessing(albumid, albumpath, release, tracks, downloaded_track_list, Kind=None):

    logger.info('Starting post-processing for: %s - %s' % (release['ArtistName'], release['AlbumTitle']))
    # Check to see if we're preserving the torrent dir
    if headphones.KEEP_TORRENT_FILES and Kind=="torrent":
        new_folder = os.path.join(albumpath, 'headphones-modified'.encode(headphones.SYS_ENCODING, 'replace'))
        logger.info("Copying files to 'headphones-modified' subfolder to preserve downloaded files for seeding")
        try:
            shutil.copytree(albumpath, new_folder)
            # Update the album path with the new location
            albumpath = new_folder
        except Exception, e:
            logger.warn("Cannot copy/move files to temp folder: " + new_folder.decode(headphones.SYS_ENCODING, 'replace') + ". Not continuing. Error: " + str(e))
            return

        # Need to update the downloaded track list with the new location.
        # Could probably just throw in the "headphones-modified" folder,
        # but this is good to make sure we're not counting files that may have failed to move

        all_matches = find_in_path(albumpath, "cue")
        downloaded_cuecount, downloaded_track_list = count_matches(all_matches,
                                                                   ".cue",
                                                                   True)


    # Check if files are valid media files and are writeable, before the steps
    # below are executed. This simplifies errors and prevents unfinished steps.
    for downloaded_track in downloaded_track_list:
        try:
            media_file = MediaFile(downloaded_track)
        except (FileTypeError, UnreadableFileError):
            logger.error("Track file is not a valid media file: %s. Not continuing.", downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
            return

        # Not sure if line(s) below are needed, since it is possible to not
        # touch any files.
        if headphones.EMBED_ALBUM_ART or headphones.CLEANUP_FILES or \
           headphones.ADD_ALBUM_ART or headphones.CORRECT_METADATA or \
           headphones.EMBED_LYRICS or headphones.RENAME_FILES or \
           headphones.MOVE_FILES:

            if not os.access(downloaded_track, os.W_OK):
                logger.error("Track file is not writeable, which is required for some post processing steps: %s", downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
                return

    #start encoding
    if headphones.MUSIC_ENCODER:
        downloaded_track_list=music_encoder.encode(albumpath)

        if not downloaded_track_list:
            return

    artwork = None
    album_art_path = albumart.getAlbumArt(albumid)
    if headphones.EMBED_ALBUM_ART or headphones.ADD_ALBUM_ART:

        if album_art_path:
            artwork = request.request_content(album_art_path)
        else:
            artwork = None

        if not album_art_path or not artwork or len(artwork) < 100:
            logger.info("No suitable album art found from Amazon. Checking Last.FM....")
            artwork = albumart.getCachedArt(albumid)
            if not artwork or len(artwork) < 100:
                artwork = False
                logger.info("No suitable album art found from Last.FM. Not adding album art")

    if headphones.EMBED_ALBUM_ART and artwork:
        embedAlbumArt(artwork, downloaded_track_list)

    if headphones.CLEANUP_FILES:
        cleanupFiles(albumpath)

    if headphones.KEEP_NFO:
        renameNFO(albumpath)

    if headphones.ADD_ALBUM_ART and artwork:
        addAlbumArt(artwork, albumpath, release)

    if headphones.CORRECT_METADATA:
        correctMetadata(albumid, release, downloaded_track_list)

    if headphones.EMBED_LYRICS:
        embedLyrics(downloaded_track_list)

    if headphones.RENAME_FILES:
        renameFiles(albumpath, downloaded_track_list, release)

    if headphones.MOVE_FILES and not headphones.DESTINATION_DIR:
        logger.error('No DESTINATION_DIR has been set. Set "Destination Directory" to the parent directory you want to move the files to')
        albumpaths = [albumpath]
    elif headphones.MOVE_FILES and headphones.DESTINATION_DIR:
        albumpaths = moveFiles(albumpath, release, tracks)
    else:
        albumpaths = [albumpath]

    updateFilePermissions(albumpaths)

    myDB = db.DBConnection()
    myDB.action('UPDATE albums SET status = "Downloaded" WHERE AlbumID=?', [albumid])
    myDB.action('UPDATE snatched SET status = "Processed" WHERE Status NOT LIKE "Seed%" and AlbumID=?', [albumid])

    # Check if torrent has finished seeding
    if headphones.TORRENT_DOWNLOADER == 1 or headphones.TORRENT_DOWNLOADER == 2:
        seed_snatched = myDB.action('SELECT * from snatched WHERE Status="Seed_Snatched" and AlbumID=?', [albumid]).fetchone()
        if seed_snatched:
            hash = seed_snatched['FolderName']
            torrent_removed = False
            if headphones.TORRENT_DOWNLOADER == 1:
                torrent_removed = transmission.removeTorrent(hash, True)
            else:
                torrent_removed = utorrent.removeTorrent(hash, True)

            # Torrent removed, delete the snatched record, else update Status for scheduled job to check
            if torrent_removed:
                myDB.action('DELETE from snatched WHERE status = "Seed_Snatched" and AlbumID=?', [albumid])
            else:
                myDB.action('UPDATE snatched SET status = "Seed_Processed" WHERE status = "Seed_Snatched" and AlbumID=?', [albumid])

    # Update the have tracks for all created dirs:
    for albumpath in albumpaths:
        librarysync.libraryScan(dir=albumpath, append=True, ArtistID=release['ArtistID'], ArtistName=release['ArtistName'])

    logger.info(u'Post-processing for %s - %s complete' % (release['ArtistName'], release['AlbumTitle']))

    pushmessage = release['ArtistName'] + ' - ' + release['AlbumTitle']
    statusmessage = "Download and Postprocessing completed"

    if headphones.GROWL_ENABLED:
        logger.info(u"Growl request")
        growl = notifiers.GROWL()
        growl.notify(pushmessage, statusmessage)

    if headphones.PROWL_ENABLED:
        logger.info(u"Prowl request")
        prowl = notifiers.PROWL()
        prowl.notify(pushmessage, statusmessage)

    if headphones.XBMC_ENABLED:
        xbmc = notifiers.XBMC()
        if headphones.XBMC_UPDATE:
            xbmc.update()
        if headphones.XBMC_NOTIFY:
            xbmc.notify(release['ArtistName'],
                        release['AlbumTitle'],
                        album_art_path)

    if headphones.LMS_ENABLED:
        lms = notifiers.LMS()
        lms.update()

    if headphones.PLEX_ENABLED:
        plex = notifiers.Plex()
        if headphones.PLEX_UPDATE:
            plex.update()
        if headphones.PLEX_NOTIFY:
            plex.notify(release['ArtistName'],
                        release['AlbumTitle'],
                        album_art_path)

    if headphones.NMA_ENABLED:
        nma = notifiers.NMA()
        nma.notify(release['ArtistName'], release['AlbumTitle'])

    if headphones.PUSHALOT_ENABLED:
        logger.info(u"Pushalot request")
        pushalot = notifiers.PUSHALOT()
        pushalot.notify(pushmessage, statusmessage)

    if headphones.SYNOINDEX_ENABLED:
        syno = notifiers.Synoindex()
        for albumpath in albumpaths:
            syno.notify(albumpath)

    if headphones.PUSHOVER_ENABLED:
        logger.info(u"Pushover request")
        pushover = notifiers.PUSHOVER()
        pushover.notify(pushmessage, "Headphones")

    if headphones.PUSHBULLET_ENABLED:
        logger.info(u"PushBullet request")
        pushbullet = notifiers.PUSHBULLET()
        pushbullet.notify(pushmessage, "Download and Postprocessing completed")

    if headphones.TWITTER_ENABLED:
        logger.info(u"Sending Twitter notification")
        twitter = notifiers.TwitterNotifier()
        twitter.notify_download(pushmessage)

    if headphones.OSX_NOTIFY_ENABLED:
        logger.info(u"Sending OS X notification")
        osx_notify = notifiers.OSX_NOTIFY()
        osx_notify.notify(release['ArtistName'],
                          release['AlbumTitle'],
                          statusmessage)

    if headphones.BOXCAR_ENABLED:
        logger.info(u"Sending Boxcar2 notification")
        boxcar = notifiers.BOXCAR()
        boxcar.notify('Headphones processed: ' + pushmessage,
                      statusmessage, release['AlbumID'])

    if headphones.MPC_ENABLED:
        mpc = notifiers.MPC()
        mpc.notify()

def embedAlbumArt(artwork, downloaded_track_list):
    logger.info('Embedding album art')

    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
        except:
            logger.error(u'Could not read %s. Not adding album art' % downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
            continue

        logger.debug('Adding album art to: %s' % downloaded_track)

        try:
            f.art = artwork
            f.save()
        except Exception, e:
            logger.error(u'Error embedding album art to: %s. Error: %s' % (downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), str(e)))
            continue

def addAlbumArt(artwork, albumpath, release):
    logger.info('Adding album art to folder')

    try:
        year = release['ReleaseDate'][:4]
    except TypeError:
        year = ''

    values = {  '$Artist':      release['ArtistName'],
                '$Album':       release['AlbumTitle'],
                '$Year':        year,
                '$artist':      release['ArtistName'].lower(),
                '$album':       release['AlbumTitle'].lower(),
                '$year':        year
                }

    album_art_name = helpers.replace_all(headphones.ALBUM_ART_FORMAT.strip(), values) + ".jpg"

    album_art_name = helpers.replace_illegal_chars(album_art_name).encode(headphones.SYS_ENCODING, 'replace')

    if headphones.FILE_UNDERSCORES:
        album_art_name = album_art_name.replace(' ', '_')

    if album_art_name.startswith('.'):
        album_art_name = album_art_name.replace(".", "_", 1)

    try:
        file = open(os.path.join(albumpath, album_art_name), 'wb')
        file.write(artwork)
        file.close()
    except Exception, e:
        logger.error('Error saving album art: %s' % str(e))
        return

def cleanupFiles(albumpath):
    logger.info('Cleaning up files')
    if headphones.KEEP_NFO:
        files = find_in_path(albumpath, extra_formats="nfo", inverted=True)
    else:
        files = find_in_path(albumpath, inverted=True)
    for _f in files:
        logger.debug('Removing: %s' % _f)
        try:
            os.remove(_f)
        except Exception, e:
            _f_decoded = _f.decode(headphones.SYS_ENCODING, 'replace')
            logger.error(u'Could not remove file: %s. Error: %s' % (_f_decoded,
                                                                    e))

def renameNFO(albumpath):
    files = find_in_path(albumpath, extra_formats="nfo", use_MF=False)
    for _f in files:
        _f_decoded = _f.decode(headphones.SYS_ENCODING, 'replace')
        logger.debug('Renaming: "%s" to "%s"' % (_f_decoded, _f_decoded + '-orig'))
        try:
            new_file_name = _f[:-3] + 'orig.nfo'
            os.rename(_f, new_file_name)
        except Exception, e:
            logger.error(u'Could not rename file: %s. Error: %s' % (_f_decoded,
                                                                    e))

def moveFiles(albumpath, release, tracks):

    try:
        year = release['ReleaseDate'][:4]
    except TypeError:
        year = ''

    artist = release['ArtistName'].replace('/', '_')
    album = release['AlbumTitle'].replace('/', '_')
    if headphones.FILE_UNDERSCORES:
        artist = artist.replace(' ', '_')
        album = album.replace(' ', '_')

    releasetype = release['Type'].replace('/', '_')

    if release['ArtistName'].startswith('The '):
        sortname = release['ArtistName'][4:] + ", The"
    else:
        sortname = release['ArtistName']

    if sortname[0].isdigit():
        firstchar = '0-9'
    else:
        firstchar = sortname[0]

    for r,d,f in os.walk(albumpath):
            try:
                origfolder = os.path.basename(os.path.normpath(r))
            except:
                origfolder = ''

    values = {  '$Artist':  artist,
                '$SortArtist': sortname,
                '$Album':   album,
                '$Year':        year,
                '$Type':  releasetype,
                '$OriginalFolder': origfolder,
                '$First':   firstchar.upper(),
                '$artist':  artist.lower(),
                '$sortartist': sortname.lower(),
                '$album':   album.lower(),
                '$year':        year,
                '$type':  releasetype.lower(),
                '$first':   firstchar.lower(),
                '$originalfolder': origfolder.lower()
            }

    folder = helpers.replace_all(headphones.FOLDER_FORMAT.strip(), values)

    folder = helpers.replace_illegal_chars(folder, type="folder")
    folder = folder.replace('./', '_/').replace('/.','/_')

    if folder.endswith('.'):
        folder = folder[:-1] + '_'

    if folder.startswith('.'):
        folder = '_' + folder[1:]

    # Grab our list of files early on so we can determine if we need to create
    # the lossy_dest_dir, lossless_dest_dir, or both
    files_to_move = []
    lossy_media = False
    lossless_media = False

    if find_in_path(albumpath,
                    extra_formats=headphones.LOSSY_MEDIA_FORMATS,
                    use_MF=False):
        lossy_media = True
    if find_in_path(albumpath,
                    extra_formats=headphones.LOSSLESS_MEDIA_FORMATS,
                    use_MF=False):
        lossless_media = True

    # Do some sanity checking to see what directories we need to create:
    make_lossy_folder = False
    make_lossless_folder = False

    lossy_destination_path = os.path.normpath(os.path.join(headphones.DESTINATION_DIR, folder)).encode(headphones.SYS_ENCODING, 'replace')
    lossless_destination_path = os.path.normpath(os.path.join(headphones.LOSSLESS_DESTINATION_DIR, folder)).encode(headphones.SYS_ENCODING, 'replace')

    # If they set a destination dir for lossless media, only create the lossy folder if there is lossy media
    if headphones.LOSSLESS_DESTINATION_DIR:
        if lossy_media:
            make_lossy_folder = True
        if lossless_media:
            make_lossless_folder = True
    # If they haven't set a lossless dest_dir, just create the "lossy" folder
    else:
        make_lossy_folder = True

    last_folder = headphones.FOLDER_FORMAT.strip().split('/')[-1]

    if make_lossless_folder:
        # Only rename the folder if they use the album name, otherwise merge into existing folder
        if os.path.exists(lossless_destination_path) and 'album' in last_folder.lower():

            create_duplicate_folder = False

            if headphones.REPLACE_EXISTING_FOLDERS:
                try:
                    shutil.rmtree(lossless_destination_path)
                except Exception, e:
                    logger.error("Error deleting existing folder: %s. Creating duplicate folder. Error: %s" % (lossless_destination_path.decode(headphones.SYS_ENCODING, 'replace'), e))
                    create_duplicate_folder = True

            if not headphones.REPLACE_EXISTING_FOLDERS or create_duplicate_folder:
                temp_folder = folder

                i = 1
                while True:
                    newfolder = temp_folder + '[%i]' % i
                    lossless_destination_path = os.path.normpath(os.path.join(headphones.LOSSLESS_DESTINATION_DIR, newfolder)).encode(headphones.SYS_ENCODING, 'replace')
                    if os.path.exists(lossless_destination_path):
                        i += 1
                    else:
                        temp_folder = newfolder
                        break

        if not os.path.exists(lossless_destination_path):
            try:
                os.makedirs(lossless_destination_path)
            except Exception, e:
                logger.error('Could not create lossless folder for %s. (Error: %s)' % (release['AlbumTitle'], e))
                if not make_lossy_folder:
                    return [albumpath]

    if make_lossy_folder:
        if os.path.exists(lossy_destination_path) and 'album' in last_folder.lower():

            create_duplicate_folder = False

            if headphones.REPLACE_EXISTING_FOLDERS:
                try:
                    shutil.rmtree(lossy_destination_path)
                except Exception, e:
                    logger.error("Error deleting existing folder: %s. Creating duplicate folder. Error: %s" % (lossy_destination_path.decode(headphones.SYS_ENCODING, 'replace'), e))
                    create_duplicate_folder = True

            if not headphones.REPLACE_EXISTING_FOLDERS or create_duplicate_folder:
                temp_folder = folder

                i = 1
                while True:
                    newfolder = temp_folder + '[%i]' % i
                    lossy_destination_path = os.path.normpath(os.path.join(headphones.DESTINATION_DIR, newfolder)).encode(headphones.SYS_ENCODING, 'replace')
                    if os.path.exists(lossy_destination_path):
                        i += 1
                    else:
                        temp_folder = newfolder
                        break

        if not os.path.exists(lossy_destination_path):
            try:
                os.makedirs(lossy_destination_path)
            except Exception, e:
                logger.error('Could not create folder for %s. Not moving: %s' % (release['AlbumTitle'], e))
                return [albumpath]

    logger.info('Checking which files we need to move.....')

    # Move files to the destination folder, renaming them if they already exist
    # If we have two desination_dirs, move non-music files to both
    if make_lossy_folder and make_lossless_folder:

        for file_to_move in files_to_move:

            if any(file_to_move.lower().endswith('.' + x.lower()) for x in headphones.LOSSY_MEDIA_FORMATS):
                helpers.smartMove(file_to_move, lossy_destination_path)

            elif any(file_to_move.lower().endswith('.' + x.lower()) for x in headphones.LOSSLESS_MEDIA_FORMATS):
                helpers.smartMove(file_to_move, lossless_destination_path)

            # If it's a non-music file, move it to both dirs
            # TODO: Move specific-to-lossless files to the lossless dir only
            else:

                moved_to_lossy_folder = helpers.smartMove(file_to_move, lossy_destination_path, delete=False)
                moved_to_lossless_folder = helpers.smartMove(file_to_move, lossless_destination_path, delete=False)

                if moved_to_lossy_folder or moved_to_lossless_folder:
                    try:
                        os.remove(file_to_move)
                    except Exception, e:
                        logger.error("Error deleting file '" + file_to_move.decode(headphones.SYS_ENCODING, 'replace') + "' from source directory")
                else:
                    logger.error("Error copying '" + file_to_move.decode(headphones.SYS_ENCODING, 'replace') + "'. Not deleting from download directory")

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
        temp_fs.append(headphones.LOSSLESS_DESTINATION_DIR)

    if make_lossy_folder:
        temp_fs.append(headphones.DESTINATION_DIR)

    for temp_f in temp_fs:

        for f in folder_list:

            temp_f = os.path.join(temp_f, f)

            try:
                os.chmod(os.path.normpath(temp_f).encode(headphones.SYS_ENCODING, 'replace'), int(headphones.FOLDER_PERMISSIONS, 8))
            except Exception, e:
                logger.error("Error trying to change permissions on folder: %s. %s", temp_f, e)

    # If we failed to move all the files out of the directory, this will fail too
    try:
        shutil.rmtree(albumpath)
    except Exception, e:
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

            if any(downloaded_track.lower().endswith('.' + x.lower()) for x in headphones.LOSSLESS_MEDIA_FORMATS):
                lossless_items.append(beets.library.Item.from_path(downloaded_track))
            elif any(downloaded_track.lower().endswith('.' + x.lower()) for x in headphones.LOSSY_MEDIA_FORMATS):
                lossy_items.append(beets.library.Item.from_path(downloaded_track))
            else:
                logger.warn("Skipping: %s because it is not a mutagen friendly file format", downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
        except Exception, e:

            logger.error("Beets couldn't create an Item from: %s - not a media file? %s", downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), str(e))

    for items in [lossy_items, lossless_items]:

        if not items:
            continue

        try:
            cur_artist, cur_album, candidates, rec = autotag.tag_album(items, search_artist=helpers.latinToAscii(release['ArtistName']), search_album=helpers.latinToAscii(release['AlbumTitle']))
        except Exception, e:
            logger.error('Error getting recommendation: %s. Not writing metadata', e)
            return
        if str(rec) == 'recommendation.none':
            logger.warn('No accurate album match found for %s, %s -  not writing metadata', release['ArtistName'], release['AlbumTitle'])
            return

        if candidates:
            dist, info, mapping, extra_items, extra_tracks = candidates[0]
        else:
            logger.warn('No accurate album match found for %s, %s -  not writing metadata', release['ArtistName'], release['AlbumTitle'])
            return

        logger.info('Beets recommendation for tagging items: %s' % rec)

        # TODO: Handle extra_items & extra_tracks

        autotag.apply_metadata(info, mapping)

        for item in items:
            try:
                item.write()
                logger.info("Successfully applied metadata to: %s", item.path.decode(headphones.SYS_ENCODING, 'replace'))
            except Exception, e:
                logger.warn("Error writing metadata to '%s': %s", item.path.decode(headphones.SYS_ENCODING, 'replace'), str(e))

def embedLyrics(downloaded_track_list):
    logger.info('Adding lyrics')

    # TODO: If adding lyrics for flac & lossy, only fetch the lyrics once
    # and apply it to both files
    for downloaded_track in downloaded_track_list:
        track_title = downloaded_track.decode(headphones.SYS_ENCODING, 'replace')
        try:
            f = MediaFile(downloaded_track)
        except:
            logger.error('Could not read %s. Not checking lyrics', track_title)
            continue

        if f.albumartist and f.title:
            metalyrics = lyrics.getLyrics(f.albumartist, f.title)
        elif f.artist and f.title:
            metalyrics = lyrics.getLyrics(f.artist, f.title)
        else:
            logger.info('No artist/track metadata found for track: %s. Not fetching lyrics', track_title)
            metalyrics = None

        if metalyrics:
            logger.debug('Adding lyrics to: %s', track_title)
            f.lyrics = metalyrics
            try:
                f.save()
            except:
                logger.error('Cannot save lyrics to: %s. Skipping', track_title)
                continue
        else:
            logger.debug('No lyrics found for track: %s', track_title)


def renameFiles(albumpath, downloaded_track_list, release):
    logger.info('Renaming files')
    try:
        year = release['ReleaseDate'][:4]
    except TypeError:
        year = ''
    # Until tagging works better I'm going to rely on the already provided metadata

    for downloaded_track in downloaded_track_list:
        try:
            f = MediaFile(downloaded_track)
        except:
            logger.info("MediaFile couldn't parse: %s", downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
            continue

        if not f.disc:
            discnumber = ''
        else:
            discnumber = '%d' % f.disc

        if not f.track:
            tracknumber = ''
        else:
            tracknumber = '%02d' % f.track

        if not f.title:

            basename = os.path.basename(downloaded_track.decode(headphones.SYS_ENCODING, 'replace'))
            title = os.path.splitext(basename)[0]
            ext = os.path.splitext(basename)[1]

            new_file_name = helpers.cleanTitle(title) + ext

        else:
            title = f.title

            if release['ArtistName'] == "Various Artists" and f.artist:
                artistname = f.artist
            else:
                artistname = release['ArtistName']

            if artistname.startswith('The '):
                sortname = artistname[4:] + ", The"
            else:
                sortname = artistname

            values = {  '$Disc':        discnumber,
                        '$Track':       tracknumber,
                        '$Title':       title,
                        '$Artist':      artistname,
                        '$SortArtist':  sortname,
                        '$Album':       release['AlbumTitle'],
                        '$Year':        year,
                        '$disc':        discnumber,
                        '$track':       tracknumber,
                        '$title':       title.lower(),
                        '$artist':      artistname.lower(),
                        '$sortartist':  sortname.lower(),
                        '$album':       release['AlbumTitle'].lower(),
                        '$year':        year
                        }

            ext = os.path.splitext(downloaded_track)[1]

            new_file_name = helpers.replace_all(headphones.FILE_FORMAT.strip(), values).replace('/','_') + ext


        new_file_name = helpers.replace_illegal_chars(new_file_name).encode(headphones.SYS_ENCODING, 'replace')

        if headphones.FILE_UNDERSCORES:
            new_file_name = new_file_name.replace(' ', '_')

        if new_file_name.startswith('.'):
            new_file_name = new_file_name.replace(".", "_", 1)

        new_file = os.path.join(albumpath, new_file_name)

        if downloaded_track == new_file_name:
            logger.debug("Renaming for: " + downloaded_track.decode(headphones.SYS_ENCODING, 'replace') + " is not neccessary")
            continue

        logger.debug('Renaming %s ---> %s', downloaded_track.decode(headphones.SYS_ENCODING,'replace'), new_file_name.decode(headphones.SYS_ENCODING,'replace'))
        try:
            os.rename(downloaded_track, new_file)
        except Exception, e:
            logger.error('Error renaming file: %s. Error: %s', downloaded_track.decode(headphones.SYS_ENCODING, 'replace'), e)
            continue

def updateFilePermissions(albumpaths):

    for folder in albumpaths:
        logger.info("Updating file permissions in %s", folder)
        for r,d,f in os.walk(folder):
            for files in f:
                full_path = os.path.join(r, files)
                try:
                    os.chmod(full_path, int(headphones.FILE_PERMISSIONS, 8))
                except:
                    logger.error("Could not change permissions for file: %s", full_path)
                    continue

def renameUnprocessedFolder(albumpath):

    i = 0
    while True:
        if i == 0:
            new_folder_name = albumpath + ' (Unprocessed)'
        else:
            new_folder_name = albumpath + ' (Unprocessed)[%i]' % i

        if os.path.exists(new_folder_name):
            i += 1

        else:
            os.rename(albumpath, new_folder_name)
            return

def forcePostProcess(dir=None, expand_subfolders=True, album_dir=None):

    if album_dir:
        folders = [album_dir.encode(headphones.SYS_ENCODING, 'replace')]

    else:
        download_dirs = []
        if dir:
            download_dirs.append(dir.encode(headphones.SYS_ENCODING, 'replace'))
        if headphones.DOWNLOAD_DIR and not dir:
            download_dirs.append(headphones.DOWNLOAD_DIR.encode(headphones.SYS_ENCODING, 'replace'))
        if headphones.DOWNLOAD_TORRENT_DIR and not dir:
            download_dirs.append(headphones.DOWNLOAD_TORRENT_DIR.encode(headphones.SYS_ENCODING, 'replace'))

        # If DOWNLOAD_DIR and DOWNLOAD_TORRENT_DIR are the same, remove the duplicate to prevent us from trying to process the same folder twice.
        download_dirs = list(set(download_dirs))

        logger.info('Checking to see if there are any folders to process in download_dir(s): %s', download_dirs)
        # Get a list of folders in the download_dir
        folders = []

        for download_dir in download_dirs:
            if not os.path.isdir(download_dir):
                logger.warn('Directory %s does not exist. Skipping', download_dir)
                continue
            for folder in os.listdir(download_dir):
                path_to_folder = os.path.join(download_dir, folder)

                if os.path.isdir(path_to_folder):
                    subfolders = helpers.expand_subfolders(path_to_folder)

                    if expand_subfolders and subfolders is not None:
                        folders.extend(subfolders)
                    else:
                        folders.append(path_to_folder)

        if len(folders):
            logger.info('Found %i folders to process', len(folders))
        else:
            logger.info('Found no folders to process in: %s', download_dirs)

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
        snatched = myDB.action('SELECT AlbumID, Title, Kind, Status from snatched WHERE FolderName LIKE ?', [folder_basename]).fetchone()

        if snatched:
            if headphones.KEEP_TORRENT_FILES and snatched['Kind'] == 'torrent' and snatched['Status'] == 'Processed':
                logger.info('%s is a torrent folder being preserved for seeding and has already been processed. Skipping.', folder_basename)
                continue
            else:
                logger.info('Found a match in the database: %s. Verifying to make sure it is the correct album', snatched['Title'])
                verify(snatched['AlbumID'], folder, snatched['Kind'])
                continue

        # Attempt 2a: parse the folder name into a valid format
        try:
            logger.debug('Attempting to extract name, album and year from folder name')
            name, album, year = helpers.extract_data(folder_basename)
        except Exception as e:
            name = album = year = None

        if name and album:
            release = myDB.action('SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE ArtistName LIKE ? and AlbumTitle LIKE ?', [name, album]).fetchone()
            if release:
                logger.info('Found a match in the database: %s - %s. Verifying to make sure it is the correct album', release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s - %s', name, album)
                try:
                    rgid = mb.findAlbumID(helpers.latinToAscii(name), helpers.latinToAscii(album))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)

        # Attempt 2b: deduce meta data into a valid format
        try:
            logger.debug('Attempting to extract name, album and year from metadata')
            name, album, year = helpers.extract_metadata(folder)
        except Exception as e:
            name = album = year = None

        if name and album:
            release = myDB.action('SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE ArtistName LIKE ? and AlbumTitle LIKE ?', [name, album]).fetchone()
            if release:
                logger.info('Found a match in the database: %s - %s. Verifying to make sure it is the correct album', release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s - %s', name, album)
                try:
                    rgid = mb.findAlbumID(helpers.latinToAscii(name), helpers.latinToAscii(album))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)

        # Attempt 3: strip release group id from filename
        try:
            logger.debug('Attempting to extract release group from folder name')
            possible_rgid = folder_basename[-36:]
            # re pattern match: [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
            rgid = uuid.UUID(possible_rgid)
        except:
            logger.info("Couldn't parse '%s' into any valid format. If adding albums from another source, they must be in an 'Artist - Album [Year]' format, or end with the musicbrainz release group id", folder_basename)
            rgid = possible_rgid = None

        if rgid:
            rgid = possible_rgid
            release = myDB.action('SELECT ArtistName, AlbumTitle, AlbumID from albums WHERE AlbumID=?', [rgid]).fetchone()
            if release:
                logger.info('Found a match in the database: %s - %s. Verifying to make sure it is the correct album', release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder, forced=True)
                continue
            else:
                logger.info('Found a (possibly) valid Musicbrainz identifier in album folder name - continuing post-processing')
                verify(rgid, folder, forced=True)
                continue

        # Attempt 4: Hail mary. Just assume the folder name is the album name if it doesn't have a separator in it
        logger.debug('Attempt to extract album name by assuming it is the folder name')

        if '-' not in folder_basename:
            release = myDB.action('SELECT AlbumID, ArtistName, AlbumTitle from albums WHERE AlbumTitle LIKE ?', [folder_basename]).fetchone()
            if release:
                logger.info('Found a match in the database: %s - %s. Verifying to make sure it is the correct album', release['ArtistName'], release['AlbumTitle'])
                verify(release['AlbumID'], folder)
                continue
            else:
                logger.info('Querying MusicBrainz for the release group id for: %s', folder_basename)
                try:
                    rgid = mb.findAlbumID(album=helpers.latinToAscii(folder_basename))
                except:
                    logger.error('Can not get release information for this album')
                    rgid = None

                if rgid:
                    verify(rgid, folder)
                    continue
                else:
                    logger.info('No match found on MusicBrainz for: %s - %s', name, album)
