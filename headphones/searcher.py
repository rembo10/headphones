import urllib, urllib2
import lib.feedparser as feedparser
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, re, time

import headphones
from headphones import logger, db, helpers, classes, sab

class NewzbinDownloader(urllib.FancyURLopener):

    def __init__(self):
        urllib.FancyURLopener.__init__(self)

    def http_error_default(self, url, fp, errcode, errmsg, headers):

        # if newzbin is throttling us, wait seconds and try again
        if errcode == 400:

            newzbinErrCode = int(headers.getheader('X-DNZB-RCode'))

            if newzbinErrCode == 450:
                rtext = str(headers.getheader('X-DNZB-RText'))
                result = re.search("wait (\d+) seconds", rtext)

            elif newzbinErrCode == 401:
                logger.info("Newzbin error 401")
                #raise exceptions.AuthException("Newzbin username or password incorrect")

            elif newzbinErrCode == 402:
                #raise exceptions.AuthException("Newzbin account not premium status, can't download NZBs")
                logger.info("Newzbin error 402")

            logger.info("Newzbin throttled our NZB downloading, pausing for " + result.group(1) + "seconds")

            time.sleep(int(result.group(1)))

            #raise exceptions.NewzbinAPIThrottled()

#this should be in a class somewhere
def getNewzbinURL(url):

    myOpener = classes.AuthURLOpener(headphones.NEWZBIN_UID, headphones.NEWZBIN_PASSWORD)
    try:
        f = myOpener.openit(url)
    except (urllib.ContentTooShortError, IOError), e:
        logger.info("Error loading search results: ContentTooShortError ")
        return None

    data = f.read()
    f.close()

    return data

