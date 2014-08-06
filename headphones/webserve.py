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

import os
import cherrypy

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import time
import threading
import string
import json
from operator import itemgetter

import headphones

from headphones import logger, searcher, db, importer, mb, lastfm, librarysync, helpers, notifiers
from headphones.helpers import checked, radio,today, cleanName

import lib.simplejson as simplejson

import sys



def serve_template(templatename, **kwargs):

    interface_dir = os.path.join(str(headphones.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), headphones.INTERFACE)

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()

class WebInterface(object):

    def index(self):
        raise cherrypy.HTTPRedirect("home")
    index.exposed=True

    def home(self):
        myDB = db.DBConnection()
        artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return serve_template(templatename="index.html", title="Home", artists=artists)
    home.exposed = True

    def artistPage(self, ArtistID):
        myDB = db.DBConnection()
        artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
        albums = myDB.select('SELECT * from albums WHERE ArtistID=? order by ReleaseDate DESC', [ArtistID])

        # Don't redirect to the artist page until it has the bare minimum info inserted
        # Redirect to the home page if we still can't get it after 5 seconds
        retry = 0

        while retry < 5:
            if not artist:
                time.sleep(1)
                artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
                retry += 1
            else:
                break

        if not artist:
            raise cherrypy.HTTPRedirect("home")

        # Serve the extras up as a dict to make things easier for new templates
        extras_list = ["single", "ep", "compilation", "soundtrack", "live", "remix", "djmix", "mixtape_street", "spokenword", "audiobook", "broadcast", "interview", "other"]
        extras_dict = {}

        if not artist['Extras']:
            artist_extras = ""
        else:
            artist_extras = artist['Extras']

        i = 1
        for extra in extras_list:
            if str(i) in artist_extras:
                extras_dict[extra] = "checked"
            else:
                extras_dict[extra] = ""
            i+=1

        return serve_template(templatename="artist.html", title=artist['ArtistName'], artist=artist, albums=albums, extras=extras_dict)
    artistPage.exposed = True


    def albumPage(self, AlbumID):
        myDB = db.DBConnection()
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
        tracks = myDB.select('SELECT * from tracks WHERE AlbumID=? ORDER BY CAST(TrackNumber AS INTEGER)', [AlbumID])
        description = myDB.action('SELECT * from descriptions WHERE ReleaseGroupID=?', [AlbumID]).fetchone()

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

        if not album['ArtistName']:
            title =  ' - '
        else:
            title = album['ArtistName'] + ' - '
        if not album['AlbumTitle']:
            title = title + ""
        else:
            title = title + album['AlbumTitle']
        return serve_template(templatename="album.html", title=title, album=album, tracks=tracks, description=description)
    albumPage.exposed = True


    def search(self, name, type):
        if len(name) == 0:
            raise cherrypy.HTTPRedirect("home")
        if type == 'artist':
            searchresults = mb.findArtist(name, limit=100)
        else:
            searchresults = mb.findRelease(name, limit=100)
        return serve_template(templatename="searchresults.html", title='Search Results for: "' + name + '"', searchresults=searchresults, type=type)
    search.exposed = True

    def addArtist(self, artistid):
        threading.Thread(target=importer.addArtisttoDB, args=[artistid]).start()
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % artistid)
    addArtist.exposed = True

    def getExtras(self, ArtistID, newstyle=False, **kwargs):
        # if calling this function without the newstyle, they're using the old format
        # which doesn't separate extras, so we'll grab all of them
        #
        # If they are, we need to convert kwargs to string format
        if not newstyle:
            extras = "1,2,3,4,5,6,7,8,9,10,11,12,13"
        else:
            temp_extras_list = []
            # TODO: Put these extras as a global variable
            i = 1
            for extra in ["single", "ep", "compilation", "soundtrack", "live", "remix", "djmix", "mixtape_street", "spokenword", "audiobook", "broadcast", "interview", "other"]:
                if extra in kwargs:
                    temp_extras_list.append(i)
                i += 1
            extras = ','.join(str(n) for n in temp_extras_list)

        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'IncludeExtras': 1,
                        'Extras':        extras}
        myDB.upsert("artists", newValueDict, controlValueDict)
        threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, True, False]).start()
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    getExtras.exposed = True

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
        importer.finalize_update(ArtistID, ArtistName)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    removeExtras.exposed = True

    def pauseArtist(self, ArtistID):
        logger.info(u"Pausing artist: " + ArtistID)
        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'Status': 'Paused'}
        myDB.upsert("artists", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    pauseArtist.exposed = True

    def resumeArtist(self, ArtistID):
        logger.info(u"Resuming artist: " + ArtistID)
        myDB = db.DBConnection()
        controlValueDict = {'ArtistID': ArtistID}
        newValueDict = {'Status': 'Active'}
        myDB.upsert("artists", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    resumeArtist.exposed = True

    def deleteArtist(self, ArtistID):
        logger.info(u"Deleting all traces of artist: " + ArtistID)
        myDB = db.DBConnection()
        namecheck = myDB.select('SELECT ArtistName from artists where ArtistID=?', [ArtistID])
        for name in namecheck:
            artistname=name['ArtistName']
        myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])

        rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM albums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
        for rgid in rgids:
            myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

        myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
        myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

        rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM allalbums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
        for rgid in rgids:
            myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

        myDB.action('DELETE from allalbums WHERE ArtistID=?', [ArtistID])
        myDB.action('DELETE from alltracks WHERE ArtistID=?', [ArtistID])
        myDB.action('UPDATE have SET Matched=NULL WHERE ArtistName=?', [artistname])
        myDB.action('INSERT OR REPLACE into blacklist VALUES (?)', [ArtistID])
        raise cherrypy.HTTPRedirect("home")
    deleteArtist.exposed = True

    def deleteEmptyArtists(self):
        logger.info(u"Deleting all empty artists")
        myDB = db.DBConnection()
        emptyArtistIDs = [row['ArtistID'] for row in myDB.select("SELECT ArtistID FROM artists WHERE LatestAlbum IS NULL")]
        for ArtistID in emptyArtistIDs:
            logger.info(u"Deleting all traces of artist: " + ArtistID)
            myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])

            rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM albums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
            for rgid in rgids:
                myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

            myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
            myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

            rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM allalbums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
            for rgid in rgids:
                myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

            myDB.action('DELETE from allalbums WHERE ArtistID=?', [ArtistID])
            myDB.action('DELETE from alltracks WHERE ArtistID=?', [ArtistID])
            myDB.action('INSERT OR REPLACE into blacklist VALUES (?)', [ArtistID])
    deleteEmptyArtists.exposed = True

    def refreshArtist(self, ArtistID):
        threading.Thread(target=importer.addArtisttoDB, args=[ArtistID, False, True]).start()
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    refreshArtist.exposed=True

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
    markAlbums.exposed = True

    def addArtists(self, action=None, **args):
        if action == "add":
            threading.Thread(target=importer.artistlist_to_mbids, args=[args, True]).start()
        if action == "ignore":
            myDB = db.DBConnection()
            for artist in args:
                myDB.action('DELETE FROM newartists WHERE ArtistName=?', [artist])
                myDB.action('UPDATE have SET Matched="Ignored" WHERE ArtistName=?', [artist])
                logger.info("Artist %s removed from new artist list and set to ignored" % artist)
        raise cherrypy.HTTPRedirect("home")
    addArtists.exposed = True

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
            raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
        else:
            raise cherrypy.HTTPRedirect(redirect)
    queueAlbum.exposed = True

    def choose_specific_download(self, AlbumID):
        results = searcher.searchforalbum(AlbumID, choose_specific_download=True)
        
        results_as_dicts = []
        
        for result in results:

            result_dict = {
                'title':result[0],
                'size':result[1],
                'url':result[2],
                'provider':result[3],
                'kind':result[4]
            }
            results_as_dicts.append(result_dict)

        s = simplejson.dumps(results_as_dicts)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s
        
    choose_specific_download.exposed = True

    def download_specific_release(self, AlbumID, title, size, url, provider, kind, **kwargs):

        # Handle situations where the torrent url contains arguments that are parsed
        if kwargs:
            import urllib, urllib2
            url = urllib2.quote(url, safe=":?/=&") + '&' + urllib.urlencode(kwargs)

        try:
            result = [(title,int(size),url,provider,kind)]
        except ValueError:
            result = [(title,float(size),url,provider,kind)]

        logger.info(u"Making sure we can download the chosen result")
        (data, bestqual) = searcher.preprocess(result)

        if data and bestqual:
          myDB = db.DBConnection()
          album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
          searcher.send_to_downloader(data, bestqual, album)

    download_specific_release.exposed = True

    def unqueueAlbum(self, AlbumID, ArtistID):
        logger.info(u"Marking album: " + AlbumID + "as skipped...")
        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': AlbumID}
        newValueDict = {'Status': 'Skipped'}
        myDB.upsert("albums", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
    unqueueAlbum.exposed = True

    def deleteAlbum(self, AlbumID, ArtistID=None):
        logger.info(u"Deleting all traces of album: " + AlbumID)
        myDB = db.DBConnection()
        myDB.action('DELETE from albums WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from tracks WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from allalbums WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from alltracks WHERE AlbumID=?', [AlbumID])
        myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [AlbumID])
        if ArtistID:
            raise cherrypy.HTTPRedirect("artistPage?ArtistID=%s" % ArtistID)
        else:
            raise cherrypy.HTTPRedirect("home")
    deleteAlbum.exposed = True

    def switchAlbum(self, AlbumID, ReleaseID):
        '''
        Take the values from allalbums/alltracks (based on the ReleaseID) and swap it into the album & track tables
        '''
        from headphones import albumswitcher
        albumswitcher.switch(AlbumID, ReleaseID)
        raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % AlbumID)
    switchAlbum.exposed = True

    def editSearchTerm(self, AlbumID, SearchTerm):
        logger.info(u"Updating search term for albumid: " + AlbumID)
        myDB = db.DBConnection()
        controlValueDict = {'AlbumID': AlbumID}
        newValueDict = {'SearchTerm': SearchTerm}
        myDB.upsert("albums", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % AlbumID)
    editSearchTerm.exposed = True

    def upcoming(self):
        myDB = db.DBConnection()
        upcoming = myDB.select("SELECT * from albums WHERE ReleaseDate > date('now') order by ReleaseDate ASC")
        wanted = myDB.select("SELECT * from albums WHERE Status='Wanted'")
        return serve_template(templatename="upcoming.html", title="Upcoming", upcoming=upcoming, wanted=wanted)
    upcoming.exposed = True

    def manage(self):
        myDB = db.DBConnection()
        emptyArtists = myDB.select("SELECT * FROM artists WHERE LatestAlbum IS NULL")
        return serve_template(templatename="manage.html", title="Manage", emptyArtists=emptyArtists)
    manage.exposed = True

    def manageArtists(self):
        myDB = db.DBConnection()
        artists = myDB.select('SELECT * from artists order by ArtistSortName COLLATE NOCASE')
        return serve_template(templatename="manageartists.html", title="Manage Artists", artists=artists)
    manageArtists.exposed = True

    def manageAlbums(self, Status=None):
        myDB = db.DBConnection()
        if Status == "Upcoming":
            albums = myDB.select("SELECT * from albums WHERE ReleaseDate > date('now')")
        elif Status:
            albums = myDB.select('SELECT * from albums WHERE Status=?', [Status])
        else:
            albums = myDB.select('SELECT * from albums')
        return serve_template(templatename="managealbums.html", title="Manage Albums", albums=albums)
    manageAlbums.exposed = True

    def manageNew(self):
        myDB = db.DBConnection()
        newartists = myDB.select('SELECT * from newartists')
        return serve_template(templatename="managenew.html", title="Manage New Artists", newartists=newartists)
    manageNew.exposed = True

    def manageUnmatched(self):
        myDB = db.DBConnection()
        have_album_dictionary = []
        headphones_album_dictionary = []
        unmatched_albums = []
        have_albums = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName from have WHERE Matched = "Failed" GROUP BY AlbumTitle ORDER BY ArtistName')
        for albums in have_albums:
            #Have to skip over manually matched tracks
            if albums['ArtistName'] and albums['AlbumTitle'] and albums['TrackTitle']:
                original_clean = helpers.cleanName(albums['ArtistName']+" "+albums['AlbumTitle']+" "+albums['TrackTitle'])
            # else:
            #     original_clean = None
                if original_clean == albums['CleanName']:
                    have_dict = { 'ArtistName' : albums['ArtistName'], 'AlbumTitle' : albums['AlbumTitle'] }
                    have_album_dictionary.append(have_dict)
        headphones_albums = myDB.select('SELECT ArtistName, AlbumTitle from albums ORDER BY ArtistName')
        for albums in headphones_albums:
            headphones_dict = { 'ArtistName' : albums['ArtistName'], 'AlbumTitle' : albums['AlbumTitle'] }
            headphones_album_dictionary.append(headphones_dict)
        #unmatchedalbums = [f for f in have_album_dictionary if f not in [x for x in headphones_album_dictionary]]

        check = set([(cleanName(d['ArtistName']).lower(), cleanName(d['AlbumTitle']).lower()) for d in headphones_album_dictionary])
        unmatchedalbums = [d for d in have_album_dictionary if (cleanName(d['ArtistName']).lower(), cleanName(d['AlbumTitle']).lower()) not in check]


        return serve_template(templatename="manageunmatched.html", title="Manage Unmatched Items", unmatchedalbums=unmatchedalbums)
    manageUnmatched.exposed = True

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
                        newValueDict = {"Location" : entry['Location'],
                                        "BitRate" : entry['BitRate'],
                                        "Format" : entry['Format']
                                        }
                        #Attempt to match tracks with new CleanName
                        match_alltracks = myDB.action('SELECT CleanName from alltracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_alltracks:
                            myDB.upsert("alltracks", newValueDict, controlValueDict)
                        match_tracks = myDB.action('SELECT CleanName, AlbumID from tracks WHERE CleanName=?', [new_clean_filename]).fetchone()
                        if match_tracks:
                            myDB.upsert("tracks", newValueDict, controlValueDict)
                            myDB.action('UPDATE have SET Matched="Manual" WHERE CleanName=?', [new_clean_filename])
                            update_count+=1
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
            existing_clean_string = existing_artist_clean+" "+existing_album_clean
            new_clean_string = new_artist_clean+" "+new_album_clean
            if existing_clean_string != new_clean_string:
                have_tracks = myDB.action('SELECT Matched, CleanName, Location, BitRate, Format FROM have WHERE ArtistName=? AND AlbumTitle=?', (existing_artist, existing_album))
                update_count = 0
                for entry in have_tracks:
                    old_clean_filename = entry['CleanName']
                    if old_clean_filename.startswith(existing_clean_string):
                        new_clean_filename = old_clean_filename.replace(existing_clean_string, new_clean_string, 1)
                        myDB.action('UPDATE have SET CleanName=? WHERE ArtistName=? AND AlbumTitle=? AND CleanName=?', [new_clean_filename, existing_artist, existing_album, old_clean_filename])
                        controlValueDict = {"CleanName": new_clean_filename}
                        newValueDict = {"Location" : entry['Location'],
                                        "BitRate" : entry['BitRate'],
                                        "Format" : entry['Format']
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
                            update_count+=1
                    #This was throwing errors and I don't know why, but it seems to be working fine.
                    #else:
                        #logger.info("There was an error modifying Artist %s / Album %s with clean name %s" % (existing_artist, existing_album, existing_clean_string))
                logger.info("Manual matching yielded %s new matches for Artist: %s / Album: %s" % (update_count, new_artist, new_album))
                if update_count > 0:
                    librarysync.update_album_status(album_id)
            else:
                logger.info("Artist %s / Album %s already named appropriately; nothing to modify" % (existing_artist, existing_album))

    markUnmatched.exposed = True

    def manageManual(self):
        myDB = db.DBConnection()
        manual_albums = []
        manualalbums = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName, Matched from have')
        for albums in manualalbums:
            if albums['ArtistName'] and albums['AlbumTitle'] and albums['TrackTitle']:
                original_clean = helpers.cleanName(albums['ArtistName']+" "+albums['AlbumTitle']+" "+albums['TrackTitle'])
                if albums['Matched'] == "Ignored" or albums['Matched'] == "Manual" or albums['CleanName'] != original_clean:
                    if albums['Matched'] == "Ignored":
                        album_status = "Ignored"
                    elif albums['Matched'] == "Manual" or albums['CleanName'] != original_clean:
                        album_status = "Matched"
                    manual_dict = { 'ArtistName' : albums['ArtistName'], 'AlbumTitle' : albums['AlbumTitle'], 'AlbumStatus' : album_status }
                    if manual_dict not in manual_albums:
                        manual_albums.append(manual_dict)
        manual_albums_sorted = sorted(manual_albums, key=itemgetter('ArtistName', 'AlbumTitle'))

        return serve_template(templatename="managemanual.html", title="Manage Manual Items", manualalbums=manual_albums_sorted)
    manageManual.exposed = True

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
                original_clean = helpers.cleanName(tracks['ArtistName']+" "+tracks['AlbumTitle']+" "+tracks['TrackTitle']).lower()
                album = tracks['AlbumTitle']
                track_title = tracks['TrackTitle']
                if tracks['CleanName'] != original_clean:
                    myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE have SET CleanName=?, Matched="Failed" WHERE ArtistName=? AND AlbumTitle=? AND TrackTitle=?', (original_clean, artist, album, track_title))
                    update_count+=1
            if update_count > 0:
                librarysync.update_album_status()
            logger.info("Artist: %s successfully restored to unmatched list" % artist)

        elif action == "unmatchAlbum":
            artist = existing_artist
            album = existing_album
            update_clean = myDB.select('SELECT ArtistName, AlbumTitle, TrackTitle, CleanName, Matched from have WHERE ArtistName=? AND AlbumTitle=?', (artist, album))
            update_count = 0
            for tracks in update_clean:
                original_clean = helpers.cleanName(tracks['ArtistName']+" "+tracks['AlbumTitle']+" "+tracks['TrackTitle']).lower()
                track_title = tracks['TrackTitle']
                if tracks['CleanName'] != original_clean:
                    album_id_check = myDB.action('SELECT AlbumID from tracks WHERE CleanName=?', [tracks['CleanName']]).fetchone()
                    if album_id_check:
                        album_id = album_id_check[0]
                    myDB.action('UPDATE tracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE alltracks SET Location=?, BitRate=?, Format=? WHERE CleanName=?', [None, None, None, tracks['CleanName']])
                    myDB.action('UPDATE have SET CleanName=?, Matched="Failed" WHERE ArtistName=? AND AlbumTitle=? AND TrackTitle=?', (original_clean, artist, album, track_title))
                    update_count+=1
            if update_count > 0:
                librarysync.update_album_status(album_id)
            logger.info("Album: %s successfully restored to unmatched list" % album)

    markManual.exposed = True

    def markArtists(self, action=None, **args):
        myDB = db.DBConnection()
        artistsToAdd = []
        for ArtistID in args:
            if action == 'delete':
                myDB.action('DELETE from artists WHERE ArtistID=?', [ArtistID])

                rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM albums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
                for rgid in rgids:
                    myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

                myDB.action('DELETE from albums WHERE ArtistID=?', [ArtistID])
                myDB.action('DELETE from tracks WHERE ArtistID=?', [ArtistID])

                rgids = myDB.select('SELECT DISTINCT ReleaseGroupID FROM allalbums JOIN releases ON AlbumID = ReleaseGroupID WHERE ArtistID=?', [ArtistID])
                for rgid in rgids:
                    myDB.action('DELETE from releases WHERE ReleaseGroupID=?', [rgid['ReleaseGroupID']])

                myDB.action('DELETE from allalbums WHERE ArtistID=?', [ArtistID])
                myDB.action('DELETE from alltracks WHERE ArtistID=?', [ArtistID])
                myDB.action('INSERT OR REPLACE into blacklist VALUES (?)', [ArtistID])
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
    markArtists.exposed = True

    def importLastFM(self, username):
        headphones.LASTFM_USERNAME = username
        headphones.config_write()
        threading.Thread(target=lastfm.getArtists).start()
        raise cherrypy.HTTPRedirect("home")
    importLastFM.exposed = True

    def importLastFMTag(self, tag, limit):
        threading.Thread(target=lastfm.getTagTopArtists, args=(tag, limit)).start()
        raise cherrypy.HTTPRedirect("home")
    importLastFMTag.exposed = True

    def importItunes(self, path):
        headphones.PATH_TO_XML = path
        headphones.config_write()
        threading.Thread(target=importer.itunesImport, args=[path]).start()
        time.sleep(10)
        raise cherrypy.HTTPRedirect("home")
    importItunes.exposed = True

    def musicScan(self, path, scan=0, redirect=None, autoadd=0, libraryscan=0):
        headphones.LIBRARYSCAN = libraryscan
        headphones.ADD_ARTISTS = autoadd
        headphones.MUSIC_DIR = path
        headphones.config_write()
        if scan:
            try:
                threading.Thread(target=librarysync.libraryScan).start()
            except Exception, e:
                logger.error('Unable to complete the scan: %s' % e)
        if redirect:
            raise cherrypy.HTTPRedirect(redirect)
        else:
            raise cherrypy.HTTPRedirect("home")
    musicScan.exposed = True

    def forceUpdate(self):
        from headphones import updater
        threading.Thread(target=updater.dbUpdate, args=[False]).start()
        raise cherrypy.HTTPRedirect("home")
    forceUpdate.exposed = True

    def forceFullUpdate(self):
        from headphones import updater
        threading.Thread(target=updater.dbUpdate, args=[True]).start()
        raise cherrypy.HTTPRedirect("home")
    forceFullUpdate.exposed = True

    def forceSearch(self):
        from headphones import searcher
        threading.Thread(target=searcher.searchforalbum).start()
        raise cherrypy.HTTPRedirect("home")
    forceSearch.exposed = True

    def forcePostProcess(self, dir=None, album_dir=None):
        from headphones import postprocessor
        threading.Thread(target=postprocessor.forcePostProcess, kwargs={'dir':dir,'album_dir':album_dir}).start()
        raise cherrypy.HTTPRedirect("home")
    forcePostProcess.exposed = True

    def checkGithub(self):
        from headphones import versioncheck
        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect("home")
    checkGithub.exposed = True

    def history(self):
        myDB = db.DBConnection()
        history = myDB.select('''SELECT * from snatched order by DateAdded DESC''')
        return serve_template(templatename="history.html", title="History", history=history)
    history.exposed = True

    def logs(self):
        return serve_template(templatename="logs.html", title="Log", lineList=headphones.LOG_LIST)
    logs.exposed = True

    def clearLogs(self):
        headphones.LOG_LIST = []
        logger.info("Web logs cleared")
        raise cherrypy.HTTPRedirect("logs")
    clearLogs.exposed = True

    def toggleVerbose(self):
        headphones.VERBOSE = not headphones.VERBOSE
        logger.initLogger(not headphones.QUIET, headphones.VERBOSE)
        logger.info("Verbose toggled, set to %s", headphones.VERBOSE)
        logger.debug("If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect("logs")
    toggleVerbose.exposed = True

    def getLog(self,iDisplayStart=0,iDisplayLength=100,iSortCol_0=0,sSortDir_0="desc",sSearch="",**kwargs):

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
        filtered.sort(key=lambda x:x[sortcolumn],reverse=sSortDir_0 == "desc")

        rows = filtered[iDisplayStart:(iDisplayStart+iDisplayLength)]
        rows = [[row[0],row[2],row[1]] for row in rows]

        dict = {'iTotalDisplayRecords':len(filtered),
                'iTotalRecords':len(headphones.LOG_LIST),
                'aaData':rows,
                }
        s = simplejson.dumps(dict)
        return s
    getLog.exposed = True

    def getArtists_json(self,iDisplayStart=0,iDisplayLength=100,sSearch="",iSortCol_0='0',sSortDir_0='asc',**kwargs):
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
            query = 'SELECT * from artists order by %s COLLATE NOCASE %s' % (sortcolumn,sSortDir_0)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT * from artists WHERE ArtistSortName LIKE "%' + sSearch + '%" OR LatestAlbum LIKE "%' + sSearch +'%"' +  'ORDER BY %s COLLATE NOCASE %s' % (sortcolumn,sSortDir_0)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from artists')[0][0]

        if sortbyhavepercent:
            filtered.sort(key=lambda x:(float(x['HaveTracks'])/x['TotalTracks'] if x['TotalTracks'] > 0 else 0.0,x['HaveTracks'] if x['HaveTracks'] else 0.0),reverse=sSortDir_0 == "asc")

        #can't figure out how to change the datatables default sorting order when its using an ajax datasource so ill
        #just reverse it here and the first click on the "Latest Album" header will sort by descending release date
        if sortcolumn == 'ReleaseDate':
            filtered.reverse()


        artists = filtered[iDisplayStart:(iDisplayStart+iDisplayLength)]
        rows = []
        for artist in artists:
            row = {"ArtistID":artist['ArtistID'],
                      "ArtistName":artist["ArtistName"],
                      "ArtistSortName":artist["ArtistSortName"],
                      "Status":artist["Status"],
                      "TotalTracks":artist["TotalTracks"],
                      "HaveTracks":artist["HaveTracks"],
                      "LatestAlbum":"",
                      "ReleaseDate":"",
                      "ReleaseInFuture":"False",
                      "AlbumID":"",
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


        dict = {'iTotalDisplayRecords':len(filtered),
                'iTotalRecords':totalcount,
                'aaData':rows,
                }
        s = simplejson.dumps(dict)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s
    getArtists_json.exposed=True

    def getAlbumsByArtist_json(self, artist=None):
        myDB = db.DBConnection()
        album_json = {}
        counter = 0
        album_list = myDB.select("SELECT AlbumTitle from albums WHERE ArtistName=?", [artist])
        for album in album_list:
            album_json[counter] = album['AlbumTitle']
            counter+=1
        json_albums = json.dumps(album_json)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json_albums
    getAlbumsByArtist_json.exposed=True

    def getArtistjson(self, ArtistID, **kwargs):
        myDB = db.DBConnection()
        artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [ArtistID]).fetchone()
        artist_json = json.dumps({      
                                    'ArtistName': artist['ArtistName'],
                                    'Status':     artist['Status']                        
                                 })
        return artist_json
    getArtistjson.exposed=True

    def getAlbumjson(self, AlbumID, **kwargs):
        myDB = db.DBConnection()
        album = myDB.action('SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
        album_json = json.dumps({
                                   'AlbumTitle': album['AlbumTitle'],
                                   'ArtistName': album['ArtistName'],
                                   'Status':     album['Status']
        })
        return album_json
    getAlbumjson.exposed=True

    def clearhistory(self, type=None, date_added=None, title=None):
        myDB = db.DBConnection()
        if type:
            if type == 'all':
                logger.info(u"Clearing all history")
                myDB.action('DELETE from snatched')
            else:
                logger.info(u"Clearing history where status is %s" % type)
                myDB.action('DELETE from snatched WHERE Status=?', [type])
        else:
            logger.info(u"Deleting '%s' from history" % title)
            myDB.action('DELETE from snatched WHERE Title=? AND DateAdded=?', [title, date_added])
        raise cherrypy.HTTPRedirect("history")
    clearhistory.exposed = True

    def generateAPI(self):

        import hashlib, random

        apikey = hashlib.sha224( str(random.getrandbits(256)) ).hexdigest()[0:32]
        logger.info("New API generated")
        return apikey

    generateAPI.exposed = True

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
        except Exception, e:
            logger.error('Unable to complete the scan: %s' % e)
        raise cherrypy.HTTPRedirect("home")
    forceScan.exposed = True

    def config(self):

        interface_dir = os.path.join(headphones.PROG_DIR, 'data/interfaces/')
        interface_list = [ name for name in os.listdir(interface_dir) if os.path.isdir(os.path.join(interface_dir, name)) ]

        config = {
                    "http_host" : headphones.HTTP_HOST,
                    "http_user" : headphones.HTTP_USERNAME,
                    "http_port" : headphones.HTTP_PORT,
                    "http_pass" : headphones.HTTP_PASSWORD,
                    "launch_browser" : checked(headphones.LAUNCH_BROWSER),
                    "enable_https" : checked(headphones.ENABLE_HTTPS),
                    "https_cert" : headphones.HTTPS_CERT,
                    "https_key" : headphones.HTTPS_KEY,
                    "api_enabled" : checked(headphones.API_ENABLED),
                    "api_key" : headphones.API_KEY,
                    "download_scan_interval" : headphones.DOWNLOAD_SCAN_INTERVAL,
                    "update_db_interval" : headphones.UPDATE_DB_INTERVAL,
                    "mb_ignore_age" : headphones.MB_IGNORE_AGE,
                    "nzb_search_interval" : headphones.SEARCH_INTERVAL,
                    "libraryscan_interval" : headphones.LIBRARYSCAN_INTERVAL,
                    "sab_host" : headphones.SAB_HOST,
                    "sab_user" : headphones.SAB_USERNAME,
                    "sab_api" : headphones.SAB_APIKEY,
                    "sab_pass" : headphones.SAB_PASSWORD,
                    "sab_cat" : headphones.SAB_CATEGORY,
                    "nzbget_host" : headphones.NZBGET_HOST,
                    "nzbget_user" : headphones.NZBGET_USERNAME,
                    "nzbget_pass" : headphones.NZBGET_PASSWORD,
                    "nzbget_cat" : headphones.NZBGET_CATEGORY,
                    "transmission_host" : headphones.TRANSMISSION_HOST,
                    "transmission_user" : headphones.TRANSMISSION_USERNAME,
                    "transmission_pass" : headphones.TRANSMISSION_PASSWORD,
                    "utorrent_host" : headphones.UTORRENT_HOST,
                    "utorrent_user" : headphones.UTORRENT_USERNAME,
                    "utorrent_pass" : headphones.UTORRENT_PASSWORD,
                    "utorrent_label" : headphones.UTORRENT_LABEL,
                    "nzb_downloader_sabnzbd" : radio(headphones.NZB_DOWNLOADER, 0),
                    "nzb_downloader_nzbget" : radio(headphones.NZB_DOWNLOADER, 1),
                    "nzb_downloader_blackhole" : radio(headphones.NZB_DOWNLOADER, 2),
                    "torrent_downloader_blackhole" : radio(headphones.TORRENT_DOWNLOADER, 0),
                    "torrent_downloader_transmission" : radio(headphones.TORRENT_DOWNLOADER, 1),
                    "torrent_downloader_utorrent" : radio(headphones.TORRENT_DOWNLOADER, 2),
                    "download_dir" : headphones.DOWNLOAD_DIR,
                    "use_blackhole" : checked(headphones.BLACKHOLE),
                    "blackhole_dir" : headphones.BLACKHOLE_DIR,
                    "usenet_retention" : headphones.USENET_RETENTION,
                    "use_headphones_indexer" : checked(headphones.HEADPHONES_INDEXER),
                    "use_newznab" : checked(headphones.NEWZNAB),
                    "newznab_host" : headphones.NEWZNAB_HOST,
                    "newznab_api" : headphones.NEWZNAB_APIKEY,
                    "newznab_enabled" : checked(headphones.NEWZNAB_ENABLED),
                    "extra_newznabs" : headphones.EXTRA_NEWZNABS,
                    "use_nzbsorg" : checked(headphones.NZBSORG),
                    "nzbsorg_uid" : headphones.NZBSORG_UID,
                    "nzbsorg_hash" : headphones.NZBSORG_HASH,
                    "use_omgwtfnzbs" : checked(headphones.OMGWTFNZBS),
                    "omgwtfnzbs_uid" : headphones.OMGWTFNZBS_UID,
                    "omgwtfnzbs_apikey" : headphones.OMGWTFNZBS_APIKEY,
                    "preferred_words" : headphones.PREFERRED_WORDS,
                    "ignored_words" : headphones.IGNORED_WORDS,
                    "required_words" : headphones.REQUIRED_WORDS,
                    "torrentblackhole_dir" : headphones.TORRENTBLACKHOLE_DIR,
                    "download_torrent_dir" : headphones.DOWNLOAD_TORRENT_DIR,
                    "numberofseeders" : headphones.NUMBEROFSEEDERS,
                    "use_kat" : checked(headphones.KAT),
                    "kat_proxy_url" : headphones.KAT_PROXY_URL,
                    "use_piratebay" : checked(headphones.PIRATEBAY),
                    "piratebay_proxy_url" : headphones.PIRATEBAY_PROXY_URL,
                    "use_mininova" : checked(headphones.MININOVA),
                    "use_waffles" : checked(headphones.WAFFLES),
                    "waffles_uid" : headphones.WAFFLES_UID,
                    "waffles_passkey": headphones.WAFFLES_PASSKEY,
                    "use_rutracker" : checked(headphones.RUTRACKER),
                    "rutracker_user" : headphones.RUTRACKER_USER,
                    "rutracker_password": headphones.RUTRACKER_PASSWORD,
                    "use_whatcd" : checked(headphones.WHATCD),
                    "whatcd_username" : headphones.WHATCD_USERNAME,
                    "whatcd_password": headphones.WHATCD_PASSWORD,
                    "pref_qual_0" : radio(headphones.PREFERRED_QUALITY, 0),
                    "pref_qual_1" : radio(headphones.PREFERRED_QUALITY, 1),
                    "pref_qual_3" : radio(headphones.PREFERRED_QUALITY, 3),
                    "pref_qual_2" : radio(headphones.PREFERRED_QUALITY, 2),
                    "pref_bitrate" : headphones.PREFERRED_BITRATE,
                    "pref_bitrate_high" : headphones.PREFERRED_BITRATE_HIGH_BUFFER,
                    "pref_bitrate_low" : headphones.PREFERRED_BITRATE_LOW_BUFFER,
                    "pref_bitrate_allow_lossless" : checked(headphones.PREFERRED_BITRATE_ALLOW_LOSSLESS),
                    "detect_bitrate" : checked(headphones.DETECT_BITRATE),
                    "lossless_bitrate_from" : headphones.LOSSLESS_BITRATE_FROM,
                    "lossless_bitrate_to" : headphones.LOSSLESS_BITRATE_TO,
                    "move_files" : checked(headphones.MOVE_FILES),
                    "rename_files" : checked(headphones.RENAME_FILES),
                    "correct_metadata" : checked(headphones.CORRECT_METADATA),
                    "cleanup_files" : checked(headphones.CLEANUP_FILES),
                    "add_album_art" : checked(headphones.ADD_ALBUM_ART),
                    "album_art_format" : headphones.ALBUM_ART_FORMAT,
                    "embed_album_art" : checked(headphones.EMBED_ALBUM_ART),
                    "embed_lyrics" : checked(headphones.EMBED_LYRICS),
                    "replace_existing_folders" : checked(headphones.REPLACE_EXISTING_FOLDERS),
                    "dest_dir" : headphones.DESTINATION_DIR,
                    "lossless_dest_dir" : headphones.LOSSLESS_DESTINATION_DIR,
                    "folder_format" : headphones.FOLDER_FORMAT,
                    "file_format" : headphones.FILE_FORMAT,
                    "file_underscores" : checked(headphones.FILE_UNDERSCORES),
                    "include_extras" : checked(headphones.INCLUDE_EXTRAS),
                    "autowant_upcoming" : checked(headphones.AUTOWANT_UPCOMING),
                    "autowant_all" : checked(headphones.AUTOWANT_ALL),
                    "keep_torrent_files" : checked(headphones.KEEP_TORRENT_FILES),
                    "prefer_torrents_0" : radio(headphones.PREFER_TORRENTS, 0),
                    "prefer_torrents_1" : radio(headphones.PREFER_TORRENTS, 1),
                    "prefer_torrents_2" : radio(headphones.PREFER_TORRENTS, 2),
                    "open_magnet_links" : checked(headphones.OPEN_MAGNET_LINKS),
                    "log_dir" : headphones.LOG_DIR,
                    "cache_dir" : headphones.CACHE_DIR,
                    "interface_list" : interface_list,
                    "music_encoder":        checked(headphones.MUSIC_ENCODER),
                    "encoder":      headphones.ENCODER,
                    "xldprofile":   headphones.XLDPROFILE,
                    "bitrate":      int(headphones.BITRATE),
                    "encoderfolder":    headphones.ENCODER_PATH,
                    "advancedencoder":  headphones.ADVANCEDENCODER,
                    "encoderoutputformat": headphones.ENCODEROUTPUTFORMAT,
                    "samplingfrequency": headphones.SAMPLINGFREQUENCY,
                    "encodervbrcbr": headphones.ENCODERVBRCBR,
                    "encoderquality": headphones.ENCODERQUALITY,
                    "encoderlossless": checked(headphones.ENCODERLOSSLESS),
                    "encoder_multicore": checked(headphones.ENCODER_MULTICORE),
                    "encoder_multicore_count": int(headphones.ENCODER_MULTICORE_COUNT),
                    "delete_lossless_files": checked(headphones.DELETE_LOSSLESS_FILES),
                    "growl_enabled": checked(headphones.GROWL_ENABLED),
                    "growl_onsnatch": checked(headphones.GROWL_ONSNATCH),
                    "growl_host": headphones.GROWL_HOST,
                    "growl_password": headphones.GROWL_PASSWORD,
                    "prowl_enabled": checked(headphones.PROWL_ENABLED),
                    "prowl_onsnatch": checked(headphones.PROWL_ONSNATCH),
                    "prowl_keys": headphones.PROWL_KEYS,
                    "prowl_priority": headphones.PROWL_PRIORITY,
                    "xbmc_enabled": checked(headphones.XBMC_ENABLED),
                    "xbmc_host": headphones.XBMC_HOST,
                    "xbmc_username": headphones.XBMC_USERNAME,
                    "xbmc_password": headphones.XBMC_PASSWORD,
                    "xbmc_update": checked(headphones.XBMC_UPDATE),
                    "xbmc_notify": checked(headphones.XBMC_NOTIFY),
                    "lms_enabled": checked(headphones.LMS_ENABLED),
                    "lms_host": headphones.LMS_HOST,
                    "plex_enabled": checked(headphones.PLEX_ENABLED),
                    "plex_server_host": headphones.PLEX_SERVER_HOST,
                    "plex_client_host": headphones.PLEX_CLIENT_HOST,
                    "plex_username": headphones.PLEX_USERNAME,
                    "plex_password": headphones.PLEX_PASSWORD,
                    "plex_update": checked(headphones.PLEX_UPDATE),
                    "plex_notify": checked(headphones.PLEX_NOTIFY),
                    "nma_enabled": checked(headphones.NMA_ENABLED),
                    "nma_apikey": headphones.NMA_APIKEY,
                    "nma_priority": int(headphones.NMA_PRIORITY),
                    "nma_onsnatch": checked(headphones.NMA_ONSNATCH),
                    "pushalot_enabled": checked(headphones.PUSHALOT_ENABLED),
                    "pushalot_apikey": headphones.PUSHALOT_APIKEY,
                    "pushalot_onsnatch": checked(headphones.PUSHALOT_ONSNATCH),
                    "synoindex_enabled": checked(headphones.SYNOINDEX_ENABLED),
                    "pushover_enabled": checked(headphones.PUSHOVER_ENABLED),
                    "pushover_onsnatch": checked(headphones.PUSHOVER_ONSNATCH),
                    "pushover_keys": headphones.PUSHOVER_KEYS,
                    "pushover_apitoken": headphones.PUSHOVER_APITOKEN,
                    "pushover_priority": headphones.PUSHOVER_PRIORITY,
                    "pushbullet_enabled": checked(headphones.PUSHBULLET_ENABLED),
                    "pushbullet_onsnatch": checked(headphones.PUSHBULLET_ONSNATCH),
                    "pushbullet_apikey": headphones.PUSHBULLET_APIKEY,
                    "pushbullet_deviceid": headphones.PUSHBULLET_DEVICEID,
                    "twitter_enabled": checked(headphones.TWITTER_ENABLED),
                    "twitter_onsnatch": checked(headphones.TWITTER_ONSNATCH),
                    "osx_notify_enabled": checked(headphones.OSX_NOTIFY_ENABLED),
                    "osx_notify_onsnatch": checked(headphones.OSX_NOTIFY_ONSNATCH),
                    "osx_notify_app": headphones.OSX_NOTIFY_APP,
                    "boxcar_enabled": checked(headphones.BOXCAR_ENABLED),
                    "boxcar_onsnatch": checked(headphones.BOXCAR_ONSNATCH),
                    "boxcar_token": headphones.BOXCAR_TOKEN,
                    "mirror_list": headphones.MIRRORLIST,
                    "mirror": headphones.MIRROR,
                    "customhost": headphones.CUSTOMHOST,
                    "customport": headphones.CUSTOMPORT,
                    "customsleep": headphones.CUSTOMSLEEP,
                    "hpuser": headphones.HPUSER,
                    "hppass": headphones.HPPASS,
                    "songkick_enabled": checked(headphones.SONGKICK_ENABLED),
                    "songkick_apikey": headphones.SONGKICK_APIKEY,
                    "songkick_location": headphones.SONGKICK_LOCATION,
                    "songkick_filter_enabled": checked(headphones.SONGKICK_FILTER_ENABLED),
                    "cache_sizemb": headphones.CACHE_SIZEMB,
                    "file_permissions": headphones.FILE_PERMISSIONS,
                    "folder_permissions": headphones.FOLDER_PERMISSIONS,
                    "mpc_enabled": checked(headphones.MPC_ENABLED)
                }

        # Need to convert EXTRAS to a dictionary we can pass to the config: it'll come in as a string like 2,5,6,8
        extras_list = ["single", "ep", "compilation", "soundtrack", "live", "remix", "dj-mix", "mixtape/street", "spokenword", "audiobook", "broadcast", "interview", "other"]
        extras_dict = {}

        i = 1
        for extra in extras_list:
            if str(i) in headphones.EXTRAS:
                extras_dict[extra] = "checked"
            else:
                extras_dict[extra] = ""
            i+=1

        config["extras"] = extras_dict

        return serve_template(templatename="config.html", title="Settings", config=config)
    config.exposed = True

    def configUpdate(self, http_host='0.0.0.0', http_username=None, http_port=8181, http_password=None, launch_browser=0, api_enabled=0, api_key=None,
        download_scan_interval=None, update_db_interval=None, mb_ignore_age=None, nzb_search_interval=None, libraryscan_interval=None, sab_host=None, sab_username=None, sab_apikey=None, sab_password=None,
        sab_category=None, nzbget_host=None, nzbget_username=None, nzbget_password=None, nzbget_category=None, transmission_host=None, transmission_username=None, transmission_password=None,
        utorrent_host=None, utorrent_username=None, utorrent_password=None, utorrent_label=None,nzb_downloader=0, torrent_downloader=0, download_dir=None, blackhole_dir=None, usenet_retention=None,
        use_headphones_indexer=0, newznab=0, newznab_host=None, newznab_apikey=None, newznab_enabled=0, nzbsorg=0, nzbsorg_uid=None, nzbsorg_hash=None, omgwtfnzbs=0, omgwtfnzbs_uid=None, omgwtfnzbs_apikey=None,
        preferred_words=None, required_words=None, ignored_words=None, preferred_quality=0, preferred_bitrate=None, detect_bitrate=0, move_files=0, torrentblackhole_dir=None, download_torrent_dir=None,
        numberofseeders=None, use_piratebay=0, piratebay_proxy_url=None, use_kat=0, kat_proxy_url=None, use_mininova=0, waffles=0, waffles_uid=None, waffles_passkey=None, whatcd=0, whatcd_username=None, whatcd_password=None,
        rutracker=0, rutracker_user=None, rutracker_password=None, rename_files=0, correct_metadata=0, cleanup_files=0, add_album_art=0, album_art_format=None, embed_album_art=0, embed_lyrics=0, replace_existing_folders=False,
        destination_dir=None, lossless_destination_dir=None, folder_format=None, file_format=None, file_underscores=0, include_extras=0, single=0, ep=0, compilation=0, soundtrack=0, live=0,
        remix=0, djmix=0, mixtape_street=0, broadcast=0, interview=0, spokenword=0, audiobook=0, other=0, autowant_upcoming=False, autowant_all=False, keep_torrent_files=False, prefer_torrents=0, open_magnet_links=0, interface=None, log_dir=None, cache_dir=None, music_encoder=0, encoder=None, xldprofile=None,
        bitrate=None, samplingfrequency=None, encoderfolder=None, advancedencoder=None, encoderoutputformat=None, encodervbrcbr=None, encoderquality=None, encoderlossless=0,
        delete_lossless_files=0, growl_enabled=0, growl_onsnatch=0, growl_host=None, growl_password=None, prowl_enabled=0, prowl_onsnatch=0, prowl_keys=None, prowl_priority=0, xbmc_enabled=0, xbmc_host=None, xbmc_username=None, xbmc_password=None,
        xbmc_update=0, xbmc_notify=0, nma_enabled=False, nma_apikey=None, nma_priority=0, nma_onsnatch=0, pushalot_enabled=False, pushalot_apikey=None, pushalot_onsnatch=0, synoindex_enabled=False, lms_enabled=0, lms_host=None,
        pushover_enabled=0, pushover_onsnatch=0, pushover_keys=None, pushover_priority=0, pushover_apitoken=None, pushbullet_enabled=0, pushbullet_onsnatch=0, pushbullet_apikey=None, pushbullet_deviceid=None, twitter_enabled=0, twitter_onsnatch=0,
        osx_notify_enabled=0, osx_notify_onsnatch=0, osx_notify_app=None, boxcar_enabled=0, boxcar_onsnatch=0, boxcar_token=None, mirror=None, customhost=None, customport=None, customsleep=None, hpuser=None, hppass=None,
        preferred_bitrate_high_buffer=None, preferred_bitrate_low_buffer=None, preferred_bitrate_allow_lossless=0, lossless_bitrate_from=None, lossless_bitrate_to=None, cache_sizemb=None, enable_https=0, https_cert=None, https_key=None,
        file_permissions=None, folder_permissions=None, plex_enabled=0, plex_server_host=None, plex_client_host=None, plex_username=None, plex_password=None, plex_update=0, plex_notify=0,
        songkick_enabled=0, songkick_apikey=None, songkick_location=None, songkick_filter_enabled=0, encoder_multicore=False, encoder_multicore_count=0, mpc_enabled=False, **kwargs ):

        headphones.HTTP_HOST = http_host
        headphones.HTTP_PORT = http_port
        headphones.HTTP_USERNAME = http_username
        headphones.HTTP_PASSWORD = http_password
        headphones.LAUNCH_BROWSER = launch_browser
        headphones.ENABLE_HTTPS = enable_https
        headphones.HTTPS_CERT = https_cert
        headphones.HTTPS_KEY = https_key
        headphones.API_ENABLED = api_enabled
        headphones.API_KEY = api_key
        headphones.DOWNLOAD_SCAN_INTERVAL = download_scan_interval
        headphones.UPDATE_DB_INTERVAL = update_db_interval
        headphones.MB_IGNORE_AGE = mb_ignore_age
        headphones.SEARCH_INTERVAL = nzb_search_interval
        headphones.LIBRARYSCAN_INTERVAL = libraryscan_interval
        headphones.SAB_HOST = sab_host
        headphones.SAB_USERNAME = sab_username
        headphones.SAB_PASSWORD = sab_password
        headphones.SAB_APIKEY = sab_apikey
        headphones.SAB_CATEGORY = sab_category
        headphones.NZBGET_HOST = nzbget_host
        headphones.NZBGET_USERNAME = nzbget_username
        headphones.NZBGET_PASSWORD = nzbget_password
        headphones.NZBGET_CATEGORY = nzbget_category
        headphones.TRANSMISSION_HOST = transmission_host
        headphones.TRANSMISSION_USERNAME = transmission_username
        headphones.TRANSMISSION_PASSWORD = transmission_password
        headphones.UTORRENT_HOST = utorrent_host
        headphones.UTORRENT_USERNAME = utorrent_username
        headphones.UTORRENT_PASSWORD = utorrent_password
        headphones.UTORRENT_LABEL = utorrent_label
        headphones.NZB_DOWNLOADER = int(nzb_downloader)
        headphones.TORRENT_DOWNLOADER = int(torrent_downloader)
        headphones.DOWNLOAD_DIR = download_dir
        headphones.BLACKHOLE_DIR = blackhole_dir
        headphones.USENET_RETENTION = usenet_retention
        headphones.HEADPHONES_INDEXER = use_headphones_indexer
        headphones.NEWZNAB = newznab
        headphones.NEWZNAB_HOST = newznab_host
        headphones.NEWZNAB_APIKEY = newznab_apikey
        headphones.NEWZNAB_ENABLED = newznab_enabled
        headphones.NZBSORG = nzbsorg
        headphones.NZBSORG_UID = nzbsorg_uid
        headphones.NZBSORG_HASH = nzbsorg_hash
        headphones.OMGWTFNZBS = omgwtfnzbs
        headphones.OMGWTFNZBS_UID = omgwtfnzbs_uid
        headphones.OMGWTFNZBS_APIKEY = omgwtfnzbs_apikey
        headphones.PREFERRED_WORDS = preferred_words
        headphones.IGNORED_WORDS = ignored_words
        headphones.REQUIRED_WORDS = required_words
        headphones.TORRENTBLACKHOLE_DIR = torrentblackhole_dir
        headphones.NUMBEROFSEEDERS = numberofseeders
        headphones.DOWNLOAD_TORRENT_DIR = download_torrent_dir
        headphones.KAT = use_kat
        headphones.KAT_PROXY_URL = kat_proxy_url
        headphones.PIRATEBAY = use_piratebay
        headphones.PIRATEBAY_PROXY_URL = piratebay_proxy_url
        headphones.MININOVA = use_mininova
        headphones.WAFFLES = waffles
        headphones.WAFFLES_UID = waffles_uid
        headphones.WAFFLES_PASSKEY = waffles_passkey
        headphones.RUTRACKER = rutracker
        headphones.RUTRACKER_USER = rutracker_user
        headphones.RUTRACKER_PASSWORD = rutracker_password
        headphones.WHATCD = whatcd
        headphones.WHATCD_USERNAME = whatcd_username
        headphones.WHATCD_PASSWORD = whatcd_password
        headphones.PREFERRED_QUALITY = int(preferred_quality)
        headphones.PREFERRED_BITRATE = preferred_bitrate
        headphones.PREFERRED_BITRATE_HIGH_BUFFER = preferred_bitrate_high_buffer
        headphones.PREFERRED_BITRATE_LOW_BUFFER = preferred_bitrate_low_buffer
        headphones.PREFERRED_BITRATE_ALLOW_LOSSLESS = preferred_bitrate_allow_lossless
        headphones.DETECT_BITRATE = detect_bitrate
        headphones.LOSSLESS_BITRATE_FROM = lossless_bitrate_from
        headphones.LOSSLESS_BITRATE_TO = lossless_bitrate_to
        headphones.MOVE_FILES = move_files
        headphones.CORRECT_METADATA = correct_metadata
        headphones.RENAME_FILES = rename_files
        headphones.CLEANUP_FILES = cleanup_files
        headphones.ADD_ALBUM_ART = add_album_art
        headphones.ALBUM_ART_FORMAT = album_art_format
        headphones.EMBED_ALBUM_ART = embed_album_art
        headphones.EMBED_LYRICS = embed_lyrics
        headphones.REPLACE_EXISTING_FOLDERS = replace_existing_folders
        headphones.DESTINATION_DIR = destination_dir
        headphones.LOSSLESS_DESTINATION_DIR = lossless_destination_dir
        headphones.FOLDER_FORMAT = folder_format
        headphones.FILE_FORMAT = file_format
        headphones.FILE_UNDERSCORES = file_underscores
        headphones.INCLUDE_EXTRAS = include_extras
        headphones.AUTOWANT_UPCOMING = autowant_upcoming
        headphones.AUTOWANT_ALL = autowant_all
        headphones.KEEP_TORRENT_FILES = keep_torrent_files
        headphones.PREFER_TORRENTS = int(prefer_torrents)
        headphones.OPEN_MAGNET_LINKS = open_magnet_links
        headphones.INTERFACE = interface
        headphones.LOG_DIR = log_dir
        headphones.CACHE_DIR = cache_dir
        headphones.MUSIC_ENCODER = music_encoder
        headphones.ENCODER = encoder
        headphones.XLDPROFILE = xldprofile
        headphones.BITRATE = int(bitrate)
        headphones.SAMPLINGFREQUENCY = int(samplingfrequency)
        headphones.ENCODER_PATH = encoderfolder
        headphones.ADVANCEDENCODER = advancedencoder
        headphones.ENCODEROUTPUTFORMAT = encoderoutputformat
        headphones.ENCODERVBRCBR = encodervbrcbr
        headphones.ENCODERQUALITY = int(encoderquality)
        headphones.ENCODERLOSSLESS = int(encoderlossless)
        headphones.ENCODER_MULTICORE = encoder_multicore
        headphones.ENCODER_MULTICORE_COUNT = max(0, int(encoder_multicore_count))
        headphones.DELETE_LOSSLESS_FILES = int(delete_lossless_files)
        headphones.GROWL_ENABLED = growl_enabled
        headphones.GROWL_ONSNATCH = growl_onsnatch
        headphones.GROWL_HOST = growl_host
        headphones.GROWL_PASSWORD = growl_password
        headphones.PROWL_ENABLED = prowl_enabled
        headphones.PROWL_ONSNATCH = prowl_onsnatch
        headphones.PROWL_KEYS = prowl_keys
        headphones.PROWL_PRIORITY = prowl_priority
        headphones.XBMC_ENABLED = xbmc_enabled
        headphones.XBMC_HOST = xbmc_host
        headphones.XBMC_USERNAME = xbmc_username
        headphones.XBMC_PASSWORD = xbmc_password
        headphones.XBMC_UPDATE = xbmc_update
        headphones.XBMC_NOTIFY = xbmc_notify
        headphones.LMS_ENABLED = lms_enabled
        headphones.LMS_HOST = lms_host
        headphones.PLEX_ENABLED = plex_enabled
        headphones.PLEX_SERVER_HOST = plex_server_host
        headphones.PLEX_CLIENT_HOST = plex_client_host
        headphones.PLEX_USERNAME = plex_username
        headphones.PLEX_PASSWORD = plex_password
        headphones.PLEX_UPDATE = plex_update
        headphones.PLEX_NOTIFY = plex_notify
        headphones.NMA_ENABLED = nma_enabled
        headphones.NMA_APIKEY = nma_apikey
        headphones.NMA_PRIORITY = nma_priority
        headphones.NMA_ONSNATCH = nma_onsnatch
        headphones.PUSHALOT_ENABLED = pushalot_enabled
        headphones.PUSHALOT_APIKEY = pushalot_apikey
        headphones.PUSHALOT_ONSNATCH = pushalot_onsnatch
        headphones.SYNOINDEX_ENABLED = synoindex_enabled
        headphones.PUSHOVER_ENABLED = pushover_enabled
        headphones.PUSHOVER_ONSNATCH = pushover_onsnatch
        headphones.PUSHOVER_KEYS = pushover_keys
        headphones.PUSHOVER_PRIORITY = pushover_priority
        headphones.PUSHOVER_APITOKEN = pushover_apitoken
        headphones.PUSHBULLET_ENABLED = pushbullet_enabled
        headphones.PUSHBULLET_ONSNATCH = pushbullet_onsnatch
        headphones.PUSHBULLET_APIKEY = pushbullet_apikey
        headphones.PUSHBULLET_DEVICEID = pushbullet_deviceid
        headphones.SONGKICK_ENABLED = songkick_enabled
        headphones.SONGKICK_APIKEY = songkick_apikey
        headphones.SONGKICK_LOCATION = songkick_location
        headphones.SONGKICK_FILTER_ENABLED = songkick_filter_enabled
        headphones.TWITTER_ENABLED = twitter_enabled
        headphones.TWITTER_ONSNATCH = twitter_onsnatch

        headphones.OSX_NOTIFY_ENABLED = osx_notify_enabled
        headphones.OSX_NOTIFY_ONSNATCH = osx_notify_onsnatch
        headphones.OSX_NOTIFY_APP = osx_notify_app

        headphones.BOXCAR_ENABLED = boxcar_enabled
        headphones.BOXCAR_ONSNATCH = boxcar_onsnatch
        headphones.BOXCAR_TOKEN = boxcar_token

        headphones.MPC_ENABLED = mpc_enabled

        headphones.MIRROR = mirror
        headphones.CUSTOMHOST = customhost
        headphones.CUSTOMPORT = customport
        headphones.CUSTOMSLEEP = customsleep
        headphones.HPUSER = hpuser
        headphones.HPPASS = hppass
        headphones.CACHE_SIZEMB = int(cache_sizemb)
        headphones.FILE_PERMISSIONS = file_permissions
        headphones.FOLDER_PERMISSIONS = folder_permissions

        # Handle the variable config options. Note - keys with False values aren't getting passed

        headphones.EXTRA_NEWZNABS = []

        for kwarg in kwargs:
            if kwarg.startswith('newznab_host'):
                newznab_number = kwarg[12:]
                newznab_host = kwargs['newznab_host' + newznab_number]
                newznab_api = kwargs['newznab_api' + newznab_number]
                try:
                    newznab_enabled = int(kwargs['newznab_enabled' + newznab_number])
                except KeyError:
                    newznab_enabled = 0

                headphones.EXTRA_NEWZNABS.append((newznab_host, newznab_api, newznab_enabled))

        # Convert the extras to list then string. Coming in as 0 or 1
        temp_extras_list = []
        extras_list = [single, ep, compilation, soundtrack, live, remix, djmix, mixtape_street, spokenword, audiobook, broadcast, interview, other]

        i = 1
        for extra in extras_list:
            if extra:
                temp_extras_list.append(i)
            i+=1

        headphones.EXTRAS = ','.join(str(n) for n in temp_extras_list)

        # Sanity checking
        if headphones.SEARCH_INTERVAL < 360:
            logger.info("Search interval too low. Resetting to 6 hour minimum")
            headphones.SEARCH_INTERVAL = 360

        # Write the config
        headphones.config_write()

        #reconfigure musicbrainz database connection with the new values
        mb.startmb()

        raise cherrypy.HTTPRedirect("config")

    configUpdate.exposed = True

    def do_state_change(self, signal, title, timer):
        headphones.SIGNAL = signal
        message = title + '...'
        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer)

    def shutdown(self):
        return self.do_state_change('shutdown', 'Shutting Down', 15)
    shutdown.exposed = True

    def restart(self):
        return self.do_state_change('restart', 'Restarting', 30)
    restart.exposed = True

    def update(self):
        return self.do_state_change('update', 'Updating', 120)
    update.exposed = True

    def extras(self):
        myDB = db.DBConnection()
        cloudlist = myDB.select('SELECT * from lastfmcloud')
        return serve_template(templatename="extras.html", title="Extras", cloudlist=cloudlist)
        return page
    extras.exposed = True

    def addReleaseById(self, rid, rgid=None):
        threading.Thread(target=importer.addReleaseById, args=[rid, rgid]).start()
        if rgid:
            raise cherrypy.HTTPRedirect("albumPage?AlbumID=%s" % rgid)
        else:
            raise cherrypy.HTTPRedirect("home")
    addReleaseById.exposed = True

    def updateCloud(self):

        lastfm.getSimilar()
        raise cherrypy.HTTPRedirect("extras")

    updateCloud.exposed = True

    def api(self, *args, **kwargs):

        from headphones.api import Api

        a = Api()

        a.checkParams(*args, **kwargs)

        data = a.fetchData()

        return data

    api.exposed = True

    def getInfo(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        info_dict = cache.getInfo(ArtistID, AlbumID)

        return simplejson.dumps(info_dict)

    getInfo.exposed = True

    def getArtwork(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        return cache.getArtwork(ArtistID, AlbumID)

    getArtwork.exposed = True

    def getThumb(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        return cache.getThumb(ArtistID, AlbumID)

    getThumb.exposed = True

    # If you just want to get the last.fm image links for an album, make sure to pass a releaseid and not a releasegroupid
    def getImageLinks(self, ArtistID=None, AlbumID=None):

        from headphones import cache
        image_dict = cache.getImageLinks(ArtistID, AlbumID)

        # Return the Cover Art Archive urls if not found on last.fm
        if AlbumID and not image_dict:
            image_url = "http://coverartarchive.org/release/%s/front-500.jpg" % AlbumID
            thumb_url = "http://coverartarchive.org/release/%s/front-250.jpg" % AlbumID
            image_dict = {'artwork' : image_url, 'thumbnail' : thumb_url}
        elif AlbumID and (not image_dict['artwork'] or not image_dict['thumbnail']):
            if not image_dict['artwork']:
                image_dict['artwork'] = "http://coverartarchive.org/release/%s/front-500.jpg" % AlbumID
            if not image_dict['thumbnail']:
                image_dict['thumbnail'] = "http://coverartarchive.org/release/%s/front-250.jpg" % AlbumID

        return simplejson.dumps(image_dict)

    getImageLinks.exposed = True

    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        return tweet._get_authorization()
    twitterStep1.exposed = True

    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet._get_credentials(key)
        logger.info(u"result: "+str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"
    twitterStep2.exposed = True

    def testTwitter(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet.test_notify()
        if result:
            return "Tweet successful, check your twitter to make sure it worked"
        else:
            return "Error sending tweet"
    testTwitter.exposed = True

    def osxnotifyregister(self, app):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        from lib.osxnotify import registerapp as osxnotify
        result, msg = osxnotify.registerapp(app)
        if result:
            osx_notify = notifiers.OSX_NOTIFY()
            osx_notify.notify('Registered', result, 'Success :-)')
            logger.info('Registered %s, to re-register a different app, delete this app first' % result)
        else:
            logger.warn(msg)
        return msg
    osxnotifyregister.exposed = True

class Artwork(object):
    def index(self):
        return "Artwork"
    index.exposed = True

    def default(self,ArtistOrAlbum="",ID=None):
        from headphones import cache
        ArtistID = None
        AlbumID = None
        if ArtistOrAlbum == "artist":
            ArtistID = ID
        elif ArtistOrAlbum == "album":
            AlbumID = ID

        relpath =  cache.getArtwork(ArtistID,AlbumID)

        if not relpath:
            relpath = "data/interfaces/default/images/no-cover-art.png"
            basedir = os.path.dirname(sys.argv[0])
            path = os.path.join(basedir,relpath)
            cherrypy.response.headers['Content-type'] = 'image/png'
            cherrypy.response.headers['Cache-Control'] = 'no-cache'
        else:
            relpath = relpath.replace('cache/','',1)
            path = os.path.join(headphones.CACHE_DIR,relpath)
            fileext = os.path.splitext(relpath)[1][1::]
            cherrypy.response.headers['Content-type'] = 'image/' + fileext
            cherrypy.response.headers['Cache-Control'] = 'max-age=31556926'

        path = os.path.normpath(path)
        f = open(path,'rb')
        return f.read()
    default.exposed = True

    class Thumbs(object):
        def index(self):
            return "Here be thumbs"
        index.exposed = True
        def default(self,ArtistOrAlbum="",ID=None):
            from headphones import cache
            ArtistID = None
            AlbumID = None
            if ArtistOrAlbum == "artist":
                ArtistID = ID
            elif ArtistOrAlbum == "album":
                AlbumID = ID

            relpath =  cache.getThumb(ArtistID,AlbumID)

            if not relpath:
                relpath = "data/interfaces/default/images/no-cover-artist.png"
                basedir = os.path.dirname(sys.argv[0])
                path = os.path.join(basedir,relpath)
                cherrypy.response.headers['Content-type'] = 'image/png'
                cherrypy.response.headers['Cache-Control'] = 'no-cache'
            else:
                relpath = relpath.replace('cache/','',1)
                path = os.path.join(headphones.CACHE_DIR,relpath)
                fileext = os.path.splitext(relpath)[1][1::]
                cherrypy.response.headers['Content-type'] = 'image/' + fileext
                cherrypy.response.headers['Cache-Control'] = 'max-age=31556926'

            path = os.path.normpath(path)
            f = open(path,'rb')
            return f.read()
        default.exposed = True

    thumbs = Thumbs()


WebInterface.artwork = Artwork()
