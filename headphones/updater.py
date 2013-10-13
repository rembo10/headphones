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

    myDB = db.DBConnection()

    activeartists = myDB.select('SELECT ArtistID, ArtistName from artists WHERE Status="Active" or Status="Loading" order by LastUpdated ASC')
    logger.info('Starting update for %i active artists' % len(activeartists))
    
    for artist in activeartists:
    
        artistid = artist[0]
        importer.addArtisttoDB(artistid=artistid, extrasonly=False, forcefull=forcefull)
        
    logger.info('Active artist update complete')
