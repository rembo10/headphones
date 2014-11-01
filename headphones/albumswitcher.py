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

import headphones
from headphones import db, logger, cache


def switch(AlbumID, ReleaseID):
    '''
    Takes the contents from allalbums & alltracks (based on ReleaseID) and switches them into
    the albums & tracks table.
    '''
    myDB = db.DBConnection()
    oldalbumdata = myDB.action(
        'SELECT * from albums WHERE AlbumID=?', [AlbumID]).fetchone()
    newalbumdata = myDB.action(
        'SELECT * from allalbums WHERE ReleaseID=?', [ReleaseID]).fetchone()
    newtrackdata = myDB.action(
        'SELECT * from alltracks WHERE ReleaseID=?', [ReleaseID]).fetchall()
    myDB.action('DELETE from tracks WHERE AlbumID=?', [AlbumID])

    controlValueDict = {"AlbumID":  AlbumID}

    newValueDict = {"ArtistID":         newalbumdata['ArtistID'],
                    "ArtistName":       newalbumdata['ArtistName'],
                    "AlbumTitle":       newalbumdata['AlbumTitle'],
                    "ReleaseID":        newalbumdata['ReleaseID'],
                    "AlbumASIN":        newalbumdata['AlbumASIN'],
                    "ReleaseDate":      newalbumdata['ReleaseDate'],
                    "Type":             newalbumdata['Type'],
                    "ReleaseCountry":   newalbumdata['ReleaseCountry'],
                    "ReleaseFormat":    newalbumdata['ReleaseFormat']
                    }

    myDB.upsert("albums", newValueDict, controlValueDict)

    # Update cache
    c = cache.Cache()
    c.remove_from_cache(AlbumID=AlbumID)
    c.get_artwork_from_cache(AlbumID=AlbumID)

    for track in newtrackdata:

        controlValueDict = {"TrackID":  track['TrackID'],
                            "AlbumID":  AlbumID}

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

    # Mark albums as downloaded if they have at least 80% (by default,
    # configurable) of the album
    total_track_count = len(newtrackdata)
    have_track_count = len(myDB.select(
        'SELECT * from tracks WHERE AlbumID=? AND Location IS NOT NULL', [AlbumID]))

    if oldalbumdata['Status'] == 'Skipped' and ((have_track_count / float(total_track_count)) >= (headphones.CONFIG.ALBUM_COMPLETION_PCT / 100.0)):
        myDB.action(
            'UPDATE albums SET Status=? WHERE AlbumID=?', ['Downloaded', AlbumID])

    # Update have track counts on index
    totaltracks = len(myDB.select(
        'SELECT TrackTitle from tracks WHERE ArtistID=? AND AlbumID IN (SELECT AlbumID FROM albums WHERE Status != "Ignored")', [newalbumdata['ArtistID']]))
    havetracks = len(myDB.select(
        'SELECT TrackTitle from tracks WHERE ArtistID=? AND Location IS NOT NULL', [newalbumdata['ArtistID']]))

    controlValueDict = {"ArtistID":     newalbumdata['ArtistID']}

    newValueDict = {"TotalTracks":      totaltracks,
                    "HaveTracks":       havetracks}

    myDB.upsert("artists", newValueDict, controlValueDict)
