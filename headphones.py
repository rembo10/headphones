#!/usr/bin/env python
import cherrypy
from cherrypy.process.plugins import Daemonizer
from optparse import OptionParser
from configobj import ConfigObj
from configcreate import configCreate
import webServer
import time
from threadtools import threadtool
import os
	


#set up paths

FULL_PATH = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(FULL_PATH, 'config.ini')
db = os.path.join(FULL_PATH, 'headphones.db')


if os.path.exists(config_file):
	pass
else:
	configCreate(config_file)

settings = ConfigObj(config_file)['General']


def serverstart():  

	parser = OptionParser()
	parser.add_option("-d", "--daemonize", action="store_true", dest="daemonize")
	parser.add_option("-q", "--quiet", action="store_true", dest="quiet")
	
	(options, args) = parser.parse_args()
	
	if options.quiet or options.daemonize:
		cherrypy.config.update({'log.screen': False})

	cherrypy.config.update({
			'server.thread_pool': 10,
			'server.socket_port': int(settings['http_port']),
			'server.socket_host': settings['http_host']
    	})

	conf = {
		'/': {
            'tools.staticdir.root': FULL_PATH
        },
        '/data/images':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "data/images"
        },
        '/data/css':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "data/css"
        },
        '/data/js':{
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "data/js"
        }
    }
    
    
	if settings['http_password'] != "":
		conf['/'].update({
			'tools.auth_basic.on': True,
    		'tools.auth_basic.realm': 'mordor',
    		'tools.auth_basic.checkpassword':  cherrypy.lib.auth_basic.checkpassword_dict(
    				{settings['http_username']:settings['http_password']})
		})
		
	if options.daemonize:
		Daemonizer(cherrypy.engine).subscribe()


	#Start threads
	threadtool(cherrypy.engine).subscribe()
	
	cherrypy.quickstart(webServer.Headphones(), config = conf)
	

if __name__ == '__main__':
	serverstart()
