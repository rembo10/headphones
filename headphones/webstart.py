import os
import sys

import cherrypy

import headphones

from headphones.webserve import WebInterface

def initialize(options={}):


	cherrypy.config.update({
				'log.screen':			False,
				'server.thread_pool': 	10,
				'server.socket_port': 	options['http_port'],
				'server.socket_host': 	options['http_host'],
				'engine.autoreload_on':	False,
		})

	conf = {
		'/': {
            'tools.staticdir.root': os.path.join(headphones.PROG_DIR, 'data')
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
        	'tools.staticfile.filename': "images/favicon.ico"
        }
    }
    
    
	if options['http_password'] != "":
		conf['/'].update({
			'tools.auth_basic.on': True,
    		'tools.auth_basic.realm': 'Headphones',
    		'tools.auth_basic.checkpassword':  cherrypy.lib.auth_basic.checkpassword_dict(
    				{options['http_username']:options['http_password']})
		})
		

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
	
	