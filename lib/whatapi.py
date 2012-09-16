# -*- coding: utf_8 -*-
#################################################################################
#
# Name: whatapi.py
#
# Synopsis: Module to manage what.cd as a web service
#
# Description: See below list of the implemented webservices
#
# Copyright 2010 devilcius
#
#                          The Wide Open License (WOL)
#
# Permission to use, copy, modify, distribute and sell this software and its
# documentation for any purpose is hereby granted without fee, provided that
# the above copyright notice and this license appear in all source copies.
# THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED WARRANTY OF
# ANY KIND. See http://www.dspguru.com/wide-open-license for more information.
#
#################################################################################


__author__ = "devilcius"
__date__ = "$Oct 23, 2010 11:21:12 PM$"


import hashlib
try:
    from BeautifulSoup import BeautifulSoup, SoupStrainer
except:
    raise ImportError, "Please install BeautifulSoup 3.2 module from http://www.crummy.com/software/BeautifulSoup/#Download"
import httplib
import os
import pickle
import re
import urllib
import shelve
import tempfile
import threading
from htmlentitydefs import name2codepoint as n2cp


"""
A list of the implemented webservices (from what.cd )
=====================================

# User

    * user.getUserId
    * user.getInfo

    * user.getTorrentsSeeding
    * user.getTorrentsSnatched
    * user.getTorrentsUploaded
    * user.getTorrentsCommented

    * user.specificUserInfo
        Atributes:
        ######## stats ###########
        -joindate
        -lastseen
        -dataup
        -datadown
        -ratio
        -rratio
        ######## percentile ###########
        -uppercentile
        -downpercentile
        -torrentsuppercentile
        -reqfilledpercentile
        -bountyspentpercentile
        -postsmadepercentile
        -artistsaddedpercentile
        -overallpercentile
        ######## community ###########
        -postsmade
        -torrentscomments
        -collagesstarted
        -collagescontr
        -reqfilled
        -reqvoted
        -uploaded
        -unique
        -perfect
        -seeding
        -leeching
        -snatched
        -invited
        -artistsadded


# Artist

    * artist.getArtistReleases
    * artist.getArtistImage
    * artist.getArtistInfo
    * artist.getArtistTags
    * artist.getArtistSimilar
    * artist.getArtistRequests

    + artist.setArtistInfo


# Torrent

    * torrent.getTorrentParentId
    * torrent.getTorrentDownloadURL
    * torrent.getTorrentDetails
    * torrent.getTorrentSize
    * torrent.getTorrentSnatched
    * torrent.getTorrentSeeders
    * torrent.getTorrentLeechers
    * torrent.getTorrentUploadedBy
    * torrent.getTorrentFolderName
    * torrent.getTorrentFileList
    * torrent.getTorrentDescription
    * torrent.getTorrentComments
    * torrent.isTorrentFreeLeech
    * torrent.isTorrentReported


# Authenticate

    * authenticate.getAuthenticatedUserId
    * authenticate.getAuthenticatedUserAuthCode
    * authenticate.getAuthenticatedUserDownload
    * authenticate.getAuthenticatedUserUpload()
    * authenticate.getAuthenticatedUserRatio
    * authenticate.getAuthenticatedUserRequiredRatio

"""

class ResponseBody:
    """A Response Body Object"""
    pass

class SpecificInformation:
    """A Specific Information Object"""
    pass


class WhatBase(object):
    """An abstract webservices object."""
    whatcd = None

    def __init__(self, whatcd):
        self.whatcd = whatcd
        #if we are not autenticated in what.cd, do it now
        if not self.whatcd.isAuthenticated():
            print "authenticating..."
            self.whatcd.headers = Authenticate(self.whatcd).getAuthenticatedHeader()

    def _request(self, type, path, data, headers):
        return Request(self.whatcd, type, path, data, headers)

    def _parser(self):
        return Parser(self.whatcd)

    def utils(self):
        return Utils()


class Utils():

    def md5(self, text):
        """Returns the md5 hash of a string."""

        h = hashlib.md5()
        h.update(self._string(text))

        return h.hexdigest()

    def _unicode(self, text):
        if type(text) == unicode:
            return text

        if type(text) == int:
            return unicode(text)

        return unicode(text, "utf-8")

    def _string(self, text):
        if type(text) == str:
            return text

        if type(text) == int:
            return str(text)

        return text.encode("utf-8")

    def _number(self, string):
        """
            Extracts an int from a string. Returns a 0 if None or an empty string was passed
        """

        if not string:
            return 0
        elif string == "":
            return 0
        else:
            try:
                return int(string)
            except ValueError:
                return float(string)

    def substituteEntity(self, match):
        ent = match.group(2)
        if match.group(1) == "#":
            return unichr(int(ent))
        else:
            cp = n2cp.get(ent)

            if cp:
                return unichr(cp)
            else:
                return match.group()

    def decodeHTMLEntities(self, string):
        entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
        return entity_re.subn(self.substituteEntity, string)[0]



class WhatCD(object):

    def __init__(self, username, password, site, loginpage, headers):

        #credentials
        self.username = username
        self.password = password
        self.site = site
        self.loginpage = loginpage
        self.headers = headers
        self.authenticateduserinfo = {}

        self.cache_backend = None
        self.proxy_enabled = False
        self.proxy = None

    def isAuthenticated(self):
        """
                Checks if we are authenticated in what.cd
            """
        if "id" in self.authenticateduserinfo:
            return True
        else:
            return False

    def getCredentials(self):
        """
                Returns an authenticated user credentials object
            """
        return Authenticate(self)


    def getUser(self, username):
        """
                Returns an user object
            """
        return User(username, self)

    def getTorrent(self, id, page=1):
        """
                Returns a torrent object
            """
        return Torrent(id, page, None, self)

    def getTorrentGroup(self, id, page=1):
        """
                Returns a torrent object
            """
        return Torrent(id, page, True, self)

    def getArtist(self, name):
        """
                Returns an artist object
            """
        return Artist(name, self)

    def enableProxy(self, host, port):
        """Enable a default web proxy"""
        self.proxy = [host, Utils()._number(port)]
        self.proxy_enabled = True

    def disableProxy(self):
        """Disable using the web proxy"""
        self.proxy_enabled = False

    def isProxyEnabled(self):
        """Returns True if a web proxy is enabled."""
        return self.proxy_enabled

    def getProxy(self):
        """Returns proxy details."""
        return self.proxy

    def enableCaching(self, file_path=None):
        """Enables caching request-wide for all cachable calls.
            * file_path: A file path for the backend storage file. If
            None set, a temp file would probably be created, according the backend.
            """
        if not file_path:
            file_path = tempfile.mktemp(prefix="whatapi_tmp_")

        self.cache_backend = _ShelfCacheBackend(file_path)

    def disableCaching(self):
        """Disables all caching features."""
        self.cache_backend = None

    def isCachingEnabled(self):
        """Returns True if caching is enabled."""

        return not (self.cache_backend == None)

    def getCacheBackend(self):

        return self.cache_backend

