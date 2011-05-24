from cherrypy.process.plugins import SimplePlugin
from apscheduler.scheduler import Scheduler
import time
import threading
import Queue

class threadtool(SimplePlugin):

	sched = Scheduler()
	thread = None

	def __init__(self, bus):
		SimplePlugin.__init__(self, bus)
			
	def start(self):
		self.running = True
		if not self.thread:
			self.thread = threading.Thread(target=self.run)
			self.thread.start()
		self.sched.start()
	start.priority = 80
		
	def stop(self):
		self.running = False
		if self.thread:
			self.thread.join()
			self.thread = None
		self.sched.shutdown()
	stop.priority = 10
		
	def run(self):
		import updater
		import searcher
		import mover
		#self.sched.add_cron_job(updater.dbUpdate, hour=3)
		#self.sched.add_interval_job(searcher.searchNZB, hours=18)
		#self.sched.add_interval_job(mover.moveFiles, minutes=10)
