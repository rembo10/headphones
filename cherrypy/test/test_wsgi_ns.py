import cherrypy
from cherrypy.test import helper


class WSGI_Namespace_Test(helper.CPWebCase):

    def setup_server():
        
        class WSGIResponse(object):
            
            def __init__(self, appresults):
                self.appresults = appresults
                self.iter = iter(appresults)
            
            def __iter__(self):
                return self
            
            def next(self):
                return self.iter.next()
            
            def close(self):
                if hasattr(self.appresults, "close"):
                    self.appresults.close()
        
        
        class ChangeCase(object):
            
            def __init__(self, app, to=None):
                self.app = app
                self.to = to
            
            def __call__(self, environ, start_response):
                res = self.app(environ, start_response)
                class CaseResults(WSGIResponse):
                    def next(this):
                        return getattr(this.iter.next(), self.to)()
                return CaseResults(res)
        
        class Replacer(object):
            
            def __init__(self, app, map={}):
                self.app = app
                self.map = map
            
            def __call__(self, environ, start_response):
                res = self.app(environ, start_response)
                class ReplaceResults(WSGIResponse):
                    def next(this):
                        line = this.iter.next()
                        for k, v in self.map.iteritems():
                            line = line.replace(k, v)
                        return line
                return ReplaceResults(res)
        
        class Root(object):
            
            def index(self):
                return "HellO WoRlD!"
            index.exposed = True
        
        
        root_conf = {'wsgi.pipeline': [('replace', Replacer)],
                     'wsgi.replace.map': {'L': 'X', 'l': 'r'},
                     }
        
        app = cherrypy.Application(Root())
        app.wsgiapp.pipeline.append(('changecase', ChangeCase))
        app.wsgiapp.config['changecase'] = {'to': 'upper'}
        cherrypy.tree.mount(app, config={'/': root_conf})
    setup_server = staticmethod(setup_server)

    
    def test_pipeline(self):
        if not cherrypy.server.httpserver:
            return self.skip()
        
        self.getPage("/")
        # If body is "HEXXO WORXD!", the middleware was applied out of order.
        self.assertBody("HERRO WORRD!")

