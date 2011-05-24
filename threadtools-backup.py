from cherrypy.process.plugins import SimplePlugin
import time
import threading
import Queue

class threadtool(SimplePlugin):

	thread = None

	def __init__(self, bus):
		SimplePlugin.__init__(self, bus)
			
	def start(self):
		self.running = True
		if not self.thread:
			self.thread = threading.Thread(target=self.run)
			self.thread.start()
		
	def stop(self):
		self.running = False
			
		if self.thread:
			self.thread.join()
			self.thread = None
		self.running = False
		
	def run(self):
		while self.running:
			from webServer import database
			import updater
			updater.dbUpdate(database)
			time.sleep(3600*24)
