"""Profiler tools for CherryPy.

CherryPy users
==============

You can profile any of your pages as follows::

    from cherrypy.lib import profiler

    class Root:
        p = profiler.Profiler("/path/to/profile/dir")

        @cherrypy.expose
        def index(self):
            self.p.run(self._index)

        def _index(self):
            return "Hello, world!"

    cherrypy.tree.mount(Root())

You can also turn on profiling for all requests
using the ``make_app`` function as WSGI middleware.

CherryPy developers
===================

This module can be used whenever you make changes to CherryPy,
to get a quick sanity-check on overall CP performance. Use the
``--profile`` flag when running the test suite. Then, use the ``serve()``
function to browse the results in a web browser. If you run this
module from the command line, it will call ``serve()`` for you.
"""

import io
import os
import os.path
import sys
import warnings

import cherrypy


try:
    import profile
    import pstats

    def new_func_strip_path(func_name):
        """Add ``__init__`` modules' parents.

        This makes the profiler output more readable.
        """
        filename, line, name = func_name
        if filename.endswith('__init__.py'):
            return (
                os.path.basename(filename[:-12]) + filename[-12:],
                line,
                name,
            )
        return os.path.basename(filename), line, name

    pstats.func_strip_path = new_func_strip_path
except ImportError:
    profile = None
    pstats = None


_count = 0


class Profiler(object):
    """A profiling app."""

    def __init__(self, path=None):
        """Prepare the profiling app resources."""
        if not path:
            path = os.path.join(os.path.dirname(__file__), 'profile')
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)

    def run(self, func, *args, **params):
        """Dump profile data into self.path."""
        global _count
        c = _count = _count + 1
        path = os.path.join(self.path, 'cp_%04d.prof' % c)
        prof = profile.Profile()
        result = prof.runcall(func, *args, **params)
        prof.dump_stats(path)
        return result

    def statfiles(self):
        """Compose a list of statistics file names.

        :returns: A list of available profiles.
        :rtype: list[str]
        """
        return [f for f in os.listdir(self.path)
                if f.startswith('cp_') and f.endswith('.prof')]

    def stats(self, filename, sortby='cumulative'):
        """Generate statistics from given profile.

        :returns: The sorted stats index printout.
        :rtype: str
        """
        sio = io.StringIO()
        if sys.version_info >= (2, 5):
            s = pstats.Stats(os.path.join(self.path, filename), stream=sio)
            s.strip_dirs()
            s.sort_stats(sortby)
            s.print_stats()
        else:
            # pstats.Stats before Python 2.5 didn't take a 'stream' arg,
            # but just printed to stdout. So re-route stdout.
            s = pstats.Stats(os.path.join(self.path, filename))
            s.strip_dirs()
            s.sort_stats(sortby)
            oldout = sys.stdout
            try:
                sys.stdout = sio
                s.print_stats()
            finally:
                sys.stdout = oldout
        response = sio.getvalue()
        sio.close()
        return response

    @cherrypy.expose
    def index(self):
        """Render the profiling viewer index page."""
        return """<html>
        <head><title>CherryPy profile data</title></head>
        <frameset cols='200, 1*'>
            <frame src='menu' />
            <frame name='main' src='' />
        </frameset>
        </html>
        """

    @cherrypy.expose
    def menu(self):
        """Render the profiler menu page html layout."""
        yield '<h2>Profiling runs</h2>'
        yield '<p>Click on one of the runs below to see profiling data.</p>'
        runs = self.statfiles()
        runs.sort()
        for i in runs:
            yield "<a href='report?filename=%s' target='main'>%s</a><br />" % (
                i, i)

    @cherrypy.expose
    def report(self, filename):
        """Render a statistics report."""
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return self.stats(filename)


class ProfileAggregator(Profiler):
    """A profiling aggregator app."""

    def __init__(self, path=None):
        """Prepare the profiling aggregator app resources."""
        Profiler.__init__(self, path)
        global _count
        self.count = _count = _count + 1
        self.profiler = profile.Profile()

    def run(self, func, *args, **params):
        """Dump aggeregated profile data into ``self.path``."""
        path = os.path.join(self.path, 'cp_%04d.prof' % self.count)
        result = self.profiler.runcall(func, *args, **params)
        self.profiler.dump_stats(path)
        return result


class make_app:
    """Profiling WSGI middleware wrapper."""

    def __init__(self, nextapp, path=None, aggregate=False):
        """Make a WSGI middleware app which wraps 'nextapp' with profiling.

        nextapp
            the WSGI application to wrap, usually an instance of
            cherrypy.Application.

        path
            where to dump the profiling output.

        aggregate
            if True, profile data for all HTTP requests will go in
            a single file. If False (the default), each HTTP request will
            dump its profile data into a separate file.

        """
        if profile is None or pstats is None:
            msg = ('Your installation of Python does not have a profile '
                   "module. If you're on Debian, try "
                   '`sudo apt-get install python-profiler`. '
                   'See http://www.cherrypy.org/wiki/ProfilingOnDebian '
                   'for details.')
            warnings.warn(msg)

        self.nextapp = nextapp
        self.aggregate = aggregate
        if aggregate:
            self.profiler = ProfileAggregator(path)
        else:
            self.profiler = Profiler(path)

    def __call__(self, environ, start_response):
        """Process a WSGI request."""
        def gather():
            result = []
            for line in self.nextapp(environ, start_response):
                result.append(line)
            return result
        return self.profiler.run(gather)


def serve(path=None, port=8080):
    """Serve the web app with profiler activated."""
    if profile is None or pstats is None:
        msg = ('Your installation of Python does not have a profile module. '
               "If you're on Debian, try "
               '`sudo apt-get install python-profiler`. '
               'See http://www.cherrypy.org/wiki/ProfilingOnDebian '
               'for details.')
        warnings.warn(msg)

    cherrypy.config.update({'server.socket_port': int(port),
                            'server.thread_pool': 10,
                            'environment': 'production',
                            })
    cherrypy.quickstart(Profiler(path))


if __name__ == '__main__':
    serve(*tuple(sys.argv[1:]))
