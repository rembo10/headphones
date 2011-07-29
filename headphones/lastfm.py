import urllib
from xml.dom import minidom
from collections import defaultdict
import random

from headphones import db

api_key = '395e6ec6bb557382fc41fde867bce66f'

  
def getSimilar():
	
	myDB = db.DBConnection()
	results = myDB.select('SELECT ArtistID from artists ORDER BY HaveTracks DESC')
	
	artistlist = []
	
	for result in results[:12]:
		
		url = 'http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&mbid=%s&api_key=%s' % (result['ArtistID'], api_key)
		data = urllib.urlopen(url).read()
		d = minidom.parseString(data)
		node = d.documentElement
		artists = d.getElementsByTagName("artist")
		
		for artist in artists:
			namenode = artist.getElementsByTagName("name")[0].childNodes
			mbidnode = artist.getElementsByTagName("mbid")[0].childNodes
			
			for node in namenode:
				artist_name = node.data
			for node in mbidnode:
				artist_mbid = node.data
				
			if not any(artist_mbid in x for x in results):
				artistlist.append((artist_name, artist_mbid))
	
	count = defaultdict(int)
	
	for artist, mbid in artistlist:
		count[artist, mbid] += 1
		
	items = count.items()
	
	top_list = sorted(items, key=lambda x: x[1], reverse=True)[:25]
	
	random.shuffle(top_list)
	
	myDB.action('''DELETE from lastfmcloud''')
	for tuple in top_list:
		artist_name, artist_mbid = tuple[0]
		count = tuple[1]	
		myDB.action('INSERT INTO lastfmcloud VALUES( ?, ?, ?)', [artist_name, artist_mbid, count])