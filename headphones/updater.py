import headphones

from headphones import logger, db, mb, importer

def dbUpdate():

	myDB = db.DBConnection()

	activeartists = myDB.select('SELECT ArtistID, ArtistName from artists WHERE Status="Active" or Status="Loading" order by ArtistSortName collate nocase')

	logger.info('Starting update for %i active artists' % len(activeartists))
	
	for artist in activeartists:
	
		artistid = artist[0]
		importer.addArtisttoDB(artistid)
		
	logger.info('Update complete')
		
		

		
			

