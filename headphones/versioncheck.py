import platform, subprocess, re, os

import urllib2
import tarfile

import headphones
from headphones import logger, version

from lib.pygithub import github


def runGit(args):

	if headphones.GIT_PATH:
		git_locations = ['"'+headphones.GIT_PATH+'"']
	else:
		git_locations = ['git']
		
	if platform.system().lower() == 'darwin':
		git_locations.append('/usr/local/git/bin/git')
		
	
	output = err = None
	
	for cur_git in git_locations:
	
		cmd = cur_git+' '+args
	
		try:
			logger.debug('Trying to execute: "' + cmd + '" with shell in ' + headphones.PROG_DIR)
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=headphones.PROG_DIR)
			output, err = p.communicate()
			logger.debug('Git output: ' + output)
		except OSError:
			logger.debug('Command ' + cmd + ' didn\'t work, couldn\'t find git')
			continue
			
		if 'not found' in output or "not recognized as an internal or external command" in output:
			logger.debug('Unable to find git with command ' + cmd)
			output = None
		elif 'fatal:' in output or err:
			logger.error('Git returned bad info. Are you sure this is a git installation?')
			output = None
		elif output:
			break
			
	return (output, err)
			
def getVersion():

	if version.HEADPHONES_VERSION.startswith('build '):
		
		headphones.INSTALL_TYPE = 'win'
		
		# Don't have a way to update exe yet, but don't want to set VERSION to None
		return 'Windows Install'
	
	elif os.path.isdir(os.path.join(headphones.PROG_DIR, '.git')):
	
		headphones.INSTALL_TYPE = 'git'
		output, err = runGit('rev-parse HEAD')
		
		if not output:
			logger.error('Couldn\'t find latest installed version.')
			return None
			
		cur_commit_hash = output.strip()
		
		if not re.match('^[a-z0-9]+$', cur_commit_hash):
			logger.error('Output doesn\'t look like a hash, not using it')
			return None
			
		return cur_commit_hash
		
	else:
		
		headphones.INSTALL_TYPE = 'source'
		
		version_file = os.path.join(headphones.PROG_DIR, 'version.txt')
		
		if not os.path.isfile(version_file):
			return None
	
		fp = open(version_file, 'r')
		current_version = fp.read().strip(' \n\r')
		fp.close()
		
		if current_version:
			return current_version
		else:
			return None
	
def checkGithub():

	commits_behind = 0
	cur_commit = headphones.CURRENT_VERSION
	latest_commit = None

	gh = github.GitHub()
	
	for curCommit in gh.commits.forBranch('rembo10', 'headphones', 'master'):
		if not latest_commit:
			latest_commit = curCommit.id
			if not cur_commit:
				break
		
		if curCommit.id == cur_commit:
			break
			
		commits_behind += 1
		
	headphones.LATEST_VERSION = latest_commit
	headphones.COMMITS_BEHIND = commits_behind
		
	if headphones.LATEST_VERSION == headphones.CURRENT_VERSION:
		logger.info('Headphones is already up-to-date.')
		

	
def update():

	
	if headphones.INSTALL_TYPE == 'win':
	
		logger.info('Windows .exe updating not supported yet.')
		pass
	

	elif headphones.INSTALL_TYPE == 'git':
		
		output, err = runGit('pull origin ' + version.HEADPHONES_VERSION)
		
		if not output:
			logger.error('Couldn\'t download latest version')
			
		for line in output.split('\n'):
		
			if 'Already up-to-date.' in line:
				logger.info('No update available, not updating')
				logger.info('Output: ' + str(output))
			elif line.endswith('Aborting.'):
				logger.error('Unable to update from git: '+line)
				logger.info('Output: ' + str(output))
				
	else:
	
		tar_download_url = 'http://github.com/rembo10/headphones/tarball'+version.HEADPHONES_VERSION
		update_dir = os.path.join(headphones.PROG_DIR, 'update')
		version_path = os.path.join(headphones.PROG_DIR, 'version.txt')
		
		try:
			logger.info('Downloading update from: '+tar_download_url)
			data = urllib2.urlopen(tar_download_url)
		except (IOError, URLError):
			logger.error("Unable to retrieve new version from "+tar_download_url+", can't update")
			return
			
		download_name = data.geturl().split('/')[-1]
		
		tar_download_path = os.path.join(headphones.PROG_DIR, download_name)
		
		# Save tar to disk
		f = open(tar_download_path, 'wb')
		f.write(data.read())
		f.close()
		
		# Extract the tar to update folder
		logger.info('Extracing file' + tar_download_path)
		tar = tarfile.open(tar_download_path)
		tar.extractall(update_dir)
		tar.close()
		
		# Delete the tar.gz
		logger.info('Deleting file' + tar_download_path)
		os.remove(tar_download_path)
		
		# Find update dir name
		update_dir_contents = [x for x in os.listdir(update_dir) if os.path.isdir(os.path.join(update_dir, x))]
		if len(update_dir_contents) != 1:
			logger.error(u"Invalid update data, update failed: "+str(update_dir_contents))
			return
		content_dir = os.path.join(update_dir, update_dir_contents[0])
		
		# walk temp folder and move files to main folder
		for dirname, dirnames, filenames in os.walk(content_dir):
			dirname = dirname[len(content_dir)+1:]
			for curfile in filenames:
				old_path = os.path.join(content_dir, dirname, curfile)
				new_path = os.path.join(headphones.PROG_DIR, dirname, curfile)
				
				if os.path.isfile(new_path):
					os.remove(new_path)
				os.renames(old_path, new_path)
				
		# Update version.txt
		try:
			ver_file = open(version_path, 'w')
			ver_file.write(headphones.LATEST_VERSION)
			ver_file.close()
		except IOError, e:
			logger.error(u"Unable to write version file, update not complete: "+ex(e))
			return