def searchNZB(albumid=None, new=False):

    myDB = db.DBConnection()
    
    if albumid:
        results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted" AND AlbumID=?', [albumid])
    else:
        results = myDB.select('SELECT ArtistName, AlbumTitle, AlbumID, ReleaseDate from albums WHERE Status="Wanted"')
        new = True
        
    for albums in results:
        
        albumid = albums[2]
        reldate = albums[3]
        
        try:
            year = reldate[:4]
        except TypeError:
            year = ''
        
        dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':''}

        cleanartistalbum = helpers.latinToAscii(helpers.replace_all(albums[0]+' '+albums[1], dic))
        cleanartist = helpers.latinToAscii(helpers.replace_all(albums[0], dic))

        # FLAC usually doesn't have a year for some reason so I'll leave it out:
        term = re.sub('[\.\-\/]', ' ', '%s' % (cleanartistalbum)).encode('utf-8')
        altterm = re.sub('[\.\-\/]', ' ', '%s %s' % (cleanartistalbum, year)).encode('utf-8')
        artistterm = re.sub('[\.\-\/]', ' ', '%s' % (cleanartist)).encode('utf-8')
        
        # Only use the year if the term could return a bunch of different albums, i.e. self-titled albums
        if albums[0] in albums[1] or len(albums[0]) < 4 or len(albums[1]) < 4:
            term = altterm    
        
        logger.info("Searching for %s since it was marked as wanted" % term)
        
        resultlist = []
        
        if headphones.NZBMATRIX:
            provider = "nzbmatrix"
            if headphones.PREFERRED_QUALITY == 3:
                categories = "23"
                maxsize = 10000000000    
            elif headphones.PREFERRED_QUALITY:
                categories = "23,22"
                maxsize = 2000000000
            else:
                categories = "22"
                maxsize = 300000000
            
            
            params = {    "page": "download",
                        "username": headphones.NZBMATRIX_USERNAME,
                        "apikey": headphones.NZBMATRIX_APIKEY,
                        "subcat": categories,
                        "age": headphones.USENET_RETENTION,
                        "english": 1,
                        "ssl": 1,
                        "scenename": 1,
                        "term": term
                        }
                        
            searchURL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)
            logger.info(u'Parsing results from <a href="%s">NZBMatrix</a>' % searchURL)
            try:
            	data = urllib2.urlopen(searchURL, timeout=20).read()
            except urllib2.URLError, e:
            	logger.warn('Error fetching data from NZBMatrix: %s' % e)
            	data = False   
            	
            if data:
            
				d = feedparser.parse(data)
				
				for item in d.entries:
					try:
						url = item.link
						title = item.title
						size = int(item.links[1]['length'])
						if size < maxsize:
							resultlist.append((title, size, url, provider))
							logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
						else:
							logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))    
					
					except AttributeError, e:
						logger.info(u"No results found from NZBMatrix for %s" % term)
            
        if headphones.NEWZNAB:
            provider = "newznab"
            if headphones.PREFERRED_QUALITY == 3:
                categories = "3040"
                maxsize = 10000000000
            elif headphones.PREFERRED_QUALITY:
                categories = "3040,3010"
                maxsize = 2000000000
            else:
                categories = "3010"
                maxsize = 300000000        

            params = {    "t": "search",
                        "apikey": headphones.NEWZNAB_APIKEY,
                        "cat": categories,
                        "maxage": headphones.USENET_RETENTION,
                        "q": term
                        }
        
            searchURL = headphones.NEWZNAB_HOST + '/api?' + urllib.urlencode(params)
                
            logger.info(u'Parsing results from <a href="%s">%s</a>' % (searchURL, headphones.NEWZNAB_HOST))
            
            try:
            	data = urllib2.urlopen(searchURL, timeout=20).read()
            except urllib2.URLError, e:
            	logger.warn('Error fetching data from %s: %s' % (headphones.NEWZNAB_HOST, e))
            	data = False
            	
            if data:
			
				d = feedparser.parse(data)
				
				if not len(d.entries):
					logger.info(u"No results found from %s for %s" % (headphones.NEWZNAB_HOST, term))
					pass
				
				else:
					for item in d.entries:
						try:
							url = item.link
							title = item.title
							size = int(item.links[1]['length'])
							if size < maxsize:
								resultlist.append((title, size, url, provider))
								logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
							else:
								logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))    
						
						except Exception, e:
							logger.error(u"An unknown error occured trying to parse the feed: %s" % e)
                    
        if headphones.NZBSORG:
            provider = "nzbsorg"
            if headphones.PREFERRED_QUALITY == 3:
                categories = "5"
                maxsize = 10000000000
                term = term + ' flac'
            elif headphones.PREFERRED_QUALITY:
                categories = "5"
                maxsize = 2000000000
            else:
                categories = "5"
                maxsize = 300000000        

            params = {    "action": "search",
                        "dl": 1,
                        "catid": categories,
                        "i": headphones.NZBSORG_UID,
                        "h": headphones.NZBSORG_HASH,
                        "age": headphones.USENET_RETENTION,
                        "q": term
                        }
        
            searchURL = 'https://secure.nzbs.org/rss.php?' + urllib.urlencode(params)
            logger.info(u'Parsing results from <a href="%s">%s</a>' % (searchURL, provider))
            
            try:
            	data = urllib2.urlopen(searchURL, timeout=20).read()
            except urllib2.URLError, e:
            	logger.warn('Error fetching data from NZBs.org: %s' % e)
            	data = False
            	items = False
            	
            if data:
				try:    
					d = minidom.parseString(data)
					node = d.documentElement
					items = d.getElementsByTagName("item")
				except ExpatError:
					logger.error('Unable to get the NZBs.org feed. Check that your settings are correct - post a bug if they are')
					items = None
            
            if items:
            
                for item in items:
        
                    sizenode = item.getElementsByTagName("report:size")[0].childNodes
                    titlenode = item.getElementsByTagName("title")[0].childNodes
                    linknode = item.getElementsByTagName("link")[0].childNodes
    
                    for node in sizenode:
                        size = int(node.data)
                    for node in titlenode:
                        title = node.data
                    for node in linknode:
                        url = node.data
    
                    if size < maxsize:
                        resultlist.append((title, size, url, provider))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    else:
                        logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))    
                
            else:
            
                logger.info('No results found from NZBs.org for %s' % term)

        if headphones.NEWZBIN:
            provider = "newzbin"    
            providerurl = "https://www.newzbin.com/"
            if headphones.PREFERRED_QUALITY == 3:
                categories = "7"        #music
                format = "2"             #flac
                maxsize = 10000000000
            elif headphones.PREFERRED_QUALITY:
                categories = "7"        #music
                format = "10"            #mp3+flac
                maxsize = 2000000000
            else:
                categories = "7"        #music
                format = "8"            #mp3
                maxsize = 300000000        

            params = {   
                        "fpn": "p",
                        'u_nfo_posts_only': 0,
						'u_url_posts_only': 0,
						'u_comment_posts_only': 0,
						'u_show_passworded': 0,
                        "searchaction": "Search",
                        #"dl": 1,
                        "category": categories,
                        "retention": headphones.USENET_RETENTION,
                        "ps_rb_audio_format": format,
                        "feed": "rss",
                        "u_post_results_amt": 50,        #this can default to a high number per user
                        "hauth": 1,
                        "q": term
                      }
            searchURL = providerurl + "search/?%s" % urllib.urlencode(params)
            data = getNewzbinURL(searchURL)    
            if data:
                logger.info(u'Parsing results from <a href="%s">%s</a>' % (searchURL, providerurl))
                
                try:    
                    d = minidom.parseString(data)
                    node = d.documentElement
                    items = d.getElementsByTagName("item")
                except ExpatError:
                    logger.info('Unable to get the NEWZBIN feed. Check that your settings are correct - post a bug if they are')
                    items = None
            
            if len(items):
            
                for item in items:
        
                    sizenode = item.getElementsByTagName("report:size")[0].childNodes
                    titlenode = item.getElementsByTagName("title")[0].childNodes
                    linknode = item.getElementsByTagName("link")[0].childNodes
    
                    for node in sizenode:
                        size = int(node.data)
                    for node in titlenode:
                        title = node.data
                    for node in linknode:
                        url = node.data
                        
                        #exract the reportid from the link nodes
                        id_regex = re.escape(providerurl) + 'browse/post/(\d+)/'
                        id_match = re.match(id_regex, url)
                        if not id_match:
                            logger.info("Didn't find a valid Newzbin reportid in linknode")
                        else:
                            url = id_match.group(1) #we have to make a post request later, need the id                            
                    if size < maxsize and url:
                        resultlist.append((title, size, url, provider))
                        logger.info('Found %s. Size: %s' % (title, helpers.bytes_to_mb(size)))
                    else:
                        logger.info('%s is larger than the maxsize for this category, skipping. (Size: %i bytes)' % (title, size))    
                
            else:
                logger.info('No results found from NEWZBIN for %s' % term)

        #attempt to verify that this isn't a substring result
        #when looking for "Foo - Foo" we don't want "Foobar"
        #this should be less of an issue when it isn't a self-titled album so we'll only check vs artist
        if len(resultlist):
            resultlist[:] = [result for result in resultlist if verifyresult(result[0], artistterm)]
        
        if len(resultlist):    
                       
            if headphones.PREFERRED_QUALITY == 2 and headphones.PREFERRED_BITRATE:

                logger.debug('Target bitrate: %s kbps' % headphones.PREFERRED_BITRATE)

                tracks = myDB.select('SELECT TrackDuration from tracks WHERE AlbumID=?', [albumid])

                try:
                    albumlength = sum([pair[0] for pair in tracks])

                    targetsize = albumlength/1000 * int(headphones.PREFERRED_BITRATE) * 128
                    logger.info('Target size: %s' % helpers.bytes_to_mb(targetsize))
    
                    newlist = []

                    for result in resultlist:
                        delta = abs(targetsize - result[1])
                        newlist.append((result[0], result[1], result[2], delta))
        
                    nzblist = sorted(newlist, key=lambda title: title[3])
                
                except Exception, e:
                    
                    logger.debug('Error: %s' % str(e))
                    logger.info('No track information for %s - %s. Defaulting to highest quality' % (albums[0], albums[1]))
                    
                    nzblist = sorted(resultlist, key=lambda title: title[1], reverse=True)
            
            else:
            
                nzblist = sorted(resultlist, key=lambda title: title[1], reverse=True)
            
            
            if new:
                # Checks to see if it's already downloaded
                i = 0
    
                while i < len(nzblist):
                    alreadydownloaded = myDB.select('SELECT * from snatched WHERE URL=?', [nzblist[i][2]])
                    
                    if len(alreadydownloaded) >= 1:
                        logger.info('%s has already been downloaded. Skipping.' % nzblist[i][0])
                        i += 1
                    
                    else:
                        bestqual = nzblist[i]
                        break
                        
                try:
                    x = bestqual[0]
                except UnboundLocalError:
                    logger.info('No more matches for %s' % term)
                    return
                        
            else:
                bestqual = nzblist[0]
            
            logger.info(u'Found best result: <a href="%s">%s</a> - %s' % (bestqual[2], bestqual[0], helpers.bytes_to_mb(bestqual[1])))
            logger.info(u"Pre-processing result")
            (data, bestqual) = preprocess(nzblist)
            if data and bestqual:
                nzb_folder_name = '%s - %s [%s]' % (helpers.latinToAscii(albums[0]).encode('UTF-8').replace('/', '_'), helpers.latinToAscii(albums[1]).encode('UTF-8').replace('/', '_'), year) 
                if headphones.SAB_HOST and not headphones.BLACKHOLE:

                    nzb = classes.NZBDataSearchResult()
                    nzb.extraInfo.append(data)
                    nzb.name = nzb_folder_name
                    sab.sendNZB(nzb)

                elif headphones.BLACKHOLE:
                
                    nzb_name = nzb_folder_name + '.nzb'
                    download_path = os.path.join(headphones.BLACKHOLE_DIR, nzb_name)
                    try:
                        f = open(download_path, 'w')
                        f.write(data)
                        f.close()
                    except Exception, e:
                        logger.error('Couldn\'t write NZB file: %s' % e)
                        break
                        
                myDB.action('UPDATE albums SET status = "Snatched" WHERE AlbumID=?', [albums[2]])
                myDB.action('INSERT INTO snatched VALUES( ?, ?, ?, ?, DATETIME("NOW", "localtime"), ?, ?)', [albums[2], bestqual[0], bestqual[1], bestqual[2], "Snatched", nzb_folder_name])

def verifyresult(title, term):
	
    title = re.sub('[\.\-\/\_]', ' ', title)
	
    if not re.search('^' + re.escape(term), title, re.IGNORECASE):
        logger.info("Removed from results: " + title + " (artist not at string start).")
        return False
    elif re.search(re.escape(term) + '\w', title, re.IGNORECASE | re.UNICODE):
        logger.info("Removed from results: " + title + " (post substring result).")
        return False
    elif re.search('\w' + re.escape(term), title, re.IGNORECASE | re.UNICODE):
        logger.info("Removed from results: " + title + " (pre substring result).")
        return False
    else:
        return True

def getresultNZB(result):
    if result[3] == 'Newzbin':
        params = urllib.urlencode({"username": headphones.NEWZBIN_UID, "password": headphones.NEWZBIN_PASSWORD, "reportid": result[2]})
        url = "https://www.newzbin.com" + "/api/dnzb/"
        urllib._urlopener = NewzbinDownloader()
        try:
            nzb = urllib.urlopen(url, data=params).read()
        except urllib2.URLError, e:
            logger.warn('Error fetching nzb from url: ' + url + ' %s' % e)
    else:
        try:
            nzb = urllib2.urlopen(result[2], timeout=20).read()
        except:
            logger.warn('Error fetching nzb from url: ' + result[2] + ' %s' % e)
    return nzb
    
def preprocess(resultlist):
    for result in resultlist:
        nzb = getresultNZB(result)
        if nzb:
            try:    
                d = minidom.parseString(nzb)
                node = d.documentElement
                nzbfiles = d.getElementsByTagName("file")
                for nzbfile in nzbfiles:
                    if nzbfile.getAttribute("date") < (time.time() - int(headphones.USENET_RETENTION) * 86400):
                        logger.error('NZB contains a file out of your retention. Skipping.')
                        continue
                    #TODO: Do we want rar checking in here to try to keep unknowns out?
                    #or at least the option to do so?
            except ExpatError:
                logger.error('Unable to parse the best result NZB. Skipping.')
                continue
            return nzb, result
        else:
            logger.error("Couldn't retrieve the best nzb. Skipping.")
    return (False, False)
