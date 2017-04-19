# -*- coding: utf8 -*-
# Copyright (C) 2012-2016 Xyne
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# (version 2) as published by the Free Software Foundation.
#
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
from __future__ import with_statement
import base64
import json
import math
import os
import ssl
import string
import time
import httplib
import urllib2

from headphones import logger

################################## Constants ###################################

DEFAULT_PORT = 6800
SERVER_URI_FORMAT = '{}://{}:{:d}/jsonrpc'

# Status values for unfinished downloads.
TEMPORARY_STATUS = ('active', 'waiting', 'paused')
# Status values for finished downloads.
FINAL_STATUS = ('complete', 'error')

ARIA2_CONTROL_FILE_EXT = '.aria2'

############################ Convenience Functions #############################

def to_json_list(objs):
	'''
	Wrap strings in lists. Other iterables are converted to lists directly.
	'''
	if isinstance(objs, str):
		return [objs]
	elif not isinstance(objs, list):
		return list(objs)
	else:
		return objs



def add_options_and_position(params, options=None, position=None):
	'''
	Convenience method for adding options and position to parameters.
	'''
	if options:
		params.append(options)
	if position:
		if not isinstance(position, int):
			try:
				position = int(position)
			except ValueError:
				position = -1
		if position >= 0:
			params.append(position)
	return params



def get_status(response):
	'''
	Process a status response.
	'''
	if response:
		try:
			return response['status']
		except KeyError:
			logger.error('no status returned from Aria2 RPC server')
			return 'error'
	else:
		logger.error('no response from server')
		return 'error'



def random_token(length, valid_chars=None):
	'''
	Get a random secret token for the Aria2 RPC server.

	length:
		The length of the token

	valid_chars:
		A list or other ordered and indexable iterable of valid characters. If not
		given of None, asciinumberic characters with some punctuation characters
		will be used.
	'''
	if not valid_chars:
		valid_chars = string.ascii_letters + string.digits + '!@#$%^&*()-_=+'
	number_of_chars = len(valid_chars)
	bytes_to_read = math.ceil(math.log(number_of_chars) / math.log(0x100))
	max_value = 0x100**bytes_to_read
	max_index = number_of_chars - 1
	token = ''
	for _ in range(length):
		value = int.from_bytes(os.urandom(bytes_to_read), byteorder='little')
		index = round((value * max_index)/max_value)
		token += valid_chars[index]
	return token


################## From python3-aur's ThreadedServers.common ###################

def format_bytes(size):
	'''Format bytes for inferior humans.'''
	if size < 0x400:
		return '{:d} B'.format(size)
	else:
		size = float(size) / 0x400
	for prefix in ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB'):
		if size < 0x400:
			return '{:0.02f} {}'.format(size, prefix)
		else:
			size /= 0x400
	return '{:0.02f} YiB'.format(size)



def format_seconds(s):
	'''Format seconds for inferior humans.'''
	string = ''
	for base, char in (
		(60, 's'),
		(60, 'm'),
		(24, 'h')
	):
		s, r = divmod(s, base)
		if s == 0:
			return '{:d}{}{}'.format(r, char, string)
		elif r != 0:
			string = '{:02d}{}{}'.format(r, char, string)
	else:
		return '{:d}d{}'.format(s, string)

############################## Aria2JsonRpcError ###############################

class Aria2JsonRpcError(Exception):
	def __init__(self, msg, connection_error=False):
		super(self.__class__, self).__init__(self, msg)
		self.connection_error = connection_error

############################## Aria2JsonRpc Class ##############################

