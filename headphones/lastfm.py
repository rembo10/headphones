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

import urllib, urllib2
from xml.dom import minidom
from collections import defaultdict
import random
import time

import headphones
from headphones import db, logger

api_key = '395e6ec6bb557382fc41fde867bce66f'

  
def getSimilar():
    
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists ORDER BY HaveTracks DESC')
    
    artistlist = []
    
    for result in results[:12]:
        
        url = 'http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&mbid=%s&api_key=%s' % (result['ArtistID'], api_key)
        
        try:
            data = urllib2.urlopen(url, timeout=20).read()
        except:
            time.sleep(1)
            continue
            
        if not data or len(data) < 200:
            continue
            
        try:    
            d = minidom.parseString(data)
        except:
            logger.debug("Could not parse similar artist data from last.fm")
        
        node = d.documentElement
        artists = d.getElementsByTagName("artist")
        
        for artist in artists:
            namenode = artist.getElementsByTagName("name")[0].childNodes
            mbidnode = artist.getElementsByTagName("mbid")[0].childNodes
            
            for node in namenode:
                artist_name = node.data
            for node in mbidnode:
                artist_mbid = node.data
                
            try:
                if not any(artist_mbid in x for x in results):
                    artistlist.append((artist_name, artist_mbid))
            except:
                continue
                
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
        
def getArtists():

    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    if not headphones.LASTFM_USERNAME:
        return
        
    else:
        username = headphones.LASTFM_USERNAME
        
    url = 'http://ws.audioscrobbler.com/2.0/?method=library.getartists&limit=10000&api_key=%s&user=%s' % (api_key, username)
    data = urllib2.urlopen(url, timeout=20).read()
    
    try:
        d = minidom.parseString(data)
    except:
        logger.error("Could not parse artist list from last.fm data")
        return
    
    artists = d.getElementsByTagName("artist")
    
    artistlist = []
    
    for artist in artists:
        mbidnode = artist.getElementsByTagName("mbid")[0].childNodes

        for node in mbidnode:
            artist_mbid = node.data
                
        try:
            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)
        except:
            continue
    
    from headphones import importer
    
    for artistid in artistlist:
        importer.addArtisttoDB(artistid)
    
def getTagTopArtists(tag, limit=50):
    myDB = db.DBConnection()
    results = myDB.select('SELECT ArtistID from artists')

    url = 'http://ws.audioscrobbler.com/2.0/?method=tag.gettopartists&limit=%s&tag=%s&api_key=%s' % (limit, tag, api_key)
    data = urllib2.urlopen(url, timeout=20).read()

    try:
        d = minidom.parseString(data)
    except:
        logger.error("Could not parse artist list from last.fm data")
        return

    artists = d.getElementsByTagName("artist")

    artistlist = []

    for artist in artists:
        mbidnode = artist.getElementsByTagName("mbid")[0].childNodes

        for node in mbidnode:
            artist_mbid = node.data

        try:
            if not any(artist_mbid in x for x in results):
                artistlist.append(artist_mbid)
        except:
            continue

    from headphones import importer

    for artistid in artistlist:
        importer.addArtisttoDB(artistid)


def getAlbumDescription(rgid, artist, album):
    
    myDB = db.DBConnection()    
    result = myDB.select('SELECT Summary from descriptions WHERE ReleaseGroupID=?', [rgid])
    
    if result:
        return
        
    params = {  "method": 'album.getInfo',
                "api_key": api_key,
                "artist": artist.encode('utf-8'),
                "album": album.encode('utf-8')
            }

    searchURL = 'http://ws.audioscrobbler.com/2.0/?' + urllib.urlencode(params)
    data = urllib2.urlopen(searchURL, timeout=20).read()
    
    if data == '<?xml version="1.0" encoding="utf-8"?><lfm status="failed"><error code="6">Album not found</error></lfm>':
        return
        
    try:
        d = minidom.parseString(data)

        albuminfo = d.getElementsByTagName("album")
        
        for item in albuminfo:
            summarynode = item.getElementsByTagName("summary")[0].childNodes
            contentnode = item.getElementsByTagName("content")[0].childNodes
            for node in summarynode:
                summary = node.data
            for node in contentnode:
                content = node.data
                
        controlValueDict = {'ReleaseGroupID': rgid}
        newValueDict = {'Summary': summary,
                        'Content': content}
        myDB.upsert("descriptions", newValueDict, controlValueDict) 
        
    except:
        return

def getAlbumDescriptionOld(rgid, releaselist):
    """
    This was a dumb way to do it - going to just use artist & album name but keeping this here
    because I may use it to fetch and cache album art
    """

    myDB = db.DBConnection()    
    result = myDB.select('SELECT Summary from descriptions WHERE ReleaseGroupID=?', [rgid])
    
    if result:
        return
    
    for release in releaselist:
        
        mbid = release['releaseid']
        url = 'http://ws.audioscrobbler.com/2.0/?method=album.getInfo&mbid=%s&api_key=%s' % (mbid, api_key)
        data = urllib.urlopen(url).read()
        
        if data == '<?xml version="1.0" encoding="utf-8"?><lfm status="failed"><error code="6">Album not found</error></lfm>':
            continue
        
        try:
            d = minidom.parseString(data)
    
            albuminfo = d.getElementsByTagName("album")
            
            for item in albuminfo:
                summarynode = item.getElementsByTagName("summary")[0].childNodes
                contentnode = item.getElementsByTagName("content")[0].childNodes
                for node in summarynode:
                    summary = node.data
                for node in contentnode:
                    content = node.data
                    
            controlValueDict = {'ReleaseGroupID': rgid}
            newValueDict = {'ReleaseID': mbid,
                            'Summary': summary,
                            'Content': content}
            myDB.upsert("descriptions", newValueDict, controlValueDict) 
            break
        
        except:
            continue
        
    
