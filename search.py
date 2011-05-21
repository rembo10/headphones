import sys
import musicbrainz2.webservice as ws
import musicbrainz2.model as m

def findArtist(name):

	if len(name) == 0 or name == 'Add an artist':
		return '''<p align="right"><font color="red">Please enter an artist</font></p>'''
		
	q = ws.Query()

	f = ws.ArtistFilter(name, limit=5)
	artistResults = ws.Query().getArtists(ws.ArtistFilter(name, limit=5))
		
	if len(artistResults) > 1:
	
		return '''We found a few different artists. Which one did you want?<br /><br />'''

		for result in artistResults:
			artist = result.artist
			return '''<a href="/addArtist?artistid=%s"> %s </a><br />''' % (artist.id, artist.name)
			
	elif len(artistRestuls) == 1:
		
		return '''Ok, we're going to add %s''' % artist.name
		
	else:

		return '''We couldn't find any artists!'''