class Aria2JsonRpc(object):
	'''
	Interface class for interacting with an Aria2 RPC server.
	'''
	# TODO: certificate options, etc.
	def __init__(
		self, ID, uri,
		mode='normal',
		token=None,
		http_user=None, http_passwd=None,
		server_cert=None, client_cert=None, client_cert_password=None,
		ssl_protocol=None,
		setup_function=None
	):
		'''
		ID: the ID to send to the RPC interface

		uri: the URI of the RPC interface

		mode:
			normal - process requests immediately
			batch - queue requests (run with "process_queue")
			format - return RPC request objects

		token:
			RPC method-level authorization token (set using `--rpc-secret`)

		http_user, http_password:
			HTTP Basic authentication credentials (deprecated)

		server_cert:
			server certificate for HTTPS connections

		client_cert:
			client certificate for HTTPS connections

		client_cert_password:
			prompt for client certificate password

		ssl_protocol:
			SSL protocol from the ssl module

		setup_function:
			A function to invoke prior to the first server call. This could be the
			launch() method of an Aria2RpcServer instance, for example. This attribute
			is set automatically in instances returned from Aria2RpcServer.get_a2jr()
		'''
		self.id = ID
		self.uri = uri
		self.mode = mode
		self.queue = []
		self.handlers = dict()
		self.token = token
		self.setup_function = setup_function

		if None not in (http_user, http_passwd):
			self.add_HTTPBasicAuthHandler(http_user, http_passwd)

		if server_cert or client_cert:
			self.add_HTTPSHandler(
				server_cert=server_cert,
				client_cert=client_cert,
				client_cert_password=client_cert_password,
				protocol=ssl_protocol
			)

		self.update_opener()



	def iter_handlers(self):
		'''
		Iterate over handlers.
		'''
		for name in ('HTTPS', 'HTTPBasicAuth'):
			try:
				yield self.handlers[name]
			except KeyError:
				pass



	def update_opener(self):
		'''
		Build an opener from the current handlers.
		'''
		self.opener = urllib2.build_opener(*self.iter_handlers())



	def remove_handler(self, name):
		'''
		Remove a handler.
		'''
		try:
			del self.handlers[name]
		except KeyError:
			pass



	def add_HTTPBasicAuthHandler(self, user, passwd):
		'''
		Add a handler for HTTP Basic authentication.

		If either user or passwd are None, the handler is removed.
		'''
		handler = urllib2.HTTPBasicAuthHandler()
		handler.add_password(
			realm='aria2',
			uri=self.uri,
			user=user,
			passwd=passwd,
		)
		self.handlers['HTTPBasicAuth'] = handler



	def remove_HTTPBasicAuthHandler(self):
		self.remove_handler('HTTPBasicAuth')



	def add_HTTPSHandler(
		self,
		server_cert=None,
		client_cert=None,
		client_cert_password=None,
		protocol=None,
	):
		'''
		Add a handler for HTTPS connections with optional server and client
		certificates.
		'''
		if not protocol:
			protocol = ssl.PROTOCOL_TLSv1
#       protocol = ssl.PROTOCOL_TLSv1_1 # openssl 1.0.1+
#       protocol = ssl.PROTOCOL_TLSv1_2 # Python 3.4+
		context = ssl.SSLContext(protocol)

		if server_cert:
			context.verify_mode = ssl.CERT_REQUIRED
			context.load_verify_locations(cafile=server_cert)
		else:
			context.verify_mode = ssl.CERT_OPTIONAL

		if client_cert:
			context.load_cert_chain(client_cert, password=client_cert_password)

		self.handlers['HTTPS'] = urllib2.HTTPSHandler(
			context=context,
			check_hostname=False
		)



	def remove_HTTPSHandler(self):
		self.remove_handler('HTTPS')



	def send_request(self, req_obj):
		'''
		Send the request and return the response.
		'''
		if self.setup_function:
			self.setup_function()
			self.setup_function = None
		logger.debug("Aria req_obj: %s" % json.dumps(req_obj, indent=2, sort_keys=True))
		req = json.dumps(req_obj).encode('UTF-8')
		try:
			f = self.opener.open(self.uri, req)
			obj = json.loads(f.read())
			try:
				return obj['result']
			except KeyError:
				raise Aria2JsonRpcError('unexpected result: {}'.format(obj))
		except (urllib2.URLError) as e:
			# This should work but URLError does not set the errno attribute:
			# e.errno == errno.ECONNREFUSED
			raise Aria2JsonRpcError(
				str(e),
				connection_error=(
					'111' in str(e)
				)
			)
		except httplib.BadStatusLine as e:
			raise Aria2JsonRpcError('{}: BadStatusLine: {} (HTTPS error?)'.format(
				self.__class__.__name__, e
			))



	def jsonrpc(self, method, params=None, prefix='aria2.'):
		'''
		POST a request to the RPC interface.
		'''
		if not params:
			params = []

		if self.token is not None:
			token_str = 'token:{}'.format(self.token)
			if method == 'multicall':
				for p in params[0]:
					try:
						p['params'].insert(0, token_str)
					except KeyError:
						p['params'] = [token_str]
			else:
				params.insert(0, token_str)

		req_obj = {
			'jsonrpc' : '2.0',
			'id' : self.id,
			'method' : prefix + method,
			'params' : params,
		}
		if self.mode == 'batch':
			self.queue.append(req_obj)
			return None
		elif self.mode == 'format':
			return req_obj
		else:
			return self.send_request(req_obj)



	def process_queue(self):
		'''
		Processed queued requests.
		'''
		req_obj = self.queue
		self.queue = []
		return self.send_request(req_obj)



