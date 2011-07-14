# mako/cache.py
# Copyright (C) 2006-2011 the Mako authors and contributors <see AUTHORS file>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from mako import exceptions

cache = None

class BeakerMissing(object):
    def get_cache(self, name, **kwargs):
        raise exceptions.RuntimeException("the Beaker package is required to use cache functionality.")

class Cache(object):
    """Represents a data content cache made available to the module
    space of a :class:`.Template` object.
 
    :class:`.Cache` is a wrapper on top of a Beaker CacheManager object.
    This object in turn references any number of "containers", each of
    which defines its own backend (i.e. file, memory, memcached, etc.) 
    independently of the rest.
 
    """
 
    def __init__(self, id, starttime):
        self.id = id
        self.starttime = starttime
        self.def_regions = {}
 
    def put(self, key, value, **kwargs):
        """Place a value in the cache.
 
        :param key: the value's key.
        :param value: the value
        :param \**kwargs: cache configuration arguments.  The 
         backend is configured using these arguments upon first request.
         Subsequent requests that use the same series of configuration
         values will use that same backend.
 
        """
 
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
 
        self._get_cache(defname, **kwargs).put_value(key, starttime=self.starttime, expiretime=expiretime)
 
    def get(self, key, **kwargs):
        """Retrieve a value from the cache.
 
        :param key: the value's key.
        :param \**kwargs: cache configuration arguments.  The 
         backend is configured using these arguments upon first request.
         Subsequent requests that use the same series of configuration
         values will use that same backend.
 
        """
 
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
 
        return self._get_cache(defname, **kwargs).get_value(key, starttime=self.starttime, expiretime=expiretime, createfunc=createfunc)
 
    def invalidate(self, key, **kwargs):
        """Invalidate a value in the cache.
 
        :param key: the value's key.
        :param \**kwargs: cache configuration arguments.  The 
         backend is configured using these arguments upon first request.
         Subsequent requests that use the same series of configuration
         values will use that same backend.
 
        """
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
 
        self._get_cache(defname, **kwargs).remove_value(key, starttime=self.starttime, expiretime=expiretime)
 
    def invalidate_body(self):
        """Invalidate the cached content of the "body" method for this template.
 
        """
        self.invalidate('render_body', defname='render_body')
 
    def invalidate_def(self, name):
        """Invalidate the cached content of a particular <%def> within this template."""
 
        self.invalidate('render_%s' % name, defname='render_%s' % name)
 
    def invalidate_closure(self, name):
        """Invalidate a nested <%def> within this template.
 
        Caching of nested defs is a blunt tool as there is no
        management of scope - nested defs that use cache tags
        need to have names unique of all other nested defs in the 
        template, else their content will be overwritten by 
        each other.
 
        """
 
        self.invalidate(name, defname=name)
 
    def _get_cache(self, defname, type=None, **kw):
        global cache
        if not cache:
            try:
                from beaker import cache as beaker_cache
                cache = beaker_cache.CacheManager()
            except ImportError:
                # keep a fake cache around so subsequent 
                # calls don't attempt to re-import
                cache = BeakerMissing()

        if type == 'memcached':
            type = 'ext:memcached'
        if not type:
            (type, kw) = self.def_regions.get(defname, ('memory', {}))
        else:
            self.def_regions[defname] = (type, kw)
        return cache.get_cache(self.id, type=type, **kw)
 