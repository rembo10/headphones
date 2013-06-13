from xml.dom.minidom import parseString
from xml.dom.minidom import Node
import urllib
import urllib2
import cookielib
from headphones import logger
import os
import headphones
from datetime import datetime
import re

class gks():

    def __init__(self):
        
                
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        
        self.url = "https://gks.gs/"
        
        self.login_done = False
        
    def searchurl(self, artist, album, year, format):
        
        """
        Return the search url
        """
         
        # Build search url
        
        searchterm = ''
        if artist != 'Various Artists':
            searchterm = artist
        searchterm = searchterm +'-'+ album
        
        
        searchString = urllib.urlencode( {'q': searchterm, 'category' : 39, 'ak' : headphones.GKS_KEY} ) + "&order=desc&sort=normal&exact"
         
        searchurl = self.url+'rdirect.php?type=search&'+searchString
              
        
        return searchurl 
    
    def search(self, searchurl, maxsize, minseeders, albumid, bitrate):
        
            searchUrl = searchurl
            results = []
            request = urllib2.Request(searchUrl)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31')  
            opener = urllib2.build_opener()
            data = opener.open(request).read()
            if "bad key" in str(data).lower() :
                logger.error(u"GKS key invalid, check your config")
                return
    
            parsedXML = parseString(data)
            channel = parsedXML.getElementsByTagName('channel')[0]
            description = channel.getElementsByTagName('description')[0]
            #description_text = self.get_xml_text(description).lower()
            text = ""
            for child_node in description.childNodes:
                if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                    text += child_node.data
            description_text=text.strip().lower()
            
            if "user can't be found" in description_text:
                logger.error(u"GKS invalid digest, check your config")
                return
            elif "invalid hash" in description_text:
                logger.error(u"GKS invalid hash, check your config")
                return
            else :
                items = channel.getElementsByTagName('item')
                for item in items:
                    text = ""
                    for child_node in item.getElementsByTagName('title')[0].childNodes:
                        if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                            text += child_node.data
                    title=text.strip().lower()
                                        
                    if "aucun resultat" in title.lower() :
                        logger.debug("No results found trying another if there is one")
                        return
                    else :
                        text = ""
                        for child_node in item.getElementsByTagName('link')[0].childNodes:
                            if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                                text += child_node.data
                        downloadURL=text.strip().lower()
                        desc=""
                        for child_node in item.getElementsByTagName('description')[0].childNodes:
                            if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                                desc += child_node.data
                        desc=desc.strip().lower()
                        desc_values=desc.split(" | ")
                        dict_attr={}
                        for x in desc_values:
                            x_values=x.split(" : ")
                            dict_attr[x_values[0]]=x_values[1]
                        size=""
                        seeders=""
                        if "taille" in dict_attr:
                            size=dict_attr["taille"]
                        if "seeders" in dict_attr:
                            seeders=dict_attr["seeders"]
                                                                           
                        size = parseSize(size)
                        size= tryInt(size)
                        seeders = tryInt(seeders)
                        
                        results.append( GKSSearchResult( self.opener, title, downloadURL, size, seeders ) )
                    
            return results  
    
    def get_torrent(self, url, savelocation,torrent_name):
    
                          
        torrent_name = torrent_name + '.torrent'
        download_path = os.path.join(savelocation, torrent_name)
        
        try:
            page = self.opener.open(url)
            torrent = page.read()
            fp = open (download_path, 'wb')
            fp.write (torrent)
            fp.close ()                        
            os.chmod(download_path, 0777)
        except Exception, e:
            logger.error('Error getting torrent: %s' % e)  
            return False      
        
        return download_path
    
    
def parseSize(size):
        
        sizeGb = ['gb', 'gib', 'go']
        sizeMb = ['mb', 'mib', 'mo']
        sizeKb = ['kb', 'kib', 'ko']
        
        sizeRaw = size.lower()
        size = tryFloat(re.sub(r'[^0-9.]', '', size).strip())

        for s in sizeGb:
            if s in sizeRaw:
                return size * 1024 * 1048576

        for s in sizeMb:
            if s in sizeRaw:
                return size * 1048576

        for s in sizeKb:
            if s in sizeRaw:
                return size /1024 *1048576

        return
def tryInt(s):
    try: return int(s)
    except: return 0

def tryFloat(s):
    try: return float(s) if '.' in s else tryInt(s)
    except: return 0
    
class GKSSearchResult:
    
    def __init__(self, opener, title, url, size, seeders):
        self.opener = opener
        self.title = title
        self.url = url
        self.size = size
        self.seeders = seeders
        
    def getNZB(self):
        return self.opener.open( self.url , 'wb').read()
    
    
provider = gks()