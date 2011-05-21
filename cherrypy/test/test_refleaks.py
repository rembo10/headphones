"""Tests for refleaks."""

import gc
from cherrypy._cpcompat import HTTPConnection, HTTPSConnection, ntob
import threading

import cherrypy
from cherrypy import _cprequest


data = object()

def get_instances(cls):
    return [x for x in gc.get_objects() if isinstance(x, cls)]


from cherrypy.test import helper


class ReferenceTests(helper.CPWebCase):

    def setup_server():
        
        class Root:
            def index(self, *args, **kwargs):
                cherrypy.request.thing = data
                return "Hello world!"
            index.exposed = True
            
            def gc_stats(self):
                output = ["Statistics:"]
                
                # Uncollectable garbage
                
                # gc_collect isn't perfectly synchronous, because it may
                # break reference cycles that then take time to fully
                # finalize. Call it twice and hope for the best.
                gc.collect()
                unreachable = gc.collect()
                if unreachable:
                    output.append("\n%s unreachable objects:" % unreachable)
                    trash = {}
                    for x in gc.garbage:
                        trash[type(x)] = trash.get(type(x), 0) + 1
                    trash = [(v, k) for k, v in trash.items()]
                    trash.sort()
                    for pair in trash:
                        output.append("    " + repr(pair))
                
                # Request references
                reqs = get_instances(_cprequest.Request)
                lenreqs = len(reqs)
                if lenreqs < 2:
                    output.append("\nMissing Request reference. Should be 1 in "
                                  "this request thread and 1 in the main thread.")
                elif lenreqs > 2:
                    output.append("\nToo many Request references (%r)." % lenreqs)
                    for req in reqs:
                        output.append("Referrers for %s:" % repr(req))
                        for ref in gc.get_referrers(req):
                            if ref is not reqs:
                                output.append("    %s" % repr(ref))
                
                # Response references
                resps = get_instances(_cprequest.Response)
                lenresps = len(resps)
                if lenresps < 2:
                    output.append("\nMissing Response reference. Should be 1 in "
                                  "this request thread and 1 in the main thread.")
                elif lenresps > 2:
                    output.append("\nToo many Response references (%r)." % lenresps)
                    for resp in resps:
                        output.append("Referrers for %s:" % repr(resp))
                        for ref in gc.get_referrers(resp):
                            if ref is not resps:
                                output.append("    %s" % repr(ref))
                
                return "\n".join(output)
            gc_stats.exposed = True
        
        cherrypy.tree.mount(Root())
    setup_server = staticmethod(setup_server)

    
    def test_threadlocal_garbage(self):
        success = []
        
        def getpage():
            host = '%s:%s' % (self.interface(), self.PORT)
            if self.scheme == 'https':
                c = HTTPSConnection(host)
            else:
                c = HTTPConnection(host)
            try:
                c.putrequest('GET', '/')
                c.endheaders()
                response = c.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertEqual(body, ntob("Hello world!"))
            finally:
                c.close()
            success.append(True)
        
        ITERATIONS = 25
        ts = []
        for _ in range(ITERATIONS):
            t = threading.Thread(target=getpage)
            ts.append(t)
            t.start()
        
        for t in ts:
            t.join()
        
        self.assertEqual(len(success), ITERATIONS)
        
        self.getPage("/gc_stats")
        self.assertBody("Statistics:")

