#!/usr/bin/env python
import os
import cherrypy
from webServer import Headphones


	
#path to config_file
config_file = os.path.join(os.path.dirname(__file__), 'server.conf')

if __name__ == '__main__':
	cherrypy.quickstart(Headphones(), config=config_file)
	
