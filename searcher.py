import urllib
from webServer import database
from configobj import ConfigObj
import string
import feedparser
import sqlite3
import re

config = ConfigObj('config.ini')
General = config['General']
NZBMatrix = config['NZBMatrix']
SABnzbd = config['SABnzbd']
nzbmatrix = NZBMatrix['nzbmatrix']
nzbmatrix_username = NZBMatrix['nzbmatrix_username']
nzbmatrix_apikey = NZBMatrix['nzbmatrix_apikey']
usenet_retention = General['usenet_retention']
sab_host = SABnzbd['sab_host']
sab_username = SABnzbd['sab_username']
sab_password = SABnzbd['sab_password']
sab_apikey = SABnzbd['sab_apikey']
sab_category = SABnzbd['sab_category']


if General['include_lossless'] == '1':
	categories = "23, 22"
	maxsize = 2000000000
else:
	categories = "22"
	maxsize = 250000000

def searchNZB(albumid=None):
	
	conn=sqlite3.connect(database)
	c=conn.cursor()
	
	if albumid:
		c.execute('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted" AND AlbumID="%s"' % albumid)
	else:
		c.execute('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted"')
	
	results = c.fetchall()
	
	for albums in results:
		
		reldate = albums[3]
		year = reldate[:4]
		clname = string.replace(albums[0], ' & ', ' ')	
		clalbum = string.replace(albums[1], ' & ', ' ')
		term = re.sub('[\.\-]', ' ', '%s %s %s' % (clname, clalbum, year)).encode('utf-8')

		params = {	"page": "download",
					"username": nzbmatrix_username,
					"apikey": nzbmatrix_apikey,
					"subcat": categories,
					"age": usenet_retention,
					"english": 1,
					"ssl": 1,
					"scenename": 1,
					"term": term
					}
					
		searchURL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)
		
		d = feedparser.parse(searchURL)

		
		resultlist = []
		
		for item in d.entries:
			try:
				url = item.link
				title = item.title
				size = int(item.links[1]['length'])
				if size < maxsize:
					resultlist.append((title, size, url))
			
			except:
				print '''No results found'''
			
			bestqual = sorted(resultlist, key=lambda title: title[1], reverse=True)[0]
	
			downloadurl = bestqual[2]
			
			linkparams = {	"mode": "addurl",
							"apikey": sab_apikey,
							"ma_username": sab_username,
							"ma_password": sab_password,
							"cat": sab_category,
							"name": downloadurl
						}
			
			saburl = 'http://' + sab_host + '/sabnzbd/api?' + urllib.urlencode(linkparams)
	
			urllib.urlopen(saburl)
			
			c.execute('UPDATE albums SET status = "Snatched" WHERE AlbumID="%s"' % albums[2])
			conn.commit()

	c.close()
		
		


	