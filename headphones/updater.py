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

from headphones import logger, db, importer

def dbUpdate(forcefull=False):

	logger.info('Starting update for %i active artists' % len(activeartists))

    myDB = db.DBConnection()

    #This can be updated to NOT include: paused artists, artists with extras enabled, wanted albums, albums matched to specific releases, etc
    #But it absolutely FLIES if these dB's are destroyed in their entirety.  With the new system, there's really no need to pause artists.
    if forcefull==True:
    	myDB.select('DELETE from albums')
    	myDB.select('DELETE from allalbums')
    	myDB.select('DELETE from tracks')
    	myDB.select('DELETE from alltracks')
    	myDB.select('DELETE from descriptions')
    	myDB.select('UPDATE artists SET LatestAlbum=?, ReleaseDate=?, AlbumID=?, HaveTracks=?, TotalTracks=?', [None, None, None, None, None])

    activeartists = myDB.select('SELECT ArtistID, ArtistName from artists WHERE Status="Active" or Status="Loading" order by LastUpdated ASC')
    
    for artist in activeartists:
    
        artistid = artist[0]
        importer.addArtisttoDB(artistid=artistid, extrasonly=False, forcefull=forcefull)
        
    logger.info('Update complete')