def getWhatcdNetwork(username="", password=""):
    """
    Returns a preconfigured WhatCD object for what.cd
    # Parameters:
        * username str: a username of a valid what.cd user
        * password str: user's password
    """

    return WhatCD (
        username=username,
        password=password,
        site="ssl.what.cd",
        loginpage="/login.php",
        headers={
            "Content-type": "application/x-www-form-urlencoded",
            'Accept-Charset': 'utf-8',
            'User-Agent': "whatapi [devilcius]"
        })



class _ShelfCacheBackend(object):
    """Used as a backend for caching cacheable requests."""
    cache_lock = threading.Lock()

    def __init__(self, file_path=None):
        self.shelf = shelve.open(file_path)

    def getHTML(self, key):
        with _ShelfCacheBackend.cache_lock:
            return self.shelf[key]

    def setHTML(self, key, xml_string):
        with _ShelfCacheBackend.cache_lock:
            self.shelf[key] = xml_string

    def hasKey(self, key):
        with _ShelfCacheBackend.cache_lock:
            return key in self.shelf.keys()


class Request(object):
    """web service operation."""

    def __init__(self, whatcd, type, path, data, headers):

        self.whatcd = whatcd
        self.utils = Utils()
        self.type = type
        self.path = path
        self.data = data
        self.headers = headers
        #enable catching?
        if whatcd.isCachingEnabled():
            self.cache = whatcd.getCacheBackend()

    def getCacheKey(self):
        """The cache key is a md5 hash of request params."""

        key = self.type + self.path + self.data
        return Utils().md5(key)

    def getCachedResponse(self):
        """Returns a file object of the cached response."""

        if not self.isCached():
            response = self.downloadResponse()
            self.cache.setHTML(self.getCacheKey(), response)
        return self.cache.getHTML(self.getCacheKey())

    def isCached(self):
        """Returns True if the request is already in cache."""

        return self.cache.hasKey(self.getCacheKey())

    def downloadResponse(self):
        """Returns a ResponseBody object from the server."""

        #print "downloading from %s" % (self.path)
        conn = httplib.HTTPSConnection(self.whatcd.site)
        rb = ResponseBody()

        if self.whatcd.isProxyEnabled():
            conn = httplib.HTTPSConnection(host=self.whatcd.getProxy()[0], port=self.whatcd.getProxy()[1])
            conn.request(method=self.type, url="https://" + self.whatcd.site + self.path, body=self.data, headers=self.headers)
        else:
            conn.request(self.type, self.path, self.data, self.headers)

        response = conn.getresponse()
        rb.headers = response.getheaders()
        # Rip all inline JavaScript out of the response in case it hasn't been properly escaped
        rb.body = re.sub('<script type="text/javascript">[^<]+</script>', '', response.read())
        conn.close()
        return rb

    def execute(self, cacheable=False):
        """Depending if caching is enabled, returns response from the server or, if available, the cached response"""
        if self.whatcd.isCachingEnabled() and cacheable:
            response = self.getCachedResponse()
        else:
            response = self.downloadResponse()

        return response

class Authenticate(WhatBase):

    def __init__(self, whatcd):
        """Create an authenticated user object.
        # Parameters:
            * whatcd object: WhatCD object.
        """
        self.whatcd = whatcd
        self.parser = Parser(whatcd)
        if not self.whatcd.isAuthenticated():
            self.getAuthenticatedHeader()

    def setCookie(self):
        print "creating cookie"
        f = open('cookie', 'w')
        loginform = {'username': self.whatcd.username, 'password': self.whatcd.password\
            , 'keeplogged': '1', 'login': 'Login'}
        data = urllib.urlencode(loginform)
        response = self._request("POST", self.whatcd.loginpage, data, self.whatcd.headers).execute(True)
        try:
            cookie = dict(response.headers)['set-cookie']
            session = re.search("session=[^;]+", cookie).group(0)
            self.whatcd.headers["Cookie"] = session
            homepage = response.body
            pickle.dump(self.whatcd.headers, f)
        except (KeyError, AttributeError):
            f.close()
            os.remove('cookie')
            self.whatcd.headers = None
            raise Exception("Login failed, most likely bad creds or the site is down, nothing to do")
        f.close()


    def getAuthenticatedHeader(self):
        """
            Log user in what.cd and returns the authenticated header
        """
        homepage = None
        if os.path.exists("cookie"):
            f = open("cookie", "r")
            try:
                self.whatcd.headers = pickle.load(f)
            except EOFError:
                f.close()
                os.remove("cookie")
                print "invalid cookie, removed"
                self.setCookie()
        else:
            self.setCookie()
            #set authenticated user info
        if 'id' not in self.whatcd.authenticateduserinfo:
            self.whatcd.authenticateduserinfo = self.getAuthenticatedUserInfo(homepage)

        return self.whatcd.headers

    def getAuthenticatedUserInfo(self, homepage=None):
        """
            Returns authenticated user's info
        """
        if not homepage:
            homepage = BeautifulSoup(self._request("GET", "/index.php", "", self.whatcd.headers).execute(True).body)
        authuserinfo = self._parser().authenticatedUserInfo(homepage.find("div", {"id": "userinfo"}))
        return authuserinfo

    def getAuthenticatedUserId(self):
        """
            Returns authenticated user's id
        """
        return self.whatcd.authenticateduserinfo["id"]

    def getAuthenticatedUserAuthCode(self):
        """
            Returns authenticated user's authcode
        """
        return self.whatcd.authenticateduserinfo["authcode"]


    def getAuthenticatedUserUpload(self):
        """
            Returns authenticated user's total uploaded data
        """
        return self.whatcd.authenticateduserinfo["uploaded"]


    def getAuthenticatedUserDownload(self):
        """
            Returns authenticated user's total downloaded data
        """
        return self.whatcd.authenticateduserinfo["downloaded"]


    def getAuthenticatedUserRatio(self):
        """
            Returns authenticated user's ratio
        """
        return self.whatcd.authenticateduserinfo["ratio"]

    def getAuthenticatedUserRequiredRatio(self):
        """
            Returns authenticated user's required ratio
        """
        return self.whatcd.authenticateduserinfo["required"]


