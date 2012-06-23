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

import os
import glob, urllib, urllib2

import lib.simplejson as simplejson

import headphones
from headphones import db, helpers, logger

lastfm_apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4"

class Cache(object):
    """
    This class deals with getting, storing and serving up artwork (album 
    art, artist images, etc) and info/descriptions (album info, artist descrptions)
    to and from the cache folder. This can be called from within a web interface, 
    for example, using the helper functions getInfo(id) and getArtwork(id), to utilize the cached
    images rather than having to retrieve them every time the page is reloaded.
    
    So you can call cache.getArtwork(id) which will return an absolute path
    to the image file on the local machine, or if the cache directory
    doesn't exist, or can not be written to, it will return a url to the image.
    
    Call cache.getInfo(id) to grab the artist/album info; will return the text description
    
    The basic format for art in the cache is <musicbrainzid>.<date>.<ext>
    and for info it is <musicbrainzid>.<date>.txt
    """
    
    path_to_art_cache = os.path.join(headphones.CACHE_DIR, 'artwork')
    path_to_info_cache = os.path.join(headphones.CACHE_DIR, 'info')
    
    id = None
    id_type = None # 'artist' or 'album' - set automatically depending on whether ArtistID or AlbumID is passed
    query_type = None # 'artwork' or 'info' - set automatically
    
    artwork_files = []
    info_files = []
    
    artwork_errors = False
    artwork_url = None
    
    thumb_errors = False
    thumb_url = None
    
    info_errors = False
    info = None
    
    def __init__(self):
        
        pass
        
    def _exists(self, type):

        self.artwork_files = glob.glob(os.path.join(self.path_to_art_cache, self.id + '*'))
        self.thumb_files = glob.glob(os.path.join(self.path_to_art_cache, 'T_' + self.id + '*'))
        self.info_files = glob.glob(os.path.join(self.path_to_info_cache, self.id + '*'))

        if type == 'artwork':

            if self.artwork_files:
                return True
            else:
                return False
                
        elif type == 'thumb':
            
            if self.thumb_files:
                return True
            else:
                return False

        else:
            
            if self.info_files:
                return True
            else:
                return False

    def _get_age(self, date):
        # There's probably a better way to do this
        split_date = date.split('-')
        days_old = int(split_date[0])*365 + int(split_date[1])*30 + int(split_date[2])
        
        return days_old
        
    
    def _is_current(self, file):
        
        base_filename = os.path.basename(file)
        date = base_filename.split('.')[1]
        
        # Calculate how old the cached file is based on todays date & file date stamp
        # helpers.today() returns todays date in yyyy-mm-dd format
        if self._get_age(helpers.today()) - self._get_age(date) < 30:
            return True
        else:
            return False
            
    def _get_thumb_url(self, data):
        
        thumb_url = None
        
        try:
            images = data[self.id_type]['image']
        except KeyError:
            return None
        
        for image in images:
            if image['size'] == 'medium':
                thumb_url = image['#text']
                break
                
        return thumb_url
        
    def get_artwork_from_cache(self, ArtistID=None, AlbumID=None):
        '''
        Pass a musicbrainz id to this function (either ArtistID or AlbumID)
        '''
        
        self.query_type = 'artwork'
        
        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'
        
        if self._exists('artwork') and self._is_current(self.artwork_files[0]):
            return self.artwork_files[0]
        else:
            self._update_cache()
            # If we failed to get artwork, either return the url or the older file
            if self.artwork_errors and self.artwork_url:
                return self.artwork_url
            elif self._exists('artwork'):
                return self.artwork_files[0]
            else:
                return None
                
    def get_thumb_from_cache(self, ArtistID=None, AlbumID=None):
        '''
        Pass a musicbrainz id to this function (either ArtistID or AlbumID)
        '''
        
        self.query_type = 'thumb'
        
        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'
        
        if self._exists('thumb') and self._is_current(self.thumb_files[0]):
            return self.thumb_files[0]
        else:
            self._update_cache()
            # If we failed to get artwork, either return the url or the older file
            if self.thumb_errors and self.thumb_url:
                return self.thumb_url
            elif self._exists('thumb'):
                return self.thumb_files[0]
            else:
                return None
                
    def get_info_from_cache(self, ArtistID=None, AlbumID=None):
        
        self.query_type = 'info'
        
        if ArtistID:    
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'
        
        if self._exists('info') and self._is_current(self.info_files[0]):
            f = open(self.info_files[0], 'r').read()
            return f.decode('utf-8')
        else:
            self._update_cache()
            
            if self.info_errors and self.info:
                return self.info
            
            elif self._exists('info'):
                f = open(self.info_files[0],'r').read()
                return f.decode('utf-8')
                
            else:
                return None

    def _update_cache(self):
        '''
        Since we call the same url for both info and artwork, we'll update both at the same time
        '''
        
        # Since lastfm uses release ids rather than release group ids for albums, we have to do a artist + album search for albums
        if self.id_type == 'artist':
            
            params = {  "method": "artist.getInfo",
                        "api_key": lastfm_apikey,
                        "mbid": self.id,
                        "format": "json"
                        }
            
            url = "http://ws.audioscrobbler.com/2.0/?" + urllib.urlencode(params)
            logger.debug('Retrieving artist information from: ' + url)
            
            try:
                result = urllib2.urlopen(url).read()
            except:
                logger.warn('Could not open url: ' + url)
                return
            
            if result:    
            
                try:
                    data = simplejson.JSONDecoder().decode(result)
                except:
                    logger.warn('Could not parse data from url: ' + url)
                    return
                try:
                    info = data['artist']['bio']['summary']
                except KeyError:
                    logger.debug('No artist bio summary found on url: ' + url)
                    info = None
                try:
                    info_full = data['artist']['bio']['content']
                except KeyError:
                    logger.debug('No artist bio found on url: ' + url)
                    info_full = None
                try:
                    image_url = data['artist']['image'][-1]['#text']
                except KeyError:
                    logger.debug('No artist image found on url: ' + url)
                    image_url = None
                
                thumb_url = self._get_thumb_url(data)
                if not thumb_url:
                    logger.debug('No artist thumbnail image found on url: ' + url)
        
        else:
            myDB = db.DBConnection()
            dbartist = myDB.action('SELECT ArtistName, AlbumTitle FROM albums WHERE AlbumID=?', [self.id]).fetchone()
            
            params = {  "method": "album.getInfo",
                        "api_key": lastfm_apikey,
                        "artist": dbartist['ArtistName'].encode('utf-8'),
                        "album": dbartist['AlbumTitle'].encode('utf-8'),
                        "format": "json"
                        }
                        
            url = "http://ws.audioscrobbler.com/2.0/?" + urllib.urlencode(params)
        
            logger.debug('Retrieving artist information from: ' + url)
            try:
                result = urllib2.urlopen(url).read()
            except:
                logger.warn('Could not open url: ' + url)
                return
                
            if result:
                try:    
                    data = simplejson.JSONDecoder().decode(result)
                except:
                    logger.warn('Could not parse data from url: ' + url)
                    return
                try:    
                    info = data['album']['wiki']['summary']
                except KeyError:
                    logger.debug('No album summary found from: ' + url)
                    info = None
                try:    
                    info_full = data['album']['wiki']['content']
                except KeyError:
                    logger.debug('No album infomation found from: ' + url)
                    info_full = None
                try:
                    image_url = data['album']['image'][-1]['#text']
                except KeyError:
                    logger.debug('No album image link found on url: ' + url)
                    image_url = None
                
                thumb_url = self._get_thumb_url(data)
                if not thumb_url:
                    logger.debug('No album thumbnail image found on url: ' + url)
                    
        #Save the content & summary to the database no matter what if we've opened up the url
        if info or info_full:
            
            myDB = db.DBConnection()
            
            if self.id_type == 'artist':
                myDB.action('UPDATE descriptions SET Summary=?, Content=? WHERE ArtistID=?', [info, info_full, self.id])
            else:
                myDB.action('UPDATE descriptions SET Summary=?, Content=? WHERE ReleaseGroupID=?', [info, info_full, self.id])
        
        # Save the info no matter what the query type if it's outdated/missing (maybe it's redundant to save
        # the info files since we're already saving them to the database??? Especially since the DB has summary & content
        if info and not (self.info_files and self._is_current(self.info_files[0])):

            # Make sure the info dir exists:
            if not os.path.isdir(self.path_to_info_cache):
                try:
                    os.makedirs(self.path_to_info_cache)
                except Exception, e:
                    logger.error('Unable to create info cache dir. Error: ' + str(e))
                    self.info_errors = True
                    self.info = info
                    
            # Delete any old files and replace it with a new one
            for info_file in self.info_files:
                try:
                    os.remove(info_file)
                except:
                    logger.error('Error deleting file from the cache: ' + info_file)
                    
            info_file_path = os.path.join(self.path_to_info_cache, self.id + '.' + helpers.today() + '.txt')
            try:    
                f = open(info_file_path, 'w')
                f.write(info.encode('utf-8'))
                f.close()
            except Exception, e:
                logger.error('Unable to write to the cache dir: ' + str(e))
                self.info_errors = True
                self.info = info
        
        # If there is no info, we should either write an empty file, or make an older file current
        # just so it doesn't check it every time        
        elif not info and not (self.info_files and self._is_current(self.info_files[0])):
            
            # Make sure the info dir exists:
            if not os.path.isdir(self.path_to_info_cache):
                try:
                    os.makedirs(self.path_to_info_cache)
                except Exception, e:
                    logger.error('Unable to create info cache dir. Error: ' + str(e))
                    self.info_errors = True
                    self.info = info
            
            new_info_file_path = os.path.join(self.path_to_info_cache, self.id + '.' + helpers.today() + '.txt')
            
            if len(self.info_files) == 1:
                try:
                    os.rename(self.info_files[0], new_info_file_path)
                except Exception, e:
                    logger.warn('Error renaming cached info file: ' + str(e))
            
            elif len(self.info_files) > 1:
                for info_file in self.info_files[1:]:
                    try:
                        os.remove(info_file)
                    except Exception, e:
                        logger.warn('Error removing cached info file "' + info_file + '". Error: ' + str(e))
                        
                try:
                    os.rename(self.info_files[0], new_info_file_path)
                except Exception, e:
                    logger.warn('Error renaming cached info file: ' + str(e))
                        
            else:
                f = open(new_info_file_path, 'w')
                f.close()
        
        # Should we grab the artwork here if we're just grabbing thumbs or info?? Probably not since the files can be quite big
        if image_url and self.query_type == 'artwork':

            myDB = db.DBConnection()
            
            if self.id_type == 'artist':
                myDB.action('UPDATE artists SET ArtworkURL=? WHERE ArtistID=?', [image_url, self.id])
            else:
                myDB.action('UPDATE albums SET ArtworkURL=? WHERE AlbumID=?', [image_url, self.id])
            
            try:
                artwork = urllib2.urlopen(image_url).read()
            except Exception, e:
                logger.error('Unable to open url "' + image_url + '". Error: ' + str(e))
                artwork = None
                
            if artwork:
                
                # Make sure the artwork dir exists:
                if not os.path.isdir(self.path_to_art_cache):
                    try:
                        os.makedirs(self.path_to_art_cache)
                    except Exception, e:
                        logger.error('Unable to create artwork cache dir. Error: ' + str(e))
                        self.artwork_errors = True
                        self.artwork_url = image_url
                        
                #Delete the old stuff
                for artwork_file in self.artwork_files:
                    try:
                        os.remove(artwork_file)
                    except:
                        logger.error('Error deleting file from the cache: ' + artwork_file)
                        
                ext = os.path.splitext(image_url)[1]
                        
                artwork_path = os.path.join(self.path_to_art_cache, self.id + '.' + helpers.today() + ext)
                try:
                    f = open(artwork_path, 'wb')
                    f.write(artwork)
                    f.close()
                except Exception, e:
                    logger.error('Unable to write to the cache dir: ' + str(e))
                    self.artwork_errors = True
                    self.artwork_url = image_url
                    
        # Grab the thumbnail as well if we're getting the full artwork (as long as it's missing/outdated
        if thumb_url and self.query_type in ['thumb','artwork'] and not (self.thumb_files and self._is_current(self.thumb_files[0])):
            
            myDB = db.DBConnection()
            
            if self.id_type == 'artist':
                myDB.action('UPDATE artists SET ThumbURL=? WHERE ArtistID=?', [thumb_url, self.id])
            else:
                myDB.action('UPDATE albums SET ThumbURL=? WHERE AlbumID=?', [thumb_url, self.id])
            
            try:
                artwork = urllib2.urlopen(thumb_url).read()
            except Exception, e:
                logger.error('Unable to open url "' + thumb_url + '". Error: ' + str(e))
                artwork = None
                
            if artwork:
                
                # Make sure the artwork dir exists:
                if not os.path.isdir(self.path_to_art_cache):
                    try:
                        os.makedirs(self.path_to_art_cache)
                    except Exception, e:
                        logger.error('Unable to create artwork cache dir. Error: ' + str(e))
                        self.thumb_errors = True
                        self.thumb_url = thumb_url
                        
                #Delete the old stuff
                for thumb_file in self.thumb_files:
                    try:
                        os.remove(thumb_file)
                    except:
                        logger.error('Error deleting file from the cache: ' + thumb_file)
                        
                ext = os.path.splitext(image_url)[1]
                        
                thumb_path = os.path.join(self.path_to_art_cache, 'T_' + self.id + '.' + helpers.today() + ext)
                try:
                    f = open(thumb_path, 'wb')
                    f.write(artwork)
                    f.close()
                except Exception, e:
                    logger.error('Unable to write to the cache dir: ' + str(e))
                    self.thumb_errors = True
                    self.thumb_url = image_url

def getArtwork(ArtistID=None, AlbumID=None):
    
    c = Cache()
    artwork_path = c.get_artwork_from_cache(ArtistID, AlbumID)
    
    if not artwork_path:
        return None
    
    if artwork_path.startswith('http://'):
        return artwork_path
    else:
        return "cache" + artwork_path[len(headphones.CACHE_DIR):]
        
def getThumb(ArtistID=None, AlbumID=None):
    
    c = Cache()
    artwork_path = c.get_thumb_from_cache(ArtistID, AlbumID)
    
    if not artwork_path:
        return None
    
    if artwork_path.startswith('http://'):
        return artwork_path
    else:
        return "cache" + artwork_path[len(headphones.CACHE_DIR):]
    
def getInfo(ArtistID=None, AlbumID=None):
    
    c = Cache()
    info = c.get_info_from_cache(ArtistID, AlbumID)
    
    if not info:
        return None
        
    return info
