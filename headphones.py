#!/usr/bin/env python
import cherrypy
from cherrypy.process.plugins import Daemonizer
from optparse import OptionParser
from configobj import ConfigObj
from configcreate import configCreate
import webbrowser
import sqlite3
import webServer
import logger
import time
from threadtools import threadtool
import os
	


#set up paths

FULL_PATH = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(FULL_PATH, 'config.ini')
LOG_DIR = os.path.join(FULL_PATH, 'logs')


if os.path.exists(config_file):
	pass
else:
	configCreate(config_file)

settings = ConfigObj(config_file)['General']

if not os.access(LOG_DIR, os.F_OK):
	try:
		os.makedirs(LOG_DIR, 0744)
	except:
		print 'Unable to create log dir, logging to screen only'

def initialize():
	database = os.path.join(FULL_PATH, 'headphones.db')
	conn=sqlite3.connect(database)
	c=conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration, TrackID TEXT)')
	c.execute('CREATE TABLE IF NOT EXISTS snatched (AlbumID TEXT, Title TEXT, Size INTEGER, URL TEXT, DateAdded TEXT, Status TEXT)')


def serverstart():  

	parser = OptionParser()
	parser.add_option("-d", "--daemonize", action="store_true", dest="daemonize")
	parser.add_option("-q", "--quiet", action="store_true", dest="quiet")
	
	(options, args) = parser.parse_args()

	consoleLogging=True
	
	if options.quiet or options.daemonize:
		cherrypy.config.update({'log.screen': False})
		consoleLogging=False

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
	cherrypy.engine.timeout_monitor.unsubscribe()

	logger.sb_log_instance.initLogging(consoleLogging=consoleLogging)
	
	
	def browser():
		if settings['http_host'] == '0.0.0.0':
			host = 'localhost'
		else:
			host = settings['http_host']
		webbrowser.open('http://' + host + ':' + settings['http_port'])
		
	
	if settings['launch_browser'] == '1':
		cherrypy.engine.subscribe('start', browser, priority=90)
	
	logger.log(u"Starting Headphones on port:" + settings['http_port'])
	cherrypy.quickstart(webServer.Headphones(), config = conf)
	

if __name__ == '__main__':
	initialize()
	serverstart()