class User(WhatBase):
    """A What.CD user"""

    def __init__(self, username, whatcd):
        """Create an user object.
        # Parameters:
            * username str: The user's name.
            - whatcd object: the what.cd network object
        """
        WhatBase.__init__(self, whatcd)
        self.name = username
        self.whatcd = whatcd
        self.userpage = "/user.php?"
        self.userid = None
        self.userinfo = None

    def getUserName(self):
        """
            Returns user's name
        """
        return self.username

    def getUserId(self):
        """
            Returns user's id, None if user doesn't exists
        """
        if self.userid:
            return self.userid
        else:
            idform = {'action': "search", 'search': self.name}
            data = urllib.urlencode(idform)
            headers = self._request("GET", self.userpage + data, "", self.whatcd.headers).execute(True).headers
            if dict(headers) is None:
                return None
            else:
                self.userid = dict(headers)['location'][12:]
                return self.userid

    def getInfo(self):
        """
            Returns a dictionary of {percentile:{dataup str,
                                                 datadown str,
                                                 overall str,
                                                 postmade str,
                                                 boutyspent str,
                                                 reqfilled str,
                                                 artistsadded str,
                                                 torrentsup str},
                                     stats: {uploaded str,
                                             ratio str,
                                             joined str,
                                             downloaded str,
                                             lastseen str,
                                             rratio str},
                                     community: {uploaded tuple(total str, url str),
                                                 forumposts tuple(total str, url str),
                                                 invited tuple (total,None),
                                                 perfectflacs tuple(total str, url str),
                                                 contributedcollages tuple(total str, url str),
                                                 reqvoted tuple(total str, url str),
                                                 uniquegroups tuple(total str, url str)
                                                 torrentscomments tuple(total str, url str),
                                                 snatched tuple(total str, url str),
                                                 artists str,
                                                 reqfilled tuple(total str, url str),
                                                 startedcollages tuple(total str, url str),
                                                 leeching tuple(total str, url str),
                                                 seeding tuple(total str, url str)}
                                                }
            If paranoia is not Off, it returns None.
        """
        if self.getUserId():
            form = {'id': self.getUserId()}
            data = urllib.urlencode(form)
            userpage = BeautifulSoup(self._request("GET", self.userpage + data, "", self.whatcd.headers).execute(True).body)
            info = self._parser().userInfo(userpage.find("div", {"class": "sidebar"}), self.name)
            self.userinfo = info
            return info
        else:
            print "no user id retrieved"
            return None


    def getTorrentsSeeding(self, page=1):
        """
            Returns a list with all user's uploaded music torrents
            in form of dictionary {page(tuple with current and total),tag, dlurl, id,
            artist(a tuple with 1 artist name || 2 names in case of two artists || 'Various Artists' if V.A.},
            album, release type, scene, year and artistid (a tuple with 1 artist id || 2 ids if 2 artists torrent || empty if V.A.}
        """
        if self.userid is None:
            self.userid = self.getUserId()
        url = "/torrents.php?type=seeding&userid=%s&page=%d" % (self.userid, page)
        torrentspage = BeautifulSoup(self._request("GET", url, "", self.whatcd.headers).execute(True).body)
        return self._parser().torrentsList(torrentspage)

    def getTorrentsSnatched(self, page=1):
        """
            Returns a list with all user's uploaded music torrents
            in form of dictionary {page(tuple with current and total),tag, dlurl, id,
            artist(a tuple with 1 artist name || 2 names in case of two artists || 'Various Artists' if V.A.},
            album, release type, scene, year and artistid (a tuple with 1 artist id || 2 ids if 2 artists torrent || empty if V.A.}
        """
        if self.userid is None:
            self.userid = self.getUserId()
        url = "/torrents.php?type=snatched&userid=%s&page=%d" % (self.userid, page)
        torrentspage = BeautifulSoup(self._request("GET", url, "", self.whatcd.headers).execute(True).body)
        return self._parser().torrentsList(torrentspage)

    def getTorrentsUploaded(self, page=1):
        """
            Returns a list with all user's uploaded music torrents
            in form of dictionary {page(tuple with current and total),tag, dlurl, id,
            artist(a tuple with 1 artist name || 2 names in case of two artists || 'Various Artists' if V.A.},
            album, release type, scene, year and artistid (a tuple with 1 artist id || 2 ids if 2 artists torrent || empty if V.A.}
        """
        if self.userid is None:
            self.userid = self.getUserId()
        url = "/torrents.php?type=uploaded&userid=%s&page=%d" % (self.userid, page)
        torrentspage = BeautifulSoup(self._request("GET", url, "", self.whatcd.headers).execute(True).body)
        return self._parser().torrentsList(torrentspage)


    def getTorrentsCommented(self, page=1):
        """
            Returns a list with all user's commented torrents
            in form of dictionary {postid, torrentid, comment,postdate, pages}

        """
        if self.userid is None:
            self.userid = self.getUserId()

        url = "/%s&page=%d" % (self.specificUserInfo().torrentscomments[1], page)
        torrentspage = BeautifulSoup(self._request("GET", url, "", self.whatcd.headers).execute(True).body)
        return self._parser().postsList(torrentspage)



    ###############################################
    #              specific values                #
    ###############################################


    def specificUserInfo(self):
        """
            Returns specific attributes of user info. None if user's paranoia is on
        """
        info = SpecificInformation()
        # Initialize attributes
        info.joindate, info.lastseen, info.dataup, info.datadown,\
        info.ratio, info.rratio, info.uppercentile, info.downpercentile,\
        info.torrentsuppercentile, info.reqfilledpercentile, info.bountyspentpercentile,\
        info.postsmadepercentile, info.artistsaddedpercentile, info.overallpercentile,\
        info.postsmadecom, info.torrentscommentscom, info.collagesstartedcom, info.collagescontrcon,\
        info.reqfilledcom, info.reqvotedcom, info.uploadedcom, info.uniquecom, info.perfectcom,\
        info.seedingcom, info.leechingcom, info.snatchedcom, info.invitedcom, info.artistsaddedcom\
        = (None, None, None, None, None, None, None, None, None, None, None, None, None, None,\
           None, None, None, None, None, None, None, None, None, None, None, None, None, None)


        if not self.userinfo and self.getInfo() is None:
            pass
        else:
            ######## stats ###########
            info.joindate = self.userinfo['stats']['joined']
            info.lastseen = self.userinfo['stats']['lastseen']
            info.dataup = self.userinfo['stats']['uploaded']
            info.datadown = self.userinfo['stats']['downloaded']
            info.ratio = self.userinfo['stats']['ratio']
            info.rratio = self.userinfo['stats']['rratio']
            ######## percentile ###########
            info.uppercentile = self.userinfo['percentile']['dataup']
            info.downpercentile = self.userinfo['percentile']['datadown']
            info.torrentsuppercentile = self.userinfo['percentile']['torrentsup']
            info.reqfilledpercentile = self.userinfo['percentile']['reqfilled']
            info.bountyspentpercentile = self.userinfo['percentile']['bountyspent']
            info.postsmadepercentile = self.userinfo['percentile']['postsmade']
            info.artistsaddedpercentile = self.userinfo['percentile']['artistsadded']
            info.overallpercentile = self.userinfo['percentile']['overall']
            ######## community ###########
            info.postsmadecom = self.userinfo['community']['forumposts']
            info.torrentscomments = self.userinfo['community']['torrentscomments']
            info.collagesstartedcom = self.userinfo['community']['startedcollages']
            info.collagescontrcon = self.userinfo['community']['contributedcollages']
            info.reqfilledcom = self.userinfo['community']['reqfilled']
            info.reqvotedcom = self.userinfo['community']['reqvoted']
            info.uploadedcom = self.userinfo['community']['uploaded']
            info.uniquecom = self.userinfo['community']['uniquegroups']
            info.perfectcom = self.userinfo['community']['pefectflacs']
            info.seedingcom = self.userinfo['community']['seeding']
            info.leechingcom = self.userinfo['community']['leeching']
            info.snatchedcom = self.userinfo['community']['snatched']
            info.invitedcom = self.userinfo['community']['invited'][0]
            info.artistsaddedcom = self.userinfo['community']['artists']



        return info


