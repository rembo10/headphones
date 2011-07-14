import platform, subprocess, re

import headphones
from headphones import logger

from pygithub import github


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

	output, err = runGit('rev-parse HEAD')
	
	if not output:
		logger.error('Couldn\'t find latest installed version.')
		return None
		
	cur_commit_hash = output.strip()
	
	if not re.match('^[a-z0-9]+$', cur_commit_hash):
		logger.error('Output doesn\'t look like a hash, not using it')
		return None
		
	return cur_commit_hash

	
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
		
	output, err = runGit('pull origin master')
	
	if not output:
		logger.error('Couldn\'t download latest version')
		
	for line in output.split('\n'):
	
		if 'Already up-to-date.' in line:
			logger.info('No update available, not updating')
			logger.info('Output: ' + str(output))
		elif line.endswith('Aborting.'):
			logger.error('Unable to update from git: '+line)
			logger.info('Output: ' + str(output))

	
	