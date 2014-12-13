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

# NZBGet support added by CurlyMo <curlymoo1@gmail.com> as a part of XBian - XBMC on the Raspberry Pi

from headphones import logger, searcher, db, importer, mb, lastfm, librarysync, helpers, notifiers
from headphones.helpers import checked, radio, today, cleanName

from mako.lookup import TemplateLookup
from mako import exceptions

from operator import itemgetter

import headphones
import threading
import cherrypy
import urllib2
import hashlib
import random
import urllib
import json
import time
import sys
import os

try:
    # pylint:disable=E0611
    # ignore this error because we are catching the ImportError
    from collections import OrderedDict
    # pylint:enable=E0611
except ImportError:
    # Python 2.6.x fallback, from libs
    from ordereddict import OrderedDict


def serve_template(templatename, **kwargs):

    interface_dir = os.path.join(str(headphones.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), headphones.CONFIG.INTERFACE)

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def home(self):
        myDB = db.DBConnection()
        artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return serve_template(templatename="index.html", title="Home", artists=artists)

    @cherrypy.expose
    def artistPage(self, ArtistID):
        myDB = db.DBConnection()
        artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()

        # Don't redirect to the artist page until it has the bare minimum info inserted
        # Redirect to the home page if we still can't get it after 5 seconds
        retry = 0

        while not artist and retry < 5:
            time.sleep(1)
            artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
            retry += 1

        if not artist:
            raise cherrypy.HTTPRedirect("home")

        albums = myDB.select('SELECT * from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])

        # Serve the extras up as a dict to make things easier for new templates (append new extras to the end)
        extras_list = headphones.POSSIBLE_EXTRAS
        if artist['Extras']:
            artist_extras = map(int, artist['Extras'].split(','))
        else:
            artist_extras = []

        extras_dict = OrderedDict()

        i = 1
        for extra in extras_list:
            if i in artist_extras:
                extras_dict[extra] = "checked"
            else:
                extras_dict[extra] = ""
            i += 1

        return serve_template(templatename="artist.html", title=artist['ArtistName'], artist=artist, albums=albums, extras=extras_dict)

    @cherrypy.expose
    def albumPage(self, AlbumID):
        myDB = db.DBConnection()
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()

        retry = 0
        while retry < 5:
            if not album:
                time.sleep(1)
                album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
                retry += 1
            else:
                break

        if not album:
            raise cherrypy.HTTPRedirect("home")

        tracks = myDB.select('SELECT * from tracks WHERE AlbumID=? ORDER BY CAST(TrackNumber AS INTEGER)', [AlbumID])
        description = myDB.action('SELECT * from descriptions WHERE ReleaseGroupID=?', [AlbumID]).fetchone()

        if not album['ArtistName']:
            title = ' - '
        else:
            title = album['ArtistName'] + ' - '
        if not album['AlbumTitle']:
            title = title + ""
        else:
            title = title + album['AlbumTitle']
        return serve_template(templatename="album.html", title=title, album=album, tracks=tracks, description=description)

    @cherrypy.expose
    def search(self, name, type):
        if len(name) == 0:
            raise cherrypy.HTTPRedirect("home")
        if type == 'artist':
            searchresults = mb.findArtist(name, limit=100)
        else:
            searchresults = mb.findRelease(name, limit=100)
        return serve_template(templatename="searchresults.html", title='Search Results for: "' + name + '"', searchresults=searchresults, name=name, type=type)

    @cherrypy.expose
    def addArtist(self, artistid):
        thread = threading.Thread(target=importer.addArtisttoDB, args=[artistid])
        thread.start()
        thread.join(1)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % artistid)

    @cherrypy.expose
    def getExtras(self, ArtistID, newstyle=False, **kwargs):
        # if calling this function without the newstyle, they're using the old format
        # which doesn't separate extras, so we'll grab all of them
        #
        # If they are, we need to convert kwargs to string format
        if not newstyle:
            extras = "1,2,3,4,5,6,7,8,9,10,11,12,13,14"
        else:
            temp_extras_list = []
            i = 1
            for extra in headphones.POSSIBLE_EXTRAS:
                if extra in kwargs:
                    temp_extras_list.append(i)
                i += 1
            extras = ','.join(str(n) for n in temp_extras_list)

        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'IncludeExtras': 1,
                        'Extras': extras}
        myDB.upsert("artists", newValueDict, controlValueDict)
        thread = threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, True, False])
        thread.start()
        thread.join(1)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    @cherrypy.expose
    def removeExtras(self, ArtistID, ArtistName):
        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'IncludeExtras': 0}
        myDB.upsert("artists", newValueDict, controlValueDict)
        extraalbums = myDB.select('SELECT AlbumID from albums WHERE ArtistID=? AND Status="Skipped" AND Type!="Album"', [ArtistID])
        for album in extraalbums:
            myDB.action('DELETE from tracks WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
            myDB.action('DELETE from albums WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
            myDB.action('DELETE from allalbums WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
            myDB.action('DELETE from alltracks WHERE ArtistID=? AND AlbumID=?', [ArtistID, album['AlbumID']])
            myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [album['AlbumID']])
            from headphones import cache
            c = cache.Cache()
            c.remove_from_cache(AlbumID=album['AlbumID'])
        importer.finalize_update(ArtistID, ArtistName)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    @cherrypy.expose
    def pauseArtist(self, ArtistID):
        logger.info(u"Pausing artist: " + ArtistID)
        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'Status': 'Paused'}
        myDB.upsert("artists", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    @cherrypy.expose
    def resumeArtist(self, ArtistID):
        logger.info(u"Resuming artist: " + ArtistID)
        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'Status': 'Active'}
        myDB.upsert("artists", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    def removeArtist(self, ArtistID):
        logger.info(u"Deleting all traces of artist: " + ArtistID)
        myDB = db.DBConnection()
        namecheck = myDB.select('SELECT ArtistName from artists where ArtistID=?', [ArtistID])
        for name in namecheck:
            artistname = name['ArtistName']
        myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])

        from headphones import cache
        c = cache.Cache()

        rgids = myDB.select('SELECT AlbumID FROM albums WHERE ArtistID=? UNION SELECT AlbumID FROM allalbums WHERE ArtistID=?', [ArtistID, ArtistID])
        for rgid in rgids:
            albumid = rgid['AlbumID']
            myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [albumid])
            myDB.action('DELETE from have WHERE Matched=?', [albumid])
            c.remove_from_cache(AlbumID=albumid)
            myDB.action('DELETE from descriptions WHERE ReleaseGroupID=?', [albumid])

        myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
        myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

        myDB.action('DELETE from allalbums WHERE ArtistID=?', [ArtistID])
        myDB.action('DELETE from alltracks WHERE ArtistID=?', [ArtistID])
        myDB.action('DELETE from have WHERE ArtistName=?', [artistname])
        c.remove_from_cache(ArtistID=ArtistID)
        myDB.action('DELETE from descriptions WHERE ArtistID=?', [ArtistID])
        myDB.action('INSERT OR REPLACE into blacklist VALUES (?)', [ArtistID])

    @cherrypy.expose
    def deleteArtist(self, ArtistID):
        self.removeArtist(ArtistID)
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def deleteEmptyArtists(self):
        logger.info(u"Deleting all empty artists")
        myDB = db.DBConnection()
        emptyArtistIDs = [row['ArtistID'] for row in myDB.select("SELECT ArtistID FROM artists WHERE LatestAlbum IS NULL")]
        for ArtistID in emptyArtistIDs:
            self.removeArtist(ArtistID)

    @cherrypy.expose
    def refreshArtist(self, ArtistID):
        thread = threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, False, True])
        thread.start()
        thread.join(1)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    @cherrypy.expose
    def markAlbums(self, ArtistID=None, action=None, **args):
        myDB = db.DBConnection()
        if action == 'WantedNew' or action == 'WantedLossless':
            newaction = 'Wanted'
        else:
            newaction = action
        for mbid in args:
            logger.info("Marking %s as %s" % (mbid, newaction))
            controlValueDict = {'AlbumID': mbid}
            newValueDict = {'Status': newaction}
            myDB.upsert("albums", newValueDict, controlValueDict)
            if action == 'Wanted':
                searcher.searchforalbum(mbid, new=False)
            if action == 'WantedNew':
                searcher.searchforalbum(mbid, new=True)
            if action == 'WantedLossless':
                searcher.searchforalbum(mbid, lossless=True)
            if ArtistID:
                ArtistIDT = ArtistID
            else:
                ArtistIDT = myDB.action('SELECT ArtistID FROM albums WHERE AlbumID=?', [mbid]).fetchone()[0]
            myDB.action('UPDATE artists SET TotalTracks=(SELECT COUNT(*) FROM tracks WHERE ArtistID = ? AND AlbumTitle IN (SELECT AlbumTitle FROM albums WHERE Status != "Ignored")) WHERE ArtistID = ?', [ArtistIDT, ArtistIDT])
        if ArtistID:
            raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
        else:
            raise cherrypy.HTTPRedirect("upcoming")

    @cherrypy.expose
    def addArtists(self, action=None, **args):
        if action == "add":
            threading.Thread(target=importer.artistlist_to_mbids, args=[args, True]).start()
        if action == "ignore":
            myDB = db.DBConnection()
            for artist in args:
                myDB.action('DELETE FROM newartists WHERE ArtistName=?', [artist.decode(headphones.SYS_ENCODING, 'replace')])
                myDB.action('UPDATE have SET Matched="Ignored" WHERE ArtistName=?', [artist.decode(headphones.SYS_ENCODING, 'replace')])
                logger.info("Artist %s removed from new artist list and set to ignored" % artist)
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def queueAlbum(self, AlbumID, ArtistID=None, new=False, redirect=None, lossless=False):
        logger.info(u"Marking album: " + AlbumID + " as wanted...")
        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': AlbumID}
        if lossless:
            newValueDict = {'Status': 'Wanted Lossless'}
            logger.info("...lossless only!")
        else:
            newValueDict = {'Status': 'Wanted'}
        myDB.upsert("albums", newValueDict, controlValueDict)
        searcher.searchforalbum(AlbumID, new)
        if ArtistID:
            redirect = "artistPage?ArtistID=%s" % ArtistID
        raise cherrypy.HTTPRedirect(redirect)

    @cherrypy.expose
    def choose_specific_download(self, AlbumID):
        results = searcher.searchforalbum(AlbumID, choose_specific_download=True)

        results_as_dicts = []

        for result in results:

            result_dict = {
                'title': result[0],
                'size': result[1],
                'url': result[2],
                'provider': result[3],
                'kind': result[4]
            }
            results_as_dicts.append(result_dict)
        s = json.dumps(results_as_dicts)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s

    @cherrypy.expose
    def download_specific_release(self, AlbumID, title, size, url, provider, kind, **kwargs):
        # Handle situations where the torrent url contains arguments that are parsed
        if kwargs:
            url = urllib2.quote(url, safe=":?/=&") + '&' + urllib.urlencode(kwargs)
        try:
            result = [(title, int(size), url, provider, kind)]
        except ValueError:
            result = [(title, float(size), url, provider, kind)]

        logger.info(u"Making sure we can download the chosen result")
        (data, bestqual) = searcher.preprocess(result)

        if data and bestqual:
          myDB = db.DBConnection()
          album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
          searcher.send_to_downloader(data, bestqual, album)

    @cherrypy.expose
    def unqueueAlbum(self, AlbumID, ArtistID):
        logger.info(u"Marking album: " + AlbumID + "as skipped...")
        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': AlbumID}
        newValueDict = {'Status': 'Skipped'}
        myDB.upsert("albums", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)

    @cherrypy.expose
    def deleteAlbum(self, AlbumID, ArtistID=None):
        logger.info(u"Deleting all traces of album: " + AlbumID)
        myDB = db.DBConnection()

        myDB.action('DELETE from have WHERE Matched=?', [AlbumID])
        album = myDB.action('SELECT ArtistID, ArtistName, AlbumTitle from albums where AlbumID=?', [AlbumID]).fetchone()
        if album:
            ArtistID = album['ArtistID']
            myDB.action('DELETE from have WHERE ArtistName=? AND AlbumTitle=?', [album['ArtistName'], album['AlbumTitle']])

        myDB.action('DELETE from albums WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from tracks WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from allalbums WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from alltracks WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [AlbumID])
        myDB.action('DELETE from descriptions WHERE ReleaseGroupID=?', [AlbumID])

        from headphones import cache
        c = cache.Cache()
        c.remove_from_cache(AlbumID=AlbumID)

        if ArtistID:
            raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
        else:
            raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def switchAlbum(self, AlbumID, ReleaseID):
        """
        Take the values from allalbums/alltracks (based on the ReleaseID) and
        swap it into the album & track tables
        """
        from headphones import albumswitcher
        albumswitcher.switch(AlbumID, ReleaseID)
        raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % AlbumID)

    @cherrypy.expose
    def editSearchTerm(self, AlbumID, SearchTerm):
        logger.info(u"Updating search term for albumid: " + AlbumID)
        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': AlbumID}
        newValueDict = {'SearchTerm': SearchTerm}
        myDB.upsert("albums", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % AlbumID)

    @cherrypy.expose
    def upcoming(self):
        myDB = db.DBConnection()
        upcoming = myDB.select("SELECT * from albums WHERE ReleaseDate > date('now') order by ReleaseDate ASC")
        wanted = myDB.select("SELECT * from albums WHERE Status='Wanted'")
        return serve_template(templatename="upcoming.html", title="Upcoming", upcoming=upcoming, wanted=wanted)

    @cherrypy.expose
    def manage(self):
        myDB = db.DBConnection()
        emptyArtists = myDB.select("SELECT * FROM artists WHERE LatestAlbum IS NULL")
        return serve_template(templatename="manage.html", title="Manage", emptyArtists=emptyArtists)

    @cherrypy.expose
    def manageArtists(self):
        myDB = db.DBConnection()
        artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return serve_template(templatename="manageartists.html", title="Manage Artists", artists=artists)

    @cherrypy.expose
    def manageAlbums(self, Status=None):
        myDB = db.DBConnection()
        if Status == "Upcoming":
            albums = myDB.select("SELECT * from albums WHERE ReleaseDate > date('now')")
        elif Status:
            albums = myDB.select('SELECT * from albums WHERE Status=?', [Status])
        else:
            albums = myDB.select('SELECT * from albums')
        return serve_template(templatename="managealbums.html", title="Manage Albums", albums=albums)

    @cherrypy.expose
    def manageNew(self):
        myDB = db.DBConnection()
        newartists = myDB.select('SELECT * from newartists')
        return serve_template(templatename="managenew.html", title="Manage New Artists", newartists=newartists)

    @cherrypy.expose
    def manageUnmatched(self):
        myDB = db.DBConnection()
        have_album_dictionary = []
        headphones_album_dictionary = []
        have_albums = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName from have WHERE Matched = "Failed" GROUP BY AlbumTitle ORDER BY ArtistName')
        for albums in have_albums:
            #Have to skip over manually matched tracks
            if albums['ArtistName'] and albums['AlbumTitle'] and albums['TrackTitle']:
                original_clean = helpers.cleanName(albums['ArtistName'] + " " + albums['AlbumTitle'] + " " + albums['TrackTitle'])
            # else:
            #     original_clean = None
                if original_clean == albums['CleanName']:
                    have_dict = {'ArtistName': albums['ArtistName'], 'AlbumTitle': albums['AlbumTitle']}
                    have_album_dictionary.append(have_dict)
        headphones_albums = myDB.select('SELECT ArtistName, AlbumTitle from albums ORDER BY ArtistName')
        for albums in headphones_albums:
            if albums['ArtistName'] and albums['AlbumTitle']:
                headphones_dict = {'ArtistName': albums['ArtistName'], 'AlbumTitle': albums['AlbumTitle']}
                headphones_album_dictionary.append(headphones_dict)
        #unmatchedalbums = [f for f in have_album_dictionary if f not in [x for x in headphones_album_dictionary]]

        check = set([(cleanName(d['ArtistName']).lower(), cleanName(d['AlbumTitle']).lower()) for d in headphones_album_dictionary])
        unmatchedalbums = [d for d in have_album_dictionary if (cleanName(d['ArtistName']).lower(), cleanName(d['AlbumTitle']).lower()) not in check]

        return serve_template(templatename="manageunmatched.html", title="Manage Unmatched Items", unmatchedalbums=unmatchedalbums)

    @cherrypy.expose
    def markUnmatched(self, action=None, existing_artist=None, existing_album=None, new_artist=None, new_album=None):
        myDB = db.DBConnection()

        if action == "ignoreArtist":
            artist = existing_artist
            myDB.action('UPDATE have SET Matched="Ignored" WHERE ArtistName=? AND Matched = "Failed"', [artist])

        elif action == "ignoreAlbum":
            artist = existing_artist
            album = existing_album
            myDB.action('UPDATE have SET Matched="Ignored" WHERE ArtistName=? AND AlbumTitle=? AND Matched = "Failed"', (artist, album))

        elif action == "matchArtist":
            existing_artist_clean = helpers.cleanName(existing_artist).lower()
            new_artist_clean = helpers.cleanName(new_artist).lower()
            if new_artist_clean != existing_artist_clean:
                have_tracks = myDB.action('SELECT Matched, CleanName, Location, BitRate, Format FROM have WHERE ArtistName=?', [existing_artist])
                update_count = 0
                for entry in have_tracks:
                    old_clean_filename = entry['CleanName']
                    if old_clean_filename.startswith(existing_artist_clean):
                        new_clean_filename = old_clean_filename.replace(existing_artist_clean, new_artist_clean, 1)
                        myDB.action('UPDATE have SET CleanName=? WHERE ArtistName=? AND CleanName=?', [new_clean_filename, existing_artist, old_clean_filename])
                        controlValueDict = {"CleanName": new_clean_filename}
                        newValueDict = {"Location": entry['Location'],
                                        "BitRate": entry['BitRate'],
                                        "Format": entry['Format']
                                        }
                        #Attempt to match tracks with new CleanName
                        match_alltracks = myDB.action('SELECT CleanName from alltracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_alltracks:
                            myDB.upsert("alltracks", newValueDict, controlValueDict)
                        match_tracks = myDB.action('SELECT CleanName, AlbumID from tracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_tracks:
                            myDB.upsert("tracks", newValueDict, controlValueDict)
                            myDB.action('UPDATE have SET Matched="Manual" WHERE CleanName=?', [new_clean_filename])
                            update_count += 1
                    #This was throwing errors and I don't know why, but it seems to be working fine.
                    #else:
                        #logger.info("There was an error modifying Artist %s. This should not have happened" % existing_artist)
                logger.info("Manual matching yielded %s new matches for Artist: %s" % (update_count, new_artist))
                if update_count > 0:
                    librarysync.update_album_status()
            else:
                logger.info("Artist %s already named appropriately; nothing to modify" % existing_artist)

        elif action == "matchAlbum":
            existing_artist_clean = helpers.cleanName(existing_artist).lower()
            new_artist_clean = helpers.cleanName(new_artist).lower()
            existing_album_clean = helpers.cleanName(existing_album).lower()
            new_album_clean = helpers.cleanName(new_album).lower()
            existing_clean_string = existing_artist_clean + " " + existing_album_clean
            new_clean_string = new_artist_clean + " " + new_album_clean
            if existing_clean_string != new_clean_string:
                have_tracks = myDB.action('SELECT Matched, CleanName, Location, BitRate, Format FROM have WHERE ArtistName=? AND AlbumTitle=?', (existing_artist, existing_album))
                update_count = 0
                for entry in have_tracks:
                    old_clean_filename = entry['CleanName']
                    if old_clean_filename.startswith(existing_clean_string):
                        new_clean_filename = old_clean_filename.replace(existing_clean_string, new_clean_string, 1)
                        myDB.action('UPDATE have SET CleanName=? WHERE ArtistName=? AND AlbumTitle=? AND CleanName=?', [new_clean_filename, existing_artist, existing_album, old_clean_filename])
                        controlValueDict = {"CleanName": new_clean_filename}
                        newValueDict = {"Location": entry['Location'],
                                        "BitRate": entry['BitRate'],
                                        "Format": entry['Format']
                                        }
                        #Attempt to match tracks with new CleanName
                        match_alltracks = myDB.action('SELECT CleanName from alltracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_alltracks:
                            myDB.upsert("alltracks", newValueDict, controlValueDict)
                        match_tracks = myDB.action('SELECT CleanName, AlbumID from tracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_tracks:
                            myDB.upsert("tracks", newValueDict, controlValueDict)
                            myDB.action('UPDATE have SET Matched="Manual" WHERE CleanName=?', [new_clean_filename])
                            album_id = match_tracks['AlbumID']
                            update_count += 1
                    #This was throwing errors and I don't know why, but it seems to be working fine.
                    #else:
                        #logger.info("There was an error modifying Artist %s / Album %s with clean name %s" % (existing_artist, existing_album, existing_clean_string))
                logger.info("Manual matching yielded %s new matches for Artist: %s / Album: %s" % (update_count, new_artist, new_album))
                if update_count > 0:
                    librarysync.update_album_status(album_id)
            else:
                logger.info("Artist %s / Album %s already named appropriately; nothing to modify" % (existing_artist, existing_album))

    @cherrypy.expose
    def manageManual(self):
        myDB = db.DBConnection()
        manual_albums = []
        manualalbums = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName, Matched from have')
        for albums in manualalbums:
            if albums['ArtistName'] and albums['AlbumTitle'] and albums['TrackTitle']:
                original_clean = helpers.cleanName(albums['ArtistName'] + " " + albums['AlbumTitle'] + " " + albums['TrackTitle'])
                if albums['Matched'] == "Ignored" or albums['Matched'] == "Manual" or albums['CleanName'] != original_clean:
                    if albums['Matched'] == "Ignored":
                        album_status = "Ignored"
                    elif albums['Matched'] == "Manual" or albums['CleanName'] != original_clean:
                        album_status = "Matched"
                    manual_dict = {'ArtistName': albums['ArtistName'], 'AlbumTitle': albums['AlbumTitle'], 'AlbumStatus': album_status}
                    if manual_dict not in manual_albums:
                        manual_albums.append(manual_dict)
        manual_albums_sorted = sorted(manual_albums, key=itemgetter('ArtistName', 'AlbumTitle'))

        return serve_template(templatename="managemanual.html", title="Manage Manual Items", manualalbums=manual_albums_sorted)

    @cherrypy.expose
    def markManual(self, action=None, existing_artist=None, existing_album=None):
        myDB = db.DBConnection()
        if action == "unignoreArtist":
            artist = existing_artist
            myDB.action('UPDATE have SET Matched="Failed" WHERE ArtistName=? AND Matched="Ignored"', [artist])
            logger.info("Artist: %s successfully restored to unmatched list" % artist)

        elif action == "unignoreAlbum":
            artist = existing_artist
            album = existing_album
            myDB.action('UPDATE have SET Matched="Failed" WHERE ArtistName=? AND AlbumTitle=? AND Matched="Ignored"', (artist, album))
            logger.info("Album: %s successfully restored to unmatched list" % album)

        elif action == "unmatchArtist":
            artist = existing_artist
            update_clean = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName, Matched from have WHERE ArtistName=?', [artist])
            update_count = 0
            for tracks in update_clean:
                original_clean = helpers.cleanName(tracks['ArtistName'] + " " + tracks['AlbumTitle'] + " " + tracks['TrackTitle']).lower()
                album = tracks['AlbumTitle']
                track_title = tracks['TrackTitle']
                if tracks['CleanName'] != original_clean:
                    myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE have SET CleanName=?, Matched="Failed" WHERE ArtistName=? AND AlbumTitle=? AND TrackTitle=?', (original_clean, artist, album, track_title))
                    update_count += 1
            if update_count > 0:
                librarysync.update_album_status()
            logger.info("Artist: %s successfully restored to unmatched list" % artist)

        elif action == "unmatchAlbum":
            artist = existing_artist
            album = existing_album
            update_clean = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName, Matched from have WHERE ArtistName=? AND AlbumTitle=?', (artist, album))
            update_count = 0
            for tracks in update_clean:
                original_clean = helpers.cleanName(tracks['ArtistName'] + " " + tracks['AlbumTitle'] + " " + tracks['TrackTitle']).lower()
                track_title = tracks['TrackTitle']
                if tracks['CleanName'] != original_clean:
                    album_id_check = myDB.action('SELECT AlbumID from tracks WHERE CleanName=?', [tracks['CleanName']]).fetchone()
                    if album_id_check:
                        album_id = album_id_check[0]
                    myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE have SET CleanName=?, Matched="Failed" WHERE ArtistName=? AND AlbumTitle=? AND TrackTitle=?', (original_clean, artist, album, track_title))
                    update_count += 1
            if update_count > 0:
                librarysync.update_album_status(album_id)
            logger.info("Album: %s successfully restored to unmatched list" % album)

    @cherrypy.expose
    def markArtists(self, action=None, **args):
        myDB = db.DBConnection()
        artistsToAdd = []
        for ArtistID in args:
            if action == 'delete':
                self.removeArtist(ArtistID)
            elif action == 'pause':
                controlValueDict = {'ArtistID': ArtistID}
                newValueDict = {'Status': 'Paused'}
                myDB.upsert("artists", newValueDict, controlValueDict)
            elif action == 'resume':
                controlValueDict = {'ArtistID': ArtistID}
                newValueDict = {'Status': 'Active'}
                myDB.upsert("artists", newValueDict, controlValueDict)
            else:
                artistsToAdd.append(ArtistID)
        if len(artistsToAdd) > 0:
            logger.debug("Refreshing artists: %s" % artistsToAdd)
            threading.Thread(target=importer.addArtistIDListToDB, args=[artistsToAdd]).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def importLastFM(self, username):
        headphones.CONFIG.LASTFM_USERNAME = username
        headphones.CONFIG.write()
        threading.Thread(target=lastfm.getArtists).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def importLastFMTag(self, tag, limit):
        threading.Thread(target=lastfm.getTagTopArtists, args=(tag, limit)).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def importItunes(self, path):
        headphones.CONFIG.PATH_TO_XML = path
        headphones.CONFIG.write()
        thread = threading.Thread(target=importer.itunesImport, args=[path])
        thread.start()
        thread.join(10)
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def musicScan(self, path, scan=0, redirect=None, autoadd=0, libraryscan=0):
        headphones.CONFIG.LIBRARYSCAN = libraryscan
        headphones.CONFIG.AUTO_ADD_ARTISTS = autoadd
        headphones.CONFIG.MUSIC_DIR = path
        headphones.CONFIG.write()
        if scan:
            try:
                threading.Thread(target=librarysync.libraryScan).start()
            except Exception as e:
                logger.error('Unable to complete the scan: %s' % e)
        if redirect:
            raise cherrypy.HTTPRedirect(redirect)
        else:
            raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def forceUpdate(self):
        from headphones import updater
        threading.Thread(target=updater.dbUpdate, args=[False]).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def forceFullUpdate(self):
        from headphones import updater
        threading.Thread(target=updater.dbUpdate, args=[True]).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def forceSearch(self):
        from headphones import searcher
        threading.Thread(target=searcher.searchforalbum).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def forcePostProcess(self, dir=None, album_dir=None):
        from headphones import postprocessor
        threading.Thread(target=postprocessor.forcePostProcess, kwargs={'dir': dir, 'album_dir': album_dir}).start()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def checkGithub(self):
        from headphones import versioncheck
        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def history(self):
        myDB = db.DBConnection()
        history = myDB.select('''SELECT * from snatched WHERE Status NOT LIKE "Seed%" order by DateAdded DESC''')
        return serve_template(templatename="history.html", title="History", history=history)

    @cherrypy.expose
    def logs(self):
        return serve_template(templatename="logs.html", title="Log", lineList=headphones.LOG_LIST)

    @cherrypy.expose
    def clearLogs(self):
        headphones.LOG_LIST = []
        logger.info("Web logs cleared")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def toggleVerbose(self):
        headphones.VERBOSE = not headphones.VERBOSE
        logger.initLogger(console=not headphones.QUIET,
            log_dir=headphones.CONFIG.LOG_DIR, verbose=headphones.VERBOSE)
        logger.info("Verbose toggled, set to %s", headphones.VERBOSE)
        logger.debug("If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def getLog(self, iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0="desc", sSearch="", **kwargs):
        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)

        filtered = []
        if sSearch == "":
            filtered = headphones.LOG_LIST[::]
        else:
            filtered = [row for row in headphones.LOG_LIST for column in row if sSearch.lower() in column.lower()]

        sortcolumn = 0
        if iSortCol_0 == '1':
            sortcolumn = 2
        elif iSortCol_0 == '2':
            sortcolumn = 1
        filtered.sort(key=lambda x: x[sortcolumn], reverse=sSortDir_0 == "desc")

        rows = filtered[iDisplayStart:(iDisplayStart + iDisplayLength)]
        rows = [[row[0], row[2], row[1]] for row in rows]

        return json.dumps({
            'iTotalDisplayRecords': len(filtered),
            'iTotalRecords': len(headphones.LOG_LIST),
            'aaData': rows,
        })

    @cherrypy.expose
    def getArtists_json(self, iDisplayStart=0, iDisplayLength=100, sSearch="", iSortCol_0='0', sSortDir_0='asc', **kwargs):
        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)
        filtered = []
        totalcount = 0
        myDB = db.DBConnection()

        sortcolumn = 'ArtistSortName'
        sortbyhavepercent = False
        if iSortCol_0 == '2':
            sortcolumn = 'Status'
        elif iSortCol_0 == '3':
            sortcolumn = 'ReleaseDate'
        elif iSortCol_0 == '4':
            sortbyhavepercent = True

        if sSearch == "":
            query = 'SELECT * from artists order by %s COLLATE NOCASE %s' % (sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT * from artists WHERE ArtistSortName LIKE "%' + sSearch + '%" OR LatestAlbum LIKE "%' + sSearch + '%"' + 'ORDER BY %s COLLATE NOCASE %s' % (sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from artists')[0][0]

        if sortbyhavepercent:
            filtered.sort(key=lambda x: (float(x['HaveTracks']) / x['TotalTracks'] if x['TotalTracks'] > 0 else 0.0, x['HaveTracks'] if x['HaveTracks'] else 0.0), reverse=sSortDir_0 == "asc")

        #can't figure out how to change the datatables default sorting order when its using an ajax datasource so ill
        #just reverse it here and the first click on the "Latest Album" header will sort by descending release date
        if sortcolumn == 'ReleaseDate':
            filtered.reverse()

        artists = filtered[iDisplayStart:(iDisplayStart + iDisplayLength)]
        rows = []
        for artist in artists:
            row = {"ArtistID": artist['ArtistID'],
                      "ArtistName": artist["ArtistName"],
                      "ArtistSortName": artist["ArtistSortName"],
                      "Status": artist["Status"],
                      "TotalTracks": artist["TotalTracks"],
                      "HaveTracks": artist["HaveTracks"],
                      "LatestAlbum": "",
                      "ReleaseDate": "",
                      "ReleaseInFuture": "False",
                      "AlbumID": "",
                      }

            if not row['HaveTracks']:
                row['HaveTracks'] = 0
            if artist['ReleaseDate'] and artist['LatestAlbum']:
                row['ReleaseDate'] = artist['ReleaseDate']
                row['LatestAlbum'] = artist['LatestAlbum']
                row['AlbumID'] = artist['AlbumID']
                if artist['ReleaseDate'] > today():
                    row['ReleaseInFuture'] = "True"
            elif artist['LatestAlbum']:
                row['ReleaseDate'] = ''
                row['LatestAlbum'] = artist['LatestAlbum']
                row['AlbumID'] = artist['AlbumID']

            rows.append(row)

        dict = {'iTotalDisplayRecords': len(filtered),
                'iTotalRecords': totalcount,
                'aaData': rows,
                }
        s = json.dumps(dict)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s

    @cherrypy.expose
    def getAlbumsByArtist_json(self, artist=None):
        myDB = db.DBConnection()
        album_json = {}
        counter = 0
        album_list = myDB.select("SELECT AlbumTitle from albums WHERE ArtistName=?", [artist])
        for album in album_list:
            album_json[counter] = album['AlbumTitle']
            counter += 1
        json_albums = json.dumps(album_json)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json_albums

    def getArtistjson(self, ArtistID, **kwargs):
        myDB = db.DBConnection()
        artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
        artist_json = json.dumps({
                                    'ArtistName': artist['ArtistName'],
                                    'Status': artist['Status']
                                 })
        return artist_json

    @cherrypy.expose
    def getAlbumjson(self, AlbumID, **kwargs):
        myDB = db.DBConnection()
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
        album_json = json.dumps({
                                   'AlbumTitle': album['AlbumTitle'],
                                   'ArtistName': album['ArtistName'],
                                   'Status': album['Status']
        })
        return album_json

    @cherrypy.expose
    def clearhistory(self, type=None, date_added=None, title=None):
        myDB = db.DBConnection()
        if type:
            if type == 'all':
                logger.info(u"Clearing all history")
                myDB.action('DELETE from snatched WHERE Status NOT LIKE "Seed%"')
            else:
                logger.info(u"Clearing history where status is %s" % type)
                myDB.action('DELETE from snatched WHERE Status=?', [type])
        else:
            logger.info(u"Deleting '%s' from history" % title)
            myDB.action('DELETE from snatched WHERE Status NOT LIKE "Seed%" AND Title=? AND DateAdded=?', [title, date_added])
        raise cherrypy.HTTPRedirect("history")

    @cherrypy.expose
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info("New API generated")
        return apikey

    @cherrypy.expose
    def forceScan(self, keepmatched=None):
        myDB = db.DBConnection()
        #########################################
        #NEED TO MOVE THIS INTO A SEPARATE FUNCTION BEFORE RELEASE
        myDB.select('DELETE from Have')
        logger.info('Removed all entries in local library database')
        myDB.select('UPDATE alltracks SET Location=NULL, BitRate=NULL, Format=NULL')
        myDB.select('UPDATE tracks SET Location=NULL, BitRate=NULL, Format=NULL')
        logger.info('All tracks in library unmatched')
        myDB.action('UPDATE artists SET HaveTracks=NULL')
        logger.info('Reset track counts for all artists')
        myDB.action('UPDATE albums SET Status="Skipped" WHERE Status="Skipped" OR Status="Downloaded"')
        logger.info('Marking all unwanted albums as Skipped')
        try:
            threading.Thread(target=librarysync.libraryScan).start()
        except Exception as e:
            logger.error('Unable to complete the scan: %s' % e)
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def config(self):
        interface_dir = os.path.join(headphones.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if os.path.isdir(os.path.join(interface_dir, name))]

        config = {
            "http_host": headphones.CONFIG.HTTP_HOST,
            "http_username": headphones.CONFIG.HTTP_USERNAME,
            "http_port": headphones.CONFIG.HTTP_PORT,
            "http_password": headphones.CONFIG.HTTP_PASSWORD,
            "launch_browser": checked(headphones.CONFIG.LAUNCH_BROWSER),
            "enable_https": checked(headphones.CONFIG.ENABLE_HTTPS),
            "https_cert": headphones.CONFIG.HTTPS_CERT,
            "https_key": headphones.CONFIG.HTTPS_KEY,
            "api_enabled": checked(headphones.CONFIG.API_ENABLED),
            "api_key": headphones.CONFIG.API_KEY,
            "download_scan_interval": headphones.CONFIG.DOWNLOAD_SCAN_INTERVAL,
            "update_db_interval": headphones.CONFIG.UPDATE_DB_INTERVAL,
            "mb_ignore_age": headphones.CONFIG.MB_IGNORE_AGE,
            "search_interval": headphones.CONFIG.SEARCH_INTERVAL,
            "libraryscan_interval": headphones.CONFIG.LIBRARYSCAN_INTERVAL,
            "sab_host": headphones.CONFIG.SAB_HOST,
            "sab_username": headphones.CONFIG.SAB_USERNAME,
            "sab_apikey": headphones.CONFIG.SAB_APIKEY,
            "sab_password": headphones.CONFIG.SAB_PASSWORD,
            "sab_category": headphones.CONFIG.SAB_CATEGORY,
            "nzbget_host": headphones.CONFIG.NZBGET_HOST,
            "nzbget_username": headphones.CONFIG.NZBGET_USERNAME,
            "nzbget_password": headphones.CONFIG.NZBGET_PASSWORD,
            "nzbget_category": headphones.CONFIG.NZBGET_CATEGORY,
            "nzbget_priority": headphones.CONFIG.NZBGET_PRIORITY,
            "transmission_host": headphones.CONFIG.TRANSMISSION_HOST,
            "transmission_username": headphones.CONFIG.TRANSMISSION_USERNAME,
            "transmission_password": headphones.CONFIG.TRANSMISSION_PASSWORD,
            "utorrent_host": headphones.CONFIG.UTORRENT_HOST,
            "utorrent_username": headphones.CONFIG.UTORRENT_USERNAME,
            "utorrent_password": headphones.CONFIG.UTORRENT_PASSWORD,
            "utorrent_label": headphones.CONFIG.UTORRENT_LABEL,
            "nzb_downloader_sabnzbd": radio(headphones.CONFIG.NZB_DOWNLOADER, 0),
            "nzb_downloader_nzbget": radio(headphones.CONFIG.NZB_DOWNLOADER, 1),
            "nzb_downloader_blackhole": radio(headphones.CONFIG.NZB_DOWNLOADER, 2),
            "torrent_downloader_blackhole": radio(headphones.CONFIG.TORRENT_DOWNLOADER, 0),
            "torrent_downloader_transmission": radio(headphones.CONFIG.TORRENT_DOWNLOADER, 1),
            "torrent_downloader_utorrent": radio(headphones.CONFIG.TORRENT_DOWNLOADER, 2),
            "download_dir": headphones.CONFIG.DOWNLOAD_DIR,
            "use_blackhole": checked(headphones.CONFIG.BLACKHOLE),
            "blackhole_dir": headphones.CONFIG.BLACKHOLE_DIR,
            "usenet_retention": headphones.CONFIG.USENET_RETENTION,
            "headphones_indexer": checked(headphones.CONFIG.HEADPHONES_INDEXER),
            "use_newznab": checked(headphones.CONFIG.NEWZNAB),
            "newznab_host": headphones.CONFIG.NEWZNAB_HOST,
            "newznab_apikey": headphones.CONFIG.NEWZNAB_APIKEY,
            "newznab_enabled": checked(headphones.CONFIG.NEWZNAB_ENABLED),
            "extra_newznabs": headphones.CONFIG.get_extra_newznabs(),
            "use_nzbsorg": checked(headphones.CONFIG.NZBSORG),
            "nzbsorg_uid": headphones.CONFIG.NZBSORG_UID,
            "nzbsorg_hash": headphones.CONFIG.NZBSORG_HASH,
            "use_omgwtfnzbs": checked(headphones.CONFIG.OMGWTFNZBS),
            "omgwtfnzbs_uid": headphones.CONFIG.OMGWTFNZBS_UID,
            "omgwtfnzbs_apikey": headphones.CONFIG.OMGWTFNZBS_APIKEY,
            "preferred_words": headphones.CONFIG.PREFERRED_WORDS,
            "ignored_words": headphones.CONFIG.IGNORED_WORDS,
            "required_words": headphones.CONFIG.REQUIRED_WORDS,
            "torrentblackhole_dir": headphones.CONFIG.TORRENTBLACKHOLE_DIR,
            "download_torrent_dir": headphones.CONFIG.DOWNLOAD_TORRENT_DIR,
            "numberofseeders": headphones.CONFIG.NUMBEROFSEEDERS,
            "use_kat": checked(headphones.CONFIG.KAT),
            "kat_proxy_url": headphones.CONFIG.KAT_PROXY_URL,
            "kat_ratio": headphones.CONFIG.KAT_RATIO,
            "use_piratebay": checked(headphones.CONFIG.PIRATEBAY),
            "piratebay_proxy_url": headphones.CONFIG.PIRATEBAY_PROXY_URL,
            "piratebay_ratio": headphones.CONFIG.PIRATEBAY_RATIO,
            "use_mininova": checked(headphones.CONFIG.MININOVA),
            "mininova_ratio": headphones.CONFIG.MININOVA_RATIO,
            "use_waffles": checked(headphones.CONFIG.WAFFLES),
            "waffles_uid": headphones.CONFIG.WAFFLES_UID,
            "waffles_passkey": headphones.CONFIG.WAFFLES_PASSKEY,
            "waffles_ratio": headphones.CONFIG.WAFFLES_RATIO,
            "use_rutracker": checked(headphones.CONFIG.RUTRACKER),
            "rutracker_user": headphones.CONFIG.RUTRACKER_USER,
            "rutracker_password": headphones.CONFIG.RUTRACKER_PASSWORD,
            "rutracker_ratio": headphones.CONFIG.RUTRACKER_RATIO,
            "use_whatcd": checked(headphones.CONFIG.WHATCD),
            "whatcd_username": headphones.CONFIG.WHATCD_USERNAME,
            "whatcd_password": headphones.CONFIG.WHATCD_PASSWORD,
            "whatcd_ratio": headphones.CONFIG.WHATCD_RATIO,
            "pref_qual_0": radio(headphones.CONFIG.PREFERRED_QUALITY, 0),
            "pref_qual_1": radio(headphones.CONFIG.PREFERRED_QUALITY, 1),
            "pref_qual_2": radio(headphones.CONFIG.PREFERRED_QUALITY, 2),
            "pref_qual_3": radio(headphones.CONFIG.PREFERRED_QUALITY, 3),
            "preferred_bitrate": headphones.CONFIG.PREFERRED_BITRATE,
            "preferred_bitrate_high": headphones.CONFIG.PREFERRED_BITRATE_HIGH_BUFFER,
            "preferred_bitrate_low": headphones.CONFIG.PREFERRED_BITRATE_LOW_BUFFER,
            "preferred_bitrate_allow_lossless": checked(headphones.CONFIG.PREFERRED_BITRATE_ALLOW_LOSSLESS),
            "detect_bitrate": checked(headphones.CONFIG.DETECT_BITRATE),
            "lossless_bitrate_from": headphones.CONFIG.LOSSLESS_BITRATE_FROM,
            "lossless_bitrate_to": headphones.CONFIG.LOSSLESS_BITRATE_TO,
            "freeze_db": checked(headphones.CONFIG.FREEZE_DB),
            "cue_split": checked(headphones.CONFIG.CUE_SPLIT),
            "cue_split_flac_path": headphones.CONFIG.CUE_SPLIT_FLAC_PATH,
            "cue_split_shntool_path": headphones.CONFIG.CUE_SPLIT_SHNTOOL_PATH,
            "move_files": checked(headphones.CONFIG.MOVE_FILES),
            "rename_files": checked(headphones.CONFIG.RENAME_FILES),
            "correct_metadata": checked(headphones.CONFIG.CORRECT_METADATA),
            "cleanup_files": checked(headphones.CONFIG.CLEANUP_FILES),
            "keep_nfo": checked(headphones.CONFIG.KEEP_NFO),
            "add_album_art": checked(headphones.CONFIG.ADD_ALBUM_ART),
            "album_art_format": headphones.CONFIG.ALBUM_ART_FORMAT,
            "embed_album_art": checked(headphones.CONFIG.EMBED_ALBUM_ART),
            "embed_lyrics": checked(headphones.CONFIG.EMBED_LYRICS),
            "replace_existing_folders": checked(headphones.CONFIG.REPLACE_EXISTING_FOLDERS),
            "destination_dir": headphones.CONFIG.DESTINATION_DIR,
            "lossless_destination_dir": headphones.CONFIG.LOSSLESS_DESTINATION_DIR,
            "folder_format": headphones.CONFIG.FOLDER_FORMAT,
            "file_format": headphones.CONFIG.FILE_FORMAT,
            "file_underscores": checked(headphones.CONFIG.FILE_UNDERSCORES),
            "include_extras": checked(headphones.CONFIG.INCLUDE_EXTRAS),
            "autowant_upcoming": checked(headphones.CONFIG.AUTOWANT_UPCOMING),
            "autowant_all": checked(headphones.CONFIG.AUTOWANT_ALL),
            "autowant_manually_added": checked(headphones.CONFIG.AUTOWANT_MANUALLY_ADDED),
            "keep_torrent_files": checked(headphones.CONFIG.KEEP_TORRENT_FILES),
            "prefer_torrents_0": radio(headphones.CONFIG.PREFER_TORRENTS, 0),
            "prefer_torrents_1": radio(headphones.CONFIG.PREFER_TORRENTS, 1),
            "prefer_torrents_2": radio(headphones.CONFIG.PREFER_TORRENTS, 2),
            "magnet_links_0": radio(headphones.CONFIG.MAGNET_LINKS, 0),
            "magnet_links_1": radio(headphones.CONFIG.MAGNET_LINKS, 1),
            "magnet_links_2": radio(headphones.CONFIG.MAGNET_LINKS, 2),
            "log_dir": headphones.CONFIG.LOG_DIR,
            "cache_dir": headphones.CONFIG.CACHE_DIR,
            "interface_list": interface_list,
            "music_encoder": checked(headphones.CONFIG.MUSIC_ENCODER),
            "encoder": headphones.CONFIG.ENCODER,
            "xldprofile": headphones.CONFIG.XLDPROFILE,
            "bitrate": int(headphones.CONFIG.BITRATE),
            "encoder_path": headphones.CONFIG.ENCODER_PATH,
            "advancedencoder": headphones.CONFIG.ADVANCEDENCODER,
            "encoderoutputformat": headphones.CONFIG.ENCODEROUTPUTFORMAT,
            "samplingfrequency": headphones.CONFIG.SAMPLINGFREQUENCY,
            "encodervbrcbr": headphones.CONFIG.ENCODERVBRCBR,
            "encoderquality": headphones.CONFIG.ENCODERQUALITY,
            "encoderlossless": checked(headphones.CONFIG.ENCODERLOSSLESS),
            "encoder_multicore": checked(headphones.CONFIG.ENCODER_MULTICORE),
            "encoder_multicore_count": int(headphones.CONFIG.ENCODER_MULTICORE_COUNT),
            "delete_lossless_files": checked(headphones.CONFIG.DELETE_LOSSLESS_FILES),
            "growl_enabled": checked(headphones.CONFIG.GROWL_ENABLED),
            "growl_onsnatch": checked(headphones.CONFIG.GROWL_ONSNATCH),
            "growl_host": headphones.CONFIG.GROWL_HOST,
            "growl_password": headphones.CONFIG.GROWL_PASSWORD,
            "prowl_enabled": checked(headphones.CONFIG.PROWL_ENABLED),
            "prowl_onsnatch": checked(headphones.CONFIG.PROWL_ONSNATCH),
            "prowl_keys": headphones.CONFIG.PROWL_KEYS,
            "prowl_priority": headphones.CONFIG.PROWL_PRIORITY,
            "xbmc_enabled": checked(headphones.CONFIG.XBMC_ENABLED),
            "xbmc_host": headphones.CONFIG.XBMC_HOST,
            "xbmc_username": headphones.CONFIG.XBMC_USERNAME,
            "xbmc_password": headphones.CONFIG.XBMC_PASSWORD,
            "xbmc_update": checked(headphones.CONFIG.XBMC_UPDATE),
            "xbmc_notify": checked(headphones.CONFIG.XBMC_NOTIFY),
            "lms_enabled": checked(headphones.CONFIG.LMS_ENABLED),
            "lms_host": headphones.CONFIG.LMS_HOST,
            "plex_enabled": checked(headphones.CONFIG.PLEX_ENABLED),
            "plex_server_host": headphones.CONFIG.PLEX_SERVER_HOST,
            "plex_client_host": headphones.CONFIG.PLEX_CLIENT_HOST,
            "plex_username": headphones.CONFIG.PLEX_USERNAME,
            "plex_password": headphones.CONFIG.PLEX_PASSWORD,
            "plex_update": checked(headphones.CONFIG.PLEX_UPDATE),
            "plex_notify": checked(headphones.CONFIG.PLEX_NOTIFY),
            "nma_enabled": checked(headphones.CONFIG.NMA_ENABLED),
            "nma_apikey": headphones.CONFIG.NMA_APIKEY,
            "nma_priority": int(headphones.CONFIG.NMA_PRIORITY),
            "nma_onsnatch": checked(headphones.CONFIG.NMA_ONSNATCH),
            "pushalot_enabled": checked(headphones.CONFIG.PUSHALOT_ENABLED),
            "pushalot_apikey": headphones.CONFIG.PUSHALOT_APIKEY,
            "pushalot_onsnatch": checked(headphones.CONFIG.PUSHALOT_ONSNATCH),
            "synoindex_enabled": checked(headphones.CONFIG.SYNOINDEX_ENABLED),
            "pushover_enabled": checked(headphones.CONFIG.PUSHOVER_ENABLED),
            "pushover_onsnatch": checked(headphones.CONFIG.PUSHOVER_ONSNATCH),
            "pushover_keys": headphones.CONFIG.PUSHOVER_KEYS,
            "pushover_apitoken": headphones.CONFIG.PUSHOVER_APITOKEN,
            "pushover_priority": headphones.CONFIG.PUSHOVER_PRIORITY,
            "pushbullet_enabled": checked(headphones.CONFIG.PUSHBULLET_ENABLED),
            "pushbullet_onsnatch": checked(headphones.CONFIG.PUSHBULLET_ONSNATCH),
            "pushbullet_apikey": headphones.CONFIG.PUSHBULLET_APIKEY,
            "pushbullet_deviceid": headphones.CONFIG.PUSHBULLET_DEVICEID,
            "subsonic_enabled": checked(headphones.CONFIG.SUBSONIC_ENABLED),
            "subsonic_host": headphones.CONFIG.SUBSONIC_HOST,
            "subsonic_username": headphones.CONFIG.SUBSONIC_USERNAME,
            "subsonic_password": headphones.CONFIG.SUBSONIC_PASSWORD,
            "twitter_enabled": checked(headphones.CONFIG.TWITTER_ENABLED),
            "twitter_onsnatch": checked(headphones.CONFIG.TWITTER_ONSNATCH),
            "osx_notify_enabled": checked(headphones.CONFIG.OSX_NOTIFY_ENABLED),
            "osx_notify_onsnatch": checked(headphones.CONFIG.OSX_NOTIFY_ONSNATCH),
            "osx_notify_app": headphones.CONFIG.OSX_NOTIFY_APP,
            "boxcar_enabled": checked(headphones.CONFIG.BOXCAR_ENABLED),
            "boxcar_onsnatch": checked(headphones.CONFIG.BOXCAR_ONSNATCH),
            "boxcar_token": headphones.CONFIG.BOXCAR_TOKEN,
            "mirrorlist": headphones.MIRRORLIST,
            "mirror": headphones.CONFIG.MIRROR,
            "customhost": headphones.CONFIG.CUSTOMHOST,
            "customport": headphones.CONFIG.CUSTOMPORT,
            "customsleep": headphones.CONFIG.CUSTOMSLEEP,
            "hpuser": headphones.CONFIG.HPUSER,
            "hppass": headphones.CONFIG.HPPASS,
            "songkick_enabled": checked(headphones.CONFIG.SONGKICK_ENABLED),
            "songkick_apikey": headphones.CONFIG.SONGKICK_APIKEY,
            "songkick_location": headphones.CONFIG.SONGKICK_LOCATION,
            "songkick_filter_enabled": checked(headphones.CONFIG.SONGKICK_FILTER_ENABLED),
            "cache_sizemb": headphones.CONFIG.CACHE_SIZEMB,
            "file_permissions": headphones.CONFIG.FILE_PERMISSIONS,
            "folder_permissions": headphones.CONFIG.FOLDER_PERMISSIONS,
            "mpc_enabled": checked(headphones.CONFIG.MPC_ENABLED)
        }

        # Need to convert EXTRAS to a dictionary we can pass to the config:
        # it'll come in as a string like 2,5,6,8
        extra_munges = {
            "dj-mix": "dj_mix",
            "mixtape/street": "mixtape_street"
        }

        extras_list = [extra_munges.get(x, x) for x in headphones.POSSIBLE_EXTRAS]
        if headphones.CONFIG.EXTRAS:
            extras = map(int, headphones.CONFIG.EXTRAS.split(','))
        else:
            extras = []

        extras_dict = OrderedDict()

        i = 1
        for extra in extras_list:
            if i in extras:
                extras_dict[extra] = "checked"
            else:
                extras_dict[extra] = ""
            i += 1

        config["extras"] = extras_dict

        return serve_template(templatename="config.html", title="Settings", config=config)

    @cherrypy.expose
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "api_enabled", "use_blackhole", "headphones_indexer", "use_newznab", "newznab_enabled",
            "use_nzbsorg", "use_omgwtfnzbs", "use_kat", "use_piratebay", "use_mininova", "use_waffles", "use_rutracker", "use_whatcd",
            "preferred_bitrate_allow_lossless", "detect_bitrate", "freeze_db", "cue_split", "move_files", "rename_files", "correct_metadata",
            "cleanup_files", "keep_nfo", "add_album_art", "embed_album_art", "embed_lyrics", "replace_existing_folders", "file_underscores",
            "include_extras", "autowant_upcoming", "autowant_all", "autowant_manually_added", "keep_torrent_files", "music_encoder",
            "encoderlossless", "encoder_multicore", "delete_lossless_files", "growl_enabled", "growl_onsnatch", "prowl_enabled",
            "prowl_onsnatch", "xbmc_enabled", "xbmc_update", "xbmc_notify", "lms_enabled", "plex_enabled", "plex_update", "plex_notify",
            "nma_enabled", "nma_onsnatch", "pushalot_enabled", "pushalot_onsnatch", "synoindex_enabled", "pushover_enabled",
            "pushover_onsnatch", "pushbullet_enabled", "pushbullet_onsnatch", "subsonic_enabled", "twitter_enabled", "twitter_onsnatch",
            "osx_notify_enabled", "osx_notify_onsnatch", "boxcar_enabled", "boxcar_onsnatch", "songkick_enabled", "songkick_filter_enabled",
            "mpc_enabled"
        ]
        for checked_config in checked_configs:
            if checked_config not in kwargs:
                # checked items should be zero or one. if they were not sent then the item was not checked
                kwargs[checked_config] = 0

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        extra_newznabs = []
        for kwarg in [x for x in kwargs if x.startswith('newznab_host')]:
            newznab_host_key = kwarg
            newznab_number = kwarg[12:]
            if len(newznab_number):
                newznab_api_key = 'newznab_api' + newznab_number
                newznab_enabled_key = 'newznab_enabled' + newznab_number
                newznab_host = kwargs.get(newznab_host_key, '')
                newznab_api = kwargs.get(newznab_api_key, '')
                newznab_enabled = int(kwargs.get(newznab_enabled_key, 0))
                for key in [newznab_host_key, newznab_api_key, newznab_enabled_key]:
                    if key in kwargs:
                        del kwargs[key]
                extra_newznabs.append((newznab_host, newznab_api, newznab_enabled))

        # Convert the extras to list then string. Coming in as 0 or 1 (append new extras to the end)
        temp_extras_list = []

        extra_munges = {
            "dj-mix": "dj_mix",
            "mixtape/street": "mixtape_street"
        }

        expected_extras = [extra_munges.get(x, x) for x in headphones.POSSIBLE_EXTRAS]
        extras_list = [kwargs.get(x, 0) for x in expected_extras]

        i = 1
        for extra in extras_list:
            if extra:
                temp_extras_list.append(i)
            i += 1

        for extra in expected_extras:
            temp = '%s_temp' % extra
            if temp in kwargs:
                del kwargs[temp]
            if extra in kwargs:
                del kwargs[extra]

        headphones.CONFIG.EXTRAS = ','.join(str(n) for n in temp_extras_list)
        headphones.CONFIG.clear_extra_newznabs()
        headphones.CONFIG.process_kwargs(kwargs)
        for extra_newznab in extra_newznabs:
            headphones.CONFIG.add_extra_newznab(extra_newznab)

        # Sanity checking
        if headphones.CONFIG.SEARCH_INTERVAL and headphones.CONFIG.SEARCH_INTERVAL < 360:
            logger.info("Search interval too low. Resetting to 6 hour minimum")
            headphones.CONFIG.SEARCH_INTERVAL = 360

        # Write the config
        headphones.CONFIG.write()

        # Reconfigure scheduler
        headphones.initialize_scheduler()

        # Reconfigure musicbrainz database connection with the new values
        mb.startmb()

        raise cherrypy.HTTPRedirect("config")

    @cherrypy.expose
    def do_state_change(self, signal, title, timer):
        headphones.SIGNAL = signal
        message = title + '...'
        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer)

    @cherrypy.expose
    def shutdown(self):
        return self.do_state_change('shutdown', 'Shutting Down', 15)

    @cherrypy.expose
    def restart(self):
        return self.do_state_change('restart', 'Restarting', 30)

    @cherrypy.expose
    def update(self):
        return self.do_state_change('update', 'Updating', 120)

    @cherrypy.expose
    def extras(self):
        myDB = db.DBConnection()
        cloudlist = myDB.select('SELECT * from lastfmcloud')
        return serve_template(templatename="extras.html", title="Extras", cloudlist=cloudlist)

    @cherrypy.expose
    def addReleaseById(self, rid, rgid=None):
        threading.Thread(target=importer.addReleaseById, args=[rid, rgid]).start()
        if rgid:
            raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % rgid)
        else:
            raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def updateCloud(self):
        lastfm.getSimilar()
        raise cherrypy.HTTPRedirect("extras")

    @cherrypy.expose
    def api(self, *args, **kwargs):
        from headphones.api import Api

        a = Api()
        a.checkParams(*args, **kwargs)

        return a.fetchData()

    @cherrypy.expose
    def getInfo(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        info_dict = cache.getInfo(ArtistID, AlbumID)

        return json.dumps(info_dict)

    @cherrypy.expose
    def getArtwork(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        return cache.getArtwork(ArtistID, AlbumID)

    @cherrypy.expose
    def getThumb(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        return cache.getThumb(ArtistID, AlbumID)

    # If you just want to get the last.fm image links for an album, make sure
    # to pass a releaseid and not a releasegroupid
    @cherrypy.expose
    def getImageLinks(self, ArtistID=None, AlbumID=None):
        from headphones import cache
        image_dict = cache.getImageLinks(ArtistID, AlbumID)

        # Return the Cover Art Archive urls if not found on last.fm
        if AlbumID and not image_dict:
            image_url = "http://coverartarchive.org/release/%s/front-500.jpg" % AlbumID
            thumb_url = "http://coverartarchive.org/release/%s/front-250.jpg" % AlbumID
            image_dict = {'artwork': image_url, 'thumbnail': thumb_url}
        elif AlbumID and (not image_dict['artwork'] or not image_dict['thumbnail']):
            if not image_dict['artwork']:
                image_dict['artwork'] = "http://coverartarchive.org/release/%s/front-500.jpg" % AlbumID
            if not image_dict['thumbnail']:
                image_dict['thumbnail'] = "http://coverartarchive.org/release/%s/front-250.jpg" % AlbumID

        return json.dumps(image_dict)

    @cherrypy.expose
    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        return tweet._get_authorization()

    @cherrypy.expose
    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet._get_credentials(key)
        logger.info(u"result: " + str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"

    @cherrypy.expose
    def testTwitter(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet.test_notify()
        if result:
            return "Tweet successful, check your twitter to make sure it worked"
        else:
            return "Error sending tweet"

    @cherrypy.expose
    def osxnotifyregister(self, app):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        from osxnotify import registerapp as osxnotify
        result, msg = osxnotify.registerapp(app)
        if result:
            osx_notify = notifiers.OSX_NOTIFY()
            osx_notify.notify('Registered', result, 'Success :-)')
            logger.info('Registered %s, to re-register a different app, delete this app first' % result)
        else:
            logger.warn(msg)
        return msg

class Artwork(object):
    @cherrypy.expose
    def index(self):
        return "Artwork"

    @cherrypy.expose
    def default(self, ArtistOrAlbum="", ID=None):
        from headphones import cache
        ArtistID = None
        AlbumID = None
        if ArtistOrAlbum == "artist":
            ArtistID = ID
        elif ArtistOrAlbum == "album":
            AlbumID = ID

        relpath = cache.getArtwork(ArtistID, AlbumID)

        if not relpath:
            relpath = "data/interfaces/default/images/no-cover-art.png"
            basedir = os.path.dirname(sys.argv[0])
            path = os.path.join(basedir, relpath)
            cherrypy.response.headers['Content-type'] = 'image/png'
            cherrypy.response.headers['Cache-Control'] = 'no-cache'
        else:
            relpath = relpath.replace('cache/', '', 1)
            path = os.path.join(headphones.CONFIG.CACHE_DIR, relpath)
            fileext = os.path.splitext(relpath)[1][1::]
            cherrypy.response.headers['Content-type'] = 'image/' + fileext
            cherrypy.response.headers['Cache-Control'] = 'max-age=31556926'

        with open(os.path.normpath(path), "rb") as fp:
            return fp.read()

    class Thumbs(object):
        @cherrypy.expose
        def index(self):
            return "Here be thumbs"

        @cherrypy.expose
        def default(self, ArtistOrAlbum="", ID=None):
            from headphones import cache
            ArtistID = None
            AlbumID = None
            if ArtistOrAlbum == "artist":
                ArtistID = ID
            elif ArtistOrAlbum == "album":
                AlbumID = ID

            relpath = cache.getThumb(ArtistID, AlbumID)

            if not relpath:
                relpath = "data/interfaces/default/images/no-cover-artist.png"
                basedir = os.path.dirname(sys.argv[0])
                path = os.path.join(basedir, relpath)
                cherrypy.response.headers['Content-type'] = 'image/png'
                cherrypy.response.headers['Cache-Control'] = 'no-cache'
            else:
                relpath = relpath.replace('cache/', '', 1)
                path = os.path.join(headphones.CONFIG.CACHE_DIR, relpath)
                fileext = os.path.splitext(relpath)[1][1::]
                cherrypy.response.headers['Content-type'] = 'image/' + fileext
                cherrypy.response.headers['Cache-Control'] = 'max-age=31556926'

            with open(os.path.normpath(path), "rb") as fp:
                return fp.read()

    thumbs = Thumbs()
WebInterface.artwork = Artwork()