class Torrent(WhatBase):
    """A What.CD torrent"""

    def __init__(self, id, page, isparent, whatcd):
        """Create a torrent object.
        # Parameters:
            * id str: The torrent's id.
            * whatcd object: the WhatCD network object
            * page: The torrent page's number [optional]
        """
        WhatBase.__init__(self, whatcd)
        self.id = id
        self.page = page
        self.whatcd = whatcd
        self.isParent = isparent
        self.torrentpage = "/torrents.php?"
        self.torrentinfo = self.getInfo()


    def getTorrentUrl(self):
        """
            Returns torrent's URL
        """
        if self.isParent:
            form = {'id': self.id, 'page':self.page}
            data = urllib.urlencode(form)
            return self.torrentpage + data
        else:
            form = {'torrentid': self.id, 'page':self.page}
        data = urllib.urlencode(form)
        headers = self._request("GET", self.torrentpage + data, "", self.whatcd.headers).execute(True).headers

        if dict(headers) is None:
            return None
        else:
            if 'location' not in dict(headers).keys():
                return None
            else:
                return dict(headers)['location']


    def getInfo(self):
        """
            Returns a dictionnary with torrents's info
        """
        if self.getTorrentUrl() is None:
            print "no torrent retrieved with such id"
            return None

        torrentpage = BeautifulSoup(self._request("GET", "/" + self.getTorrentUrl(), "", self.whatcd.headers).execute(True).body)

        if 'Site log' in torrentpage.find("title").string:
            print "no torrent retrieved with such id"
            return None
        else:
            return self._parser().torrentInfo(torrentpage, self.id, self.isParent)


    def getTorrentParentId(self):
        """
            Returns torrent's group id
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['parentid']

    def getTorrentChildren(self):
        """
            Returns list of children if is a torrent group, else returns own id in list
        """
        if self.isParent:
            return self.torrentinfo['torrent']['childrenids']
        else:
            return [self.id]

    def getTorrentDownloadURL(self):
        """
            Returns relative url to download the torrent
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['downloadurl']

    def getTorrentDetails(self):
        """
            Returns torrent's details (format / bitrate)
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['details']

    def getTorrentEditionInfo(self):
        """
            Returns torrent's edition info (Edition information / media type)
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['editioninfo']

    def getTorrentMediaType(self):
        """
            Returns torrent's media type
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['rlsmedia']

    def getTorrentSize(self):
        """
            Returns torrent's size
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['size']


    def getTorrentSnatched(self):
        """
            Returns torrent's total snatches
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['snatched']


    def getTorrentSeeders(self):
        """
            Returns torrent's current seeders
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['seeders']

    def getTorrentLeechers(self):
        """
            Returns torrent's current leechers
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['leechers']

    def getTorrentUploadedBy(self):
        """
            Returns torrent's uploader
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['uploadedby']

    def getTorrentFolderName(self):
        """
            Returns torrent's folder name
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['foldername']

    def getTorrentFileList(self):
        """
            Returns torrent's file list
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['filelist']


    def getTorrentReleaseType(self):
        """
            Returns torrent's release type
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['rlstype']

    def getTorrentDescription(self):
        """
            Returns torrent's description / empty string is there's none
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['torrentdescription']

    def getTorrentComments(self):
        """
            Returns a list of dictionnaries with each comment in the torrent page
            {postid,post,userid,username}
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['comments']

    def getTorrentCommentsPagesNumber(self):
        """
            Returns number of pages of comments in the torrent
        """
        if self.torrentinfo:
            return self.torrentInfo['torrent']['commentspages']

    def isTorrentFreeLeech(self):
        """
            Returns True if torrent is freeleeech, False if not
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['isfreeleech']

    def isTorrentReported(self):
        """
            Returns True if torrent is reported, False if not
        """
        if self.torrentinfo:
            return self.torrentinfo['torrent']['isreported']


