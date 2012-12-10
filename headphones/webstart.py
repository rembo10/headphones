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
import sys

import cherrypy

import headphones

from headphones.webserve import WebInterface

def initialize(options={}):


    cherrypy.config.update({
                'log.screen':           False,
                'server.thread_pool':   10,
                'server.socket_port':   options['http_port'],
                'server.socket_host':   options['http_host'],
                'engine.autoreload_on': False,
                'tools.encode.on' : True,
                'tools.encode.encoding' : 'utf-8',
                'tools.decode.on' : True,
        })

    conf = {
        '/': {
            'tools.staticdir.root': os.path.join(headphones.PROG_DIR, 'data'),
            'tools.proxy.on': options['http_proxy']  # pay attention to X-Forwarded-Proto header
        },
        '/interfaces':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces"
        },
        '/images':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "images"
        },
        '/css':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "css"
        },
        '/js':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "js"
        },
        '/favicon.ico':{
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(os.path.abspath(os.curdir),"images" + os.sep + "favicon.ico")
        },
        '/cache':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': headphones.CACHE_DIR
        }
    }
    
    # If no user is configured there is still an empty string element in the dict which we have to ignore
    if len(options['http_user_dict']) > 0 and not options['http_user_dict'].has_key(''):
        conf['/'].update({
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'Headphones',
            'tools.auth_basic.checkpassword':  cherrypy.lib.auth_basic.checkpassword_dict(
                headphones.HTTP_USER_DICT)
        })
        conf['/api'] = { 'tools.auth_basic.on': False }
        

    # Prevent time-outs
    cherrypy.engine.timeout_monitor.unsubscribe()
    
    cherrypy.tree.mount(WebInterface(), options['http_root'], config = conf)
    
    try:
        cherrypy.process.servers.check_port(options['http_host'], options['http_port'])
        cherrypy.server.start()
    except IOError:
        print 'Failed to start on port: %i. Is something else running?' % (options['http_port'])
        sys.exit(0)
    
    cherrypy.server.wait()
    
    
