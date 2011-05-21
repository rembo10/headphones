import sys
from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError

def findArtist(self, name):

	if len(name) < 2:
		return '''Please enter an artist'''

	q = Query()

	try:
		f = ArtistFilter(name, limit=5)
		artistResults = q.getArtists(f)
	
	except WebServiceError, e:
		print 'Error:', e
		sys.exit(1)

	for result in artistResults:
		artist = result.artist
		return '''
		Score = %s
		Id = %s  
		Name = %s 
		Sort Name = %s
		''' % result.score, artist.id, artist.name, artist.sortName