class Artist(WhatBase):
    """A What.CD artist"""

    def __init__(self, name, whatcd):
        """Create an artist object.
        # Parameters:
            * name str: The artist's name.
            * whatcd object: The WhatCD network object
        """
        WhatBase.__init__(self, whatcd)
        self.name = name
        self.whatcd = whatcd
        self.artistpage = "/artist.php"
        self.utils = Utils()
        self.info = self.getInfo()


    def getArtistName(self):
        """
            Returns artist's name
        """
        return self.name

    def getArtistId(self):
        """
            Returns artist's id, None if artist's not found
        """
        form = {'artistname': self.name}
        data = urllib.urlencode(form)
        headers = self._request("GET", self.artistpage + "?" + data, "", self.whatcd.headers).execute(True).headers
        if dict(headers)['location'][0:14] != 'artist.php?id=':
            return None
        else:
            return dict(headers)['location'][14:]

    def getInfo(self):
        """
            Returns artist's info, None if there isn't
        """
        if self.getArtistId():
            form = {'id': self.getArtistId()}
            data = urllib.urlencode(form)
            artistpage = BeautifulSoup(self._request("GET", self.artistpage + "?" + data, "", self.whatcd.headers).execute(True).body)
            return self._parser().artistInfo(artistpage)
        else:
            print "no artist info retrieved"
            return None

    def getArtistReleases(self):
        """
            Returns a list with all artist's releases in form of dictionary {releasetype, year, name, id}
        """
        return self.info['releases']

    def getArtistImage(self):
        """
            Return the artist image URL, None if there's no image
        """
        return self.info['image']

    def getArtistInfo(self):
        """
            Return the artist's info, blank string if none
        """
        return self.info['info']

    def getArtistTags(self):
        """
            Return a list with artist's tags
        """
        return self.info['tags']

    def getArtistSimilar(self):
        """
            Return a list with artist's similar artists
        """
        return self.info['similarartists']

    def getArtistRequests(self):
        """
            Returns a list with all artist's requests in form of dictionary {requestname, id}
        """
        return self.info['requests']

    def setArtistInfo(self, id, info):
        """
            Updates what.cd artist's info and image
            Returns 1 if artist info updated succesfully, 0 if not.
        # Parameters:
            * id str: what.cd artist's id
            * info tuple: (The artist's info -str-, image url -str- (None if there isn't))
        """
        if info[0]:
            params = {'action': 'edit', 'artistid':id}
            data = urllib.urlencode(params)

            edit_page = BeautifulSoup(self._request("GET", self.artistpage + "?" + data, "", self.whatcd.headers).execute(True).body)
            what_form = self._parser().whatForm(edit_page, 'edit')
            if info[1]:
                image_to_post = info[1]
            else:
                image_to_post = what_form['image']
            data_to_post = {'body': info[0].encode('utf-8'),
                            'summary':'automated artist info insertion',\
                            'image':image_to_post,\
                            'artistid':what_form['artistid'],\
                            'auth':what_form['auth'],\
                            'action':what_form['action']}

            #post artist's info
            self.whatcd.headers['Content-type'] = "application/x-www-form-urlencoded"
            response = self._request("POST", self.artistpage, urllib.urlencode(data_to_post), self.whatcd.headers).execute(False)
            artist_id_returned = dict(response.headers)['location'][14:]

            if str(artist_id_returned) == str(what_form['artistid']):
                return 1
            else:
                return 0

        else:
            return 'no artist info provided. Aborting.'
            exit()


class Parser(object):

    def __init__(self, whatcd):
        self.utils = Utils()
        self.whatcd = whatcd
        self.totalpages = 0

    def authenticatedUserInfo(self, dom):
        """
            Parse the index page and returns a dictionnary with basic authenticated user information
        """
        userInfo = {}
        soup = BeautifulSoup(str(dom))
        for ul in soup.fetch('ul'):
            ul_all_li = ul.findAll('li')
            if ul["id"] == "userinfo_username":
                #retrieve user logged id
                hrefid = ul_all_li[0].find("a")["href"]
                regid = re.compile('[0-9]+')
                if regid.search(hrefid) is None:
                    self.debugMessage("not found  href to retrieve user id")
                else:
                    userInfo["id"] = regid.search(hrefid).group(0)

                #retrieve user logged id
                hrefauth = ul_all_li[2].find("a")["href"]
                regauth = re.compile('=[0-9a-zA-Z]+')
                if regid.search(hrefid) is None:
                    self.debugMessage("not found  href to retrieve user id")
                else:
                    userInfo["authcode"] = regauth.search(hrefauth).group(0)[1:]

            elif ul["id"] == "userinfo_stats":
                if len(ul_all_li) > 0:
                    userInfo["uploaded"] = ul_all_li[0].find("span").string
                    userInfo["downloaded"] = ul_all_li[1].find("span").string
                    userInfo["ratio"] = ul_all_li[2].findAll("span")[1].string
                    userInfo["required"] = ul_all_li[3].find("span").string
                    userInfo["authenticate"] = True

        return userInfo

    def userInfo(self, dom, user):
        """
            Parse an user's page and returns a dictionnary with its information

        # Parameters:
            * dom str: user page html
            * user str: what.cd username
        """
        userInfo = {'stats':{}, 'percentile':{}, 'community':{}}
        soup = BeautifulSoup(str(dom))

        for div in soup.fetch('div', {'class':'box'}):

            #if paronoia is not set to 'Off', stop collecting data
            if div.findAll('div')[0].string == "Personal":
                if div.find('ul').findAll('li')[1].contents[1].string.strip() != "Off":
                    return None

        all_div_box = soup.findAll('div', {'class': 'box'})
        statscontainer = all_div_box[1]
        percentilecontainer = all_div_box[2]
        communitycontainer = all_div_box[4]

        statscontainer_all_li = statscontainer.findAll('li')
        userInfo['stats']['joined'] = statscontainer_all_li[0].find('span')['title']
        userInfo['stats']['lastseen'] = statscontainer_all_li[1].find('span')['title']
        userInfo['stats']['uploaded'] = statscontainer_all_li[2].string[10:]
        userInfo['stats']['downloaded'] = statscontainer_all_li[3].string[12:]
        userInfo['stats']['ratio'] = statscontainer_all_li[4].find('span').string
        userInfo['stats']['rratio'] = statscontainer_all_li[5].string[16:]

#        percentilecontainer_all_li = percentilecontainer.findAll('li')
#        userInfo['percentile']['dataup'] = percentilecontainer_all_li[0].string[15:]
#        userInfo['percentile']['datadown'] = percentilecontainer_all_li[1].string[17:]
#        userInfo['percentile']['torrentsup'] = percentilecontainer_all_li[2].string[19:]
#        userInfo['percentile']['reqfilled'] = percentilecontainer_all_li[3].string[17:]
#        userInfo['percentile']['bountyspent'] = percentilecontainer_all_li[4].string[14:]
#        userInfo['percentile']['postsmade'] = percentilecontainer_all_li[5].string[12:]
#        userInfo['percentile']['artistsadded'] = percentilecontainer_all_li[6].string[15:]
#        userInfo['percentile']['overall'] = percentilecontainer_all_li[7].find('strong').string[14:]

#        communitycontainer_all_li = communitycontainer.findAll('li')
#        userInfo['community']['forumposts'] = (communitycontainer_all_li[0].contents[0].string[13:len(communitycontainer_all_li[0].contents[0].string)-2],\
#                                               communitycontainer_all_li[0].find('a')['href'])
#        userInfo['community']['torrentscomments'] = (communitycontainer_all_li[1].contents[0].string[18:len(communitycontainer_all_li[1].contents[0].string)-2],\
#                                                     communitycontainer_all_li[1].find('a')['href'])
#        userInfo['community']['startedcollages'] = (communitycontainer_all_li[2].contents[0].string[18:len(communitycontainer_all_li[2].contents[0].string)-2],\
#                                                    communitycontainer_all_li[2].find('a')['href'])
#        userInfo['community']['contributedcollages'] = (communitycontainer_all_li[3].contents[0].string[25:len(communitycontainer_all_li[3].contents[0].string)-2],\
#                                                        communitycontainer_all_li[3].find('a')['href'])
#        userInfo['community']['reqfilled'] = (communitycontainer_all_li[4].contents[0].string[17:len(communitycontainer_all_li[4].contents[0].string)-2],\
#                                              communitycontainer_all_li[4].find('a')['href'])
#        userInfo['community']['reqvoted'] = (communitycontainer_all_li[5].contents[0].string[16:len(communitycontainer_all_li[5].contents[0].string)-2],\
#                                             communitycontainer_all_li[5].find('a')['href'])
#        userInfo['community']['uploaded'] = (communitycontainer_all_li[6].contents[0].string[10:len(communitycontainer_all_li[6].contents[0].string)-2],\
#                                             communitycontainer_all_li[6].find('a')['href'])
#        userInfo['community']['uniquegroups'] = (communitycontainer_all_li[7].contents[0].string[15:len(communitycontainer_all_li[7].contents[0].string)-2],\
#                                                 communitycontainer_all_li[7].find('a')['href'])
#        userInfo['community']['pefectflacs'] = (communitycontainer_all_li[8].contents[0].string[16:len(communitycontainer_all_li[8].contents[0].string)-2],\
#                                                communitycontainer_all_li[8].find('a')['href'])
#        userInfo['community']['seeding'] = (communitycontainer_all_li[9].contents[0].string[9:len(communitycontainer_all_li[9].contents[0].string)-2],\
#                                            communitycontainer_all_li[9].find('a')['href'])
#        userInfo['community']['leeching'] = (communitycontainer_all_li[10].contents[0].string[10:len(communitycontainer_all_li[10].contents[0].string)-2],\
#                                             communitycontainer_all_li[10].find('a')['href'])
#        #NB: there's a carriage return and white spaces inside the snatched li tag
#        userInfo['community']['snatched'] = (communitycontainer_all_li[11].contents[0].string[10:len(communitycontainer_all_li[11].contents[0].string)-7],\
#                                             communitycontainer_all_li[11].find('a')['href'])
#        userInfo['community']['invited'] = (communitycontainer_all_li[12].contents[0].string[9:],\
#                                            None)
#        userInfo['community']['artists'] = percentilecontainer_all_li[6]['title']

        return userInfo

    def torrentInfo(self, dom, id, isparent):
        """
            Parse a torrent's page and returns a dictionnary with its information
        """

        torrentInfo = {'torrent':{}}
        torrentfiles = []
        torrentdescription = ""
        isreported = False
        isfreeleech = False
        soup = BeautifulSoup(str(dom))
        if isparent:
            torrentInfo['torrent']['parentid'] = id
            torrentInfo['torrent']['childrenids'] = []
            for torrent in soup.findAll('tr', {'class':re.compile(r'\bgroupid_%s.+edition_\d.+group_torrent' % id)}):
                child_id = re.search('\d+$', torrent['id']).group(0)
                if child_id:
                    torrentInfo['torrent']['childrenids'].append(child_id)
        else:
            groupidurl = soup.findAll('div', {'class':'linkbox'})[0].find('a')['href']
            torrentInfo['torrent']['editioninfo'] = soup.findAll('td', {'class':'edition_info'})[0].find('strong').contents[-1]
            regrlsmedia = re.compile('CD|DVD|Vinyl|Soundboard|SACD|Cassette|WEB|Blu-ray')
            torrentInfo['torrent']['rlsmedia'] = regrlsmedia.search(torrentInfo['torrent']['editioninfo']).group(0)
            torrentInfo['torrent']['parentid'] = groupidurl[groupidurl.rfind("=") + 1:]

            all_tr_id_torrent = soup.findAll('tr', {'id': 'torrent%s' % id})
            all_torrent_a = all_tr_id_torrent[0].findAll('a')

            torrentInfo['torrent']['downloadurl'] = all_tr_id_torrent[0].findAll('a', {'title':'Download'})[0]['href']
            ## is freeleech or/and reported? ##
            #both
            if len(all_torrent_a[-1].contents) == 4:
                isreported = True
                isfreeleech = True
                torrentInfo['torrent']['details'] = all_torrent_a[-1].contents[0]
            #either
            elif len(all_torrent_a[-1].contents) == 2:
                if all_torrent_a[-1].contents[1].string == 'Reported':
                    isreported = True
                elif all_torrent_a[-1].contents[1].string == 'Freeleech!':
                    isreported = True
                torrentInfo['torrent']['details'] = all_torrent_a[-1].contents[0]
            #none
            else:
                torrentInfo['torrent']['details'] = all_torrent_a[-1].contents[0]
            torrentInfo['torrent']['isfreeleech'] = isfreeleech
            torrentInfo['torrent']['isreported'] = isreported

            all_torrent_td = all_tr_id_torrent[0].findAll('td')
            torrentInfo['torrent']['size'] = all_torrent_td[1].string
            torrentInfo['torrent']['snatched'] = all_torrent_td[2].string
            torrentInfo['torrent']['seeders'] = all_torrent_td[3].string
            torrentInfo['torrent']['leechers'] = all_torrent_td[4].string

            all_tr_id_torrent_underscore = soup.findAll('tr', {'id': 'torrent_%s' % id})
            torrentInfo['torrent']['uploadedby'] = all_tr_id_torrent_underscore[0].findAll('a')[0].string
            foldername = soup.findAll('div', {'id':'files_%s' % id})[0].findAll('div')[1].string
            if(foldername is None):
                torrentInfo['torrent']['foldername'] = None
            else:
                torrentInfo['torrent']['foldername'] = self.utils.decodeHTMLEntities(foldername)
            files = soup.findAll('div', {'id':'files_%s' % id})[0].findAll('tr')
            for file in files[1:-1]:
                torrentfiles.append(self.utils.decodeHTMLEntities(file.contents[0].string))
            torrentInfo['torrent']['filelist'] = torrentfiles
            #is there any description?
#            all_torrent_blockquote = all_tr_id_torrent_underscore[0].findAll('blockquote')
#            if len(all_torrent_blockquote) > 1:
#                description = torrentInfo['torrent']['description'] = all_torrent_blockquote[1].contents
#                info = ''
#                for content in description:
#                    if content.string:
#                        info = "%s%s" % (info, self.utils._string(content.string))
#                        torrentdescription = "%s%s" % (torrentdescription, self.utils._string(content.string))
#            torrentInfo['torrent']['torrentdescription'] = torrentdescription
            regrlstype = re.compile('Album|Soundtrack|EP|Anthology|Compilation|DJ Mix|Single|Live album|Remix|Bootleg|Interview|Mixtape|Unknown')
            torrentInfo['torrent']['rlstype'] = regrlstype.search(soup.find('div', {'class':'thin'}).find('h2').contents[1]).group(0)

        torrentInfo['torrent']['comments'] = []
        torrentInfo['torrent']['commentspages'] = 0

        #        if len(soup.findAll('table', {'class':'forum_post box vertical_margin'})) > 0:
        #            linkbox = dom.findAll("div", {"class": "linkbox"})[-1]
        #            pages = 1
        #            postid = ''
        #            userid = ''
        #            post = ''
        #            # if there's more than 1 page of torrents
        #            linkbox_all_a = linkbox.findAll("a")
        #            if len(linkbox_all_a):
        #                # by default torrent page show last page of comments
        #                lastpage = linkbox_all_a[-1]['href']
        #                pages = int(lastpage[18:lastpage.find('&')]) + 1
        #            for comment in soup.findAll('table', {'class':'forum_post box vertical_margin'}):
        #                postid = comment.find("a", {"class":"post_id"}).string[1:]
        #
        #                all_comment_a = comment.findAll("a")
        #                userid = all_comment_a[1]['href'][12:]
        #                username = all_comment_a[1].string
        #                post = comment.find("div", {"id":"content" + postid})
        #                post = u''.join([post.string for post in post.findAll(text=True)])
        #                torrentInfo['torrent']['comments'].append({"postid":postid, "post":post, "userid":userid, "username":username})
        #
        #            torrentInfo['torrent']['commentspages'] = pages

        return torrentInfo

    def artistInfo(self, dom):
        """
            Parse an artist's page and returns a dictionnary with its information
        """
        artistInfo = {}
        releases = []
        requests = []
        infoartist = ""
        tagsartist = []
        similarartists = []
        soup = BeautifulSoup(str(dom))
        for releasetype in soup.fetch('table', {'class': re.compile(r'\btorrent_table\b')}):
            releasetypenames = releasetype.findAll('strong')
            releasetypename = releasetypenames[0].string
            for release in releasetypenames[1:-1]:
                #skip release edition info and Freeleech! <strong>s
                if len(release.parent.contents) > 1 and len(release.contents) > 1:
                    releaseyear = release.contents[0][0:4]
                    releasename = release.contents[1].string
                    releasehref = release.contents[1]['href']
                    releaseid = releasehref[releasehref.rfind('=') + 1:]
                    releases.append({'releasetype':releasetypename,\
                                     'year': releaseyear, 'name':self.utils.decodeHTMLEntities(releasename), 'id':releaseid})

        artistInfo['releases'] = releases

        # This artist stuff wastes 10 secs

        #is there an artist image?
#        artistInfo['image'] = None
#        div_box = soup.find('div', {'class': 'box'})
#        if div_box.find('img'):
#            artistInfo['image'] = div_box.find('img')['src']
#            #is there any artist info?
#        contents = soup.find('div', {'class':'body'}).contents
#        if len(contents) > 0:
#            for content in contents:
#                if content.string:
#                    infoartist = "%s%s" % (infoartist, self.utils._string(content.string))
#        artistInfo['info'] = self.utils.decodeHTMLEntities(infoartist)
        #is there any artist tags?
#        all_ul_class_stats_nobullet = soup.findAll('ul', {'class': 'stats nobullet'})
#        all_ul_class_stats_nobullet_li = all_ul_class_stats_nobullet[0].findAll('li')
#        if all_ul_class_stats_nobullet_li:
#            ul = all_ul_class_stats_nobullet_li
#            for li in ul:
#                if li.contents[0].string:
#                    tagsartist.append(self.utils._string(li.contents[0].string))
#        artistInfo['tags'] = tagsartist
        #is there any similar artist?
#        if all_ul_class_stats_nobullet[2].findAll('span', {'title':'2'}):
#            artists = all_ul_class_stats_nobullet[2].findAll('span', {'title':'2'})
#            for artist in artists:
#                if artist.contents[0].string:
#                    similarartists.append(self.utils._string(artist.contents[0].string))
#        artistInfo['similarartists'] = similarartists
        #is there any request?
#        table_requests = soup.find('table', {'id': 'requests'})
#        if table_requests:
#            for request in table_requests.findAll('tr', {'class':re.compile('row')}):
#                request_all_a_1 = request.findAll('a')[1]
#                requests.append({'requestname': request_all_a_1.string, 'id': request_all_a_1['href'][28:]})
#
#        artistInfo['requests'] = requests

        return artistInfo

    def torrentsList(self, dom):
        """
            Parse a torrent's list page and returns a dictionnary with its information
        """
        torrentslist = []
        torrentssoup = dom.find("table", {"width": "100%"})
        pages = 0

        #if there's at least 1 torrent in the list
        if torrentssoup:
            navsoup = dom.find("div", {"class": "linkbox"})
            pages = 1
            regyear = re.compile('\[\d{4}\]')

            #is there a page navigation bar?
            if navsoup.contents:
                #if there's more than 1 page of torrents
                if navsoup.contents[-1].has_key('href'):
                    lastpage = navsoup.contents[-1]['href']
                    pages = lastpage[18:lastpage.find('&')]
                    self.totalpages = pages
                else: #we are at the last page, no href
                    pages = self.totalpages + 1
                #fetch all tr except first one (column head)
            for torrent in torrentssoup.fetch('tr')[1:]:
                #exclude non music torrents
                if torrent.find('td').find('div')['class'][0:10] == 'cats_music':

                    torrenttag = torrent.find('td').contents[1]['title']
                    all_td_1_span_a = torrent.findAll('td')[1].find('span').findAll('a')
                    torrentdl = all_td_1_span_a[0]['href']
                    torrentrm = all_td_1_span_a[1]['href']
                    torrentid = torrentrm[torrentrm.rfind('=') + 1:]
                    torrenttd = torrent.findAll('td')[1]

                    # remove dataless elements
                    torrenttags = torrenttd.div
                    rightlinks = torrenttd.span
                    torrenttags.extract()
                    rightlinks.extract()

                    # remove line breaks
                    torrenttd = "".join([line.strip() for line in str(torrenttd).split("\n")])
                    torrenttd = BeautifulSoup(torrenttd)
                    isScene = False
                    info = ""

                    torrenttd_find_a = torrenttd.find("a")
                    torrenttd_all_a = torrenttd.findAll("a")
                    if len(torrenttd_all_a) == 2:
                        #one artist
                        torrentartist = (self.utils.decodeHTMLEntities(torrenttd_find_a.string), )
                        artistid = (torrenttd_find_a['href'][14:], )
                        torrentalbum = torrenttd_all_a[1].string
                        info = torrenttd_all_a[1].nextSibling.string.strip()


                    elif len(torrenttd_all_a) == 1:
                        #various artists
                        torrentartist = ('Various Artists', )
                        artistid = ()
                        torrentalbum = torrenttd_find_a.string
                        info = torrenttd_find_a.nextSibling.string.strip()

                    elif len(torrenttd_all_a) == 3:
                        #two artists
                        torrentartist = (self.utils.decodeHTMLEntities(torrenttd_all_a[0].string),\
                                         self.utils.decodeHTMLEntities(torrenttd_all_a[1].string))
                        artistid = (torrenttd_all_a[0]['href'][14:],\
                                    torrenttd_all_a[1]['href'][14:])
                        torrentalbum = torrenttd_all_a[2].string
                        info = torrenttd_all_a[2].nextSibling.string.strip()

                    elif torrenttd.find(text=re.compile('performed by')):
                        #performed by
                        torrentartist = (self.utils.decodeHTMLEntities(torrenttd_all_a[-2].string), )
                        artistid = (torrenttd_all_a[-2]['href'][14:], )
                        torrentalbum = torrenttd_all_a[-1].string
                        info = torrenttd_all_a[-1].nextSibling.string.strip()

                    if 'Scene' in info:
                        isScene = True

                    torrentyear = regyear.search(info).group(0)[1:5]
                    torrentslist.append({'tag':torrenttag,\
                                         'dlurl':torrentdl,\
                                         'id':torrentid,\
                                         'artist':torrentartist,\
                                         'artistid':artistid,\
                                         'album':self.utils.decodeHTMLEntities(torrentalbum),
                                         'year':torrentyear,
                                         'pages':pages,
                                         'scene':isScene})

        return torrentslist

    def postsList(self, dom):
        """
            Parse a post list page and returns a dictionnary with each post information:
            {torrentid, commentid, postid}
        """
        postslist = []
        postssoup = dom.find("div", {"class": "thin"})
        pages = 0

        #if there's at least 1 post in the list
        if postssoup:
            navsoup = dom.find("div", {"class": "linkbox"})

            #if there's more than 1 page of torrents
            if navsoup.find("a"):
                lastpage = navsoup.findAll("a")[1]['href']
                pages = lastpage[18:lastpage.find('&')]
                self.totalpages = pages
            else: #we are at the last page, no link
                pages = 1

            for post in postssoup.fetch('table', {'class':'forum_post box vertical_margin'}):
                commentbody = post.find("td", {"class":"body"})
                postid = post.find("span").findAll("a")[0].string[1:]
                torrentid = post.find("span").findAll("a")[-1]['href'][post.find("span").findAll("a")[-1]['href'].rfind('=') + 1:]
                comment = u''.join([commentbody.string for commentbody in commentbody.findAll(text=True)])
                postdate = post.find("span", {"class":"time"})['title']
                postslist.append({'postid':postid,\
                                  'torrentid':torrentid,\
                                  'comment':comment,\
                                  'postdate':postdate,\
                                  'pages':pages})


        return postslist


    def whatForm(self, dom, action):
        """
            Parse a what.cd edit page and returns a dict with all form inputs/textareas names and values
            # Parameters:
                * dom str: the edit page dom.
                + action str: the action value from the requested form
        """
        inputs = {}

        form = dom.find('input', {'name':'action', 'value':action}).parent
        elements = form.fetch(('input', 'textarea'))
        #get all form elements except for submit input
        for element in elements[0:3]:
            name = element.get('name', None)
            if element.name == 'textarea':
                inputs[name] = element.string
            else:
                inputs[name] = element.get('value', None)
        return inputs



if __name__ == "__main__":
    print "Module to manage what.cd as a web service"