############################### Standard Methods ###############################

	def addUri(self, uris, options=None, position=None):
		'''
		aria2.addUri method

		uris: list of URIs

		options: dictionary of additional options

		position: position in queue

		Returns a GID
		'''
		params = [uris]
		params = add_options_and_position(params, options, position)
		return self.jsonrpc('addUri', params)



	def addTorrent(self, torrent, uris=None, options=None, position=None):
		'''
		aria2.addTorrent method

		torrent: base64-encoded torrent file

		uris: list of webseed URIs

		options: dictionary of additional options

		position: position in queue

		Returns a GID.
		'''
		params = [torrent]
		if uris:
			params.append(uris)
		params = add_options_and_position(params, options, position)
		return self.jsonrpc('addTorrent', params)



	def addMetalink(self, metalink, options=None, position=None):
		'''
		aria2.addMetalink method

		metalink: base64-encoded metalink file

		options: dictionary of additional options

		position: position in queue

		Returns an array of GIDs.
		'''
		params = [metalink]
		params = add_options_and_position(params, options, position)
		return self.jsonrpc('addTorrent', params)



	def remove(self, gid):
		'''
		aria2.remove method

		gid: GID to remove
		'''
		params = [gid]
		return self.jsonrpc('remove', params)



	def forceRemove(self, gid):
		'''
		aria2.forceRemove method

		gid: GID to remove
		'''
		params = [gid]
		return self.jsonrpc('forceRemove', params)



	def pause(self, gid):
		'''
		aria2.pause method

		gid: GID to pause
		'''
		params = [gid]
		return self.jsonrpc('pause', params)



	def pauseAll(self):
		'''
		aria2.pauseAll method
		'''
		return self.jsonrpc('pauseAll')



	def forcePause(self, gid):
		'''
		aria2.forcePause method

		gid: GID to pause
		'''
		params = [gid]
		return self.jsonrpc('forcePause', params)



	def forcePauseAll(self):
		'''
		aria2.forcePauseAll method
		'''
		return self.jsonrpc('forcePauseAll')



	def unpause(self, gid):
		'''
		aria2.unpause method

		gid: GID to unpause
		'''
		params = [gid]
		return self.jsonrpc('unpause', params)



	def unpauseAll(self):
		'''
		aria2.unpauseAll method
		'''
		return self.jsonrpc('unpauseAll')



	def tellStatus(self, gid, keys=None):
		'''
		aria2.tellStatus method

		gid: GID to query

		keys: subset of status keys to return (all keys are returned otherwise)

		Returns a dictionary.
		'''
		params = [gid]
		if keys:
			params.append(keys)
		return self.jsonrpc('tellStatus', params)



	def getUris(self, gid):
		'''
		aria2.getUris method

		gid: GID to query

		Returns a list of dictionaries.
		'''
		params = [gid]
		return self.jsonrpc('getUris', params)



	def getFiles(self, gid):
		'''
		aria2.getFiles method

		gid: GID to query

		Returns a list of dictionaries.
		'''
		params = [gid]
		return self.jsonrpc('getFiles', params)



	def getPeers(self, gid):
		'''
		aria2.getPeers method

		gid: GID to query

		Returns a list of dictionaries.
		'''
		params = [gid]
		return self.jsonrpc('getPeers', params)



	def getServers(self, gid):
		'''
		aria2.getServers method

		gid: GID to query

		Returns a list of dictionaries.
		'''
		params = [gid]
		return self.jsonrpc('getServers', params)



	def tellActive(self, keys=None):
		'''
		aria2.tellActive method

		keys: same as tellStatus

		Returns a list of dictionaries. The dictionaries are the same as those
		returned by tellStatus.
		'''
		if keys:
			params = [keys]
		else:
			params = None
		return self.jsonrpc('tellActive', params)



	def tellWaiting(self, offset, num, keys=None):
		'''
		aria2.tellWaiting method

		offset: offset from start of waiting download queue
						(negative values are counted from the end of the queue)

		num: number of downloads to return

		keys: same as tellStatus

		Returns a list of dictionaries. The dictionaries are the same as those
		returned by tellStatus.
		'''
		params = [offset, num]
		if keys:
			params.append(keys)
		return self.jsonrpc('tellWaiting', params)



	def tellStopped(self, offset, num, keys=None):
		'''
		aria2.tellStopped method

		offset: offset from oldest download (same semantics as tellWaiting)

		num: same as tellWaiting

		keys: same as tellStatus

		Returns a list of dictionaries. The dictionaries are the same as those
		returned by tellStatus.
		'''
		params = [offset, num]
		if keys:
			params.append(keys)
		return self.jsonrpc('tellStopped', params)



	def changePosition(self, gid, pos, how):
		'''
		aria2.changePosition method

		gid: GID to change

		pos: the position

		how: "POS_SET", "POS_CUR" or "POS_END"
		'''
		params = [gid, pos, how]
		return self.jsonrpc('changePosition', params)



	def changeUri(self, gid, fileIndex, delUris, addUris, position=None):
		'''
		aria2.changePosition method

		gid: GID to change

		fileIndex: file to affect (1-based)

		delUris: URIs to remove

		addUris: URIs to add

		position: where URIs are inserted, after URIs have been removed
		'''
		params = [gid, fileIndex, delUris, addUris]
		if position:
			params.append(position)
		return self.jsonrpc('changePosition', params)



	def getOption(self, gid):
		'''
		aria2.getOption method

		gid: GID to query

		Returns a dictionary of options.
		'''
		params = [gid]
		return self.jsonrpc('getOption', params)



	def changeOption(self, gid, options):
		'''
		aria2.changeOption method

		gid: GID to change

		options: dictionary of new options
						 (not all options can be changed for active downloads)
		'''
		params = [gid, options]
		return self.jsonrpc('changeOption', params)



	def getGlobalOption(self):
		'''
		aria2.getGlobalOption method

		Returns a dictionary.
		'''
		return self.jsonrpc('getGlobalOption')



	def changeGlobalOption(self, options):
		'''
		aria2.changeGlobalOption method

		options: dictionary of new options
		'''
		params = [options]
		return self.jsonrpc('changeGlobalOption', params)



	def getGlobalStat(self):
		'''
		aria2.getGlobalStat method

		Returns a dictionary.
		'''
		return self.jsonrpc('getGlobalStat')



	def purgeDownloadResult(self):
		'''
		aria2.purgeDownloadResult method
		'''
		self.jsonrpc('purgeDownloadResult')



	def removeDownloadResult(self, gid):
		'''
		aria2.removeDownloadResult method

		gid: GID to remove
		'''
		params = [gid]
		return self.jsonrpc('removeDownloadResult', params)



	def getVersion(self):
		'''
		aria2.getVersion method

		Returns a dictionary.
		'''
		return self.jsonrpc('getVersion')



	def getSessionInfo(self):
		'''
		aria2.getSessionInfo method

		Returns a dictionary.
		'''
		return self.jsonrpc('getSessionInfo')



	def shutdown(self):
		'''
		aria2.shutdown method
		'''
		return self.jsonrpc('shutdown')



	def forceShutdown(self):
		'''
		aria2.forceShutdown method
		'''
		return self.jsonrpc('forceShutdown')



	def multicall(self, methods):
		'''
		aria2.multicall method

		methods: list of dictionaries (keys: methodName, params)

		The method names must be those used by Aria2c, e.g. "aria2.tellStatus".
		'''
		return self.jsonrpc('multicall', [methods], prefix='system.')




