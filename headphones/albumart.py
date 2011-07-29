from headphones import db

def getAlbumArt(albumid):

	myDB = db.DBConnection()
	asin = myDB.action('SELECT AlbumASIN from albums WHERE AlbumID=?', [albumid]).fetchone()[0]
	
	url = 'http://ec1.images-amazon.com/images/P/%s.01.LZZZZZZZ.jpg' % asin
	
	return url