############################# Convenience Methods ##############################

	def add_torrent(self, path, uris=None, options=None, position=None):
		'''
		A wrapper around addTorrent for loading files.
		'''
		with open(path, 'r') as f:
			torrent = base64.encode(f.read())
		return self.addTorrent(torrent, uris, options, position)



	def add_metalink(self, path, uris=None, options=None, position=None):
		'''
		A wrapper around addMetalink for loading files.
		'''
		with open(path, 'r') as f:
			metalink = base64.encode(f.read())
		return self.addMetalink(metalink, uris, options, position)



	def get_status(self, gid):
		'''
		Get the status of a single GID.
		'''
		response = self.tellStatus(gid, ['status'])
		return get_status(response)



	def wait_for_final_status(self, gid, interval=1):
		'''
		Wait for a GID to complete or fail and return its status.
		'''
		if not interval or interval < 0:
			interval = 1
		while True:
			status = self.get_status(gid)
			if status in TEMPORARY_STATUS:
				time.sleep(interval)
			else:
				return status



	def get_statuses(self, gids):
		'''
		Get the status of multiple GIDs. The status of each is yielded in order.
		'''
		methods = [
			{
				'methodName' : 'aria2.tellStatus',
				'params' : [gid, ['gid', 'status']]
			}
			for gid in gids
		]
		results = self.multicall(methods)
		if results:
			status = dict((r[0]['gid'], r[0]['status']) for r in results)
			for gid in gids:
				try:
					yield status[gid]
				except KeyError:
					logger.error('Aria2 RPC server returned no status for GID {}'.format(gid))
					yield 'error'
		else:
			logger.error('no response from Aria2 RPC server')
			for gid in gids:
				yield 'error'



	def wait_for_final_statuses(self, gids, interval=1):
		'''
		Wait for multiple GIDs to complete or fail and return their statuses in
		order.

		gids:
			A flat list of GIDs.
		'''
		if not interval or interval < 0:
			interval = 1
		statusmap = dict((g, None) for g in gids)
		remaining = list(
			g for g,s in statusmap.items() if s is None
		)
		while remaining:
			for g, s in zip(remaining, self.get_statuses(remaining)):
				if s in TEMPORARY_STATUS:
					continue
				else:
					statusmap[g] = s
			remaining = list(
				g for g,s in statusmap.items() if s is None
			)
			if remaining:
				time.sleep(interval)
		for g in gids:
			yield statusmap[g]



	def print_global_status(self):
		'''
		Print global status of the RPC server.
		'''
		status = self.getGlobalStat()
		if status:
			numWaiting = int(status['numWaiting'])
			numStopped = int(status['numStopped'])
			keys = ['totalLength', 'completedLength']
			total = self.tellActive(keys)
			waiting = self.tellWaiting(0, numWaiting, keys)
			if waiting:
				total += waiting
			stopped = self.tellStopped(0, numStopped, keys)
			if stopped:
				total += stopped

			downloadSpeed = int(status['downloadSpeed'])
			uploadSpeed = int(status['uploadSpeed'])
			totalLength = sum(int(x['totalLength']) for x in total)
			completedLength = sum(int(x['completedLength']) for x in total)
			remaining = totalLength - completedLength

			status['downloadSpeed'] = format_bytes(downloadSpeed) + '/s'
			status['uploadSpeed'] = format_bytes(uploadSpeed) + '/s'

			preordered = ('downloadSpeed', 'uploadSpeed')

			rows = list()
			for k in sorted(status):
				if k in preordered:
					continue
				rows.append((k, status[k]))

			rows.extend((x, status[x]) for x in preordered)

			if totalLength > 0:
				rows.append(('total', format(format_bytes(totalLength))))
				rows.append(('completed', format(format_bytes(completedLength))))
				rows.append(('remaining', format(format_bytes(remaining))))
				if completedLength == totalLength:
					eta = 'finished'
				else:
					try:
						eta = format_seconds(remaining // downloadSpeed)
					except ZeroDivisionError:
						eta = 'never'
				rows.append(('ETA', eta))

			l = max(len(r[0]) for r in rows)
			r = max(len(r[1]) for r in rows)
			r = max(r, len(self.uri) - (l + 2))
			fmt = '{:<' + str(l) + 's}  {:>' + str(r) + 's}'

			print(self.uri)
			for k, v in rows:
				print(fmt.format(k, v))



	def queue_uris(self, uris, options, interval=None):
		'''
		Enqueue URIs and wait for download to finish while printing status at
		regular intervals.
		'''
		gid = self.addUri(uris, options)
		print('GID: {}'.format(gid))

		if gid and interval is not None:
			blanker = ''
			while True:
				response = self.tellStatus(gid, ['status'])
				if response:
					try:
						status = response['status']
					except KeyError:
						print('error: no status returned from Aria2 RPC server')
						break
					print('{}\rstatus: {}'.format(blanker, status)),
					blanker = ' ' * len(status)
					if status in TEMPORARY_STATUS:
						time.sleep(interval)
					else:
						break
				else:
					print('error: no response from server')
					break



######################### Polymethod download handlers #########################

	def polymethod_enqueue_many(self, downloads):
		'''
		Enqueue downloads.

		downloads: Same as polymethod_download().
		'''
		methods = list(
			{
				'methodName': 'aria2.{}'.format(d[0]),
				'params': list(d[1:])
			} for d in downloads
		)
		return self.multicall(methods)



	def polymethod_wait_many(self, gids, interval=1):
		'''
		Wait for the GIDs to complete or fail and return their statuses.

		gids:
			A list of lists of GIDs.
		'''
		# The flattened list of GIDs
		gs = list(g for gs in gids for g in gs)
		statusmap = dict(tuple(zip(
			gs,
			self.wait_for_final_statuses(gs, interval=interval)
		)))
		for gs in gids:
			yield list(statusmap.get(g, 'error') for g in gs)




	def polymethod_enqueue_one(self, download):
		'''
		Same as polymethod_enqueue_many but for one element.
		'''
		return getattr(self, download[0])(*download[1:])



	def polymethod_download(self, downloads, interval=1):
		'''
		Enqueue a series of downloads and wait for them to finish. Iterate over the
		status of each, in order.

		downloads:
			An iterable over (<type>, <args>, ...) where <type> indicates the "add"
			method to use ('addUri', 'addTorrent', 'addMetalink') and everything that
			follows are arguments to pass to that method.

		interval:
			The status check interval while waiting.

		Iterates over the download status of finished downloads. "complete"
		indicates success. Lists of statuses will be returned for downloads that
		create multiple GIDs (e.g. metalinks).
		'''
		gids = self.polymethod_enqueue_many(downloads)
		return self.polymethod_wait_many(gids, interval=interval)



	def polymethod_download_bool(self, *args, **kwargs):
		'''
		A wrapper around polymethod_download() which returns a boolean for each
		download to indicate success (True) or failure (False).
		'''
#     for status in self.polymethod_download(*args, **kwargs):
#       yield all(s == 'complete' for s in status)
		return list(
			all(s == 'complete' for s in status)
			for status in self.polymethod_download(*args, **kwargs)
		)
	