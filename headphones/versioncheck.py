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

import tarfile
import platform
import subprocess

import re
import os
import headphones
from headphones import logger, version, request


def runGit(args):
    if headphones.CONFIG.GIT_PATH:
        git_locations = ['"' + headphones.CONFIG.GIT_PATH + '"']
    else:
        git_locations = ['git']

    if platform.system().lower() == 'darwin':
        git_locations.append('/usr/local/git/bin/git')

    output = err = None

    for cur_git in git_locations:
        cmd = cur_git + ' ' + args

        try:
            logger.debug('Trying to execute: "' + cmd + '" with shell in ' + headphones.PROG_DIR)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                 cwd=headphones.PROG_DIR)
            output, err = p.communicate()
            output = output.strip()

            logger.debug('Git output: ' + output)
        except OSError:
            logger.debug('Command failed: %s', cmd)
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
    if version.HEADPHONES_VERSION.startswith('win32build'):
        headphones.INSTALL_TYPE = 'win'

        # Don't have a way to update exe yet, but don't want to set VERSION to None
        return 'Windows Install', 'master'

    elif os.path.isdir(os.path.join(headphones.PROG_DIR, '.git')):

        headphones.INSTALL_TYPE = 'git'
        output, err = runGit('rev-parse HEAD')

        if not output:
            logger.error('Couldn\'t find latest installed version.')
            cur_commit_hash = None

        cur_commit_hash = str(output)

        if not re.match('^[a-z0-9]+$', cur_commit_hash):
            logger.error('Output doesn\'t look like a hash, not using it')
            cur_commit_hash = None

        if headphones.CONFIG.DO_NOT_OVERRIDE_GIT_BRANCH and headphones.CONFIG.GIT_BRANCH:
            branch_name = headphones.CONFIG.GIT_BRANCH

        else:
            branch_name, err = runGit('rev-parse --abbrev-ref HEAD')
            branch_name = branch_name

            if not branch_name and headphones.CONFIG.GIT_BRANCH:
                logger.error(
                    'Could not retrieve branch name from git. Falling back to %s' % headphones.CONFIG.GIT_BRANCH)
                branch_name = headphones.CONFIG.GIT_BRANCH
            if not branch_name:
                logger.error('Could not retrieve branch name from git. Defaulting to master')
                branch_name = 'master'

        return cur_commit_hash, branch_name

    else:

        headphones.INSTALL_TYPE = 'source'

        version_file = os.path.join(headphones.PROG_DIR, 'version.txt')

        if not os.path.isfile(version_file):
            return None, 'master'

        with open(version_file, 'r') as f:
            current_version = f.read().strip(' \n\r')

        if current_version:
            return current_version, headphones.CONFIG.GIT_BRANCH
        else:
            return None, 'master'


def checkGithub():
    headphones.COMMITS_BEHIND = 0

    # Get the latest version available from github
    logger.info('Retrieving latest version information from GitHub')
    url = 'https://api.github.com/repos/%s/headphones/commits/%s' % (
    headphones.CONFIG.GIT_USER, headphones.CONFIG.GIT_BRANCH)
    version = request.request_json(url, timeout=20, validator=lambda x: type(x) == dict)

    if version is None:
        logger.warn(
            'Could not get the latest version from GitHub. Are you running a local development version?')
        return headphones.CURRENT_VERSION

    headphones.LATEST_VERSION = version['sha']
    logger.debug("Latest version is %s", headphones.LATEST_VERSION)

    # See how many commits behind we are
    if not headphones.CURRENT_VERSION:
        logger.info(
            'You are running an unknown version of Headphones. Run the updater to identify your version')
        return headphones.LATEST_VERSION

    if headphones.LATEST_VERSION == headphones.CURRENT_VERSION:
        logger.info('Headphones is up to date')
        return headphones.LATEST_VERSION

    logger.info('Comparing currently installed version with latest GitHub version')
    url = 'https://api.github.com/repos/%s/headphones/compare/%s...%s' % (
    headphones.CONFIG.GIT_USER, headphones.LATEST_VERSION, headphones.CURRENT_VERSION)
    commits = request.request_json(url, timeout=20, whitelist_status_code=404,
                                   validator=lambda x: type(x) == dict)

    if commits is None:
        logger.warn('Could not get commits behind from GitHub.')
        return headphones.LATEST_VERSION

    try:
        headphones.COMMITS_BEHIND = int(commits['behind_by'])
        logger.debug("In total, %d commits behind", headphones.COMMITS_BEHIND)
    except KeyError:
        logger.info('Cannot compare versions. Are you running a local development version?')
        headphones.COMMITS_BEHIND = 0

    if headphones.COMMITS_BEHIND > 0:
        logger.info(
            'New version is available. You are %s commits behind' % headphones.COMMITS_BEHIND)
    elif headphones.COMMITS_BEHIND == 0:
        logger.info('Headphones is up to date')

    return headphones.LATEST_VERSION


def update():
    if headphones.INSTALL_TYPE == 'win':
        logger.info('Windows .exe updating not supported yet.')

    elif headphones.INSTALL_TYPE == 'git':
        output, err = runGit('pull origin ' + headphones.CONFIG.GIT_BRANCH)

        if not output:
            logger.error('Couldn\'t download latest version')

        for line in output.split('\n'):

            if 'Already up-to-date.' in line:
                logger.info('No update available, not updating')
                logger.info('Output: ' + str(output))
            elif line.endswith('Aborting.'):
                logger.error('Unable to update from git: ' + line)
                logger.info('Output: ' + str(output))

    else:
        tar_download_url = 'https://github.com/%s/headphones/tarball/%s' % (
        headphones.CONFIG.GIT_USER, headphones.CONFIG.GIT_BRANCH)
        update_dir = os.path.join(headphones.PROG_DIR, 'update')
        version_path = os.path.join(headphones.PROG_DIR, 'version.txt')

        logger.info('Downloading update from: ' + tar_download_url)
        data = request.request_content(tar_download_url)

        if not data:
            logger.error("Unable to retrieve new version from '%s', can't update", tar_download_url)
            return

        download_name = headphones.CONFIG.GIT_BRANCH + '-github'
        tar_download_path = os.path.join(headphones.PROG_DIR, download_name)

        # Save tar to disk
        with open(tar_download_path, 'wb') as f:
            f.write(data)

        # Extract the tar to update folder
        logger.info('Extracting file: ' + tar_download_path)
        tar = tarfile.open(tar_download_path)
        tar.extractall(update_dir)
        tar.close()

        # Delete the tar.gz
        logger.info('Deleting file: ' + tar_download_path)
        os.remove(tar_download_path)

        # Find update dir name
        update_dir_contents = [x for x in os.listdir(update_dir) if
                               os.path.isdir(os.path.join(update_dir, x))]
        if len(update_dir_contents) != 1:
            logger.error("Invalid update data, update failed: " + str(update_dir_contents))
            return
        content_dir = os.path.join(update_dir, update_dir_contents[0])

        # walk temp folder and move files to main folder
        for dirname, dirnames, filenames in os.walk(content_dir):
            dirname = dirname[len(content_dir) + 1:]
            for curfile in filenames:
                old_path = os.path.join(content_dir, dirname, curfile)
                new_path = os.path.join(headphones.PROG_DIR, dirname, curfile)

                if os.path.isfile(new_path):
                    os.remove(new_path)
                os.renames(old_path, new_path)

        # Update version.txt
        try:
            with open(version_path, 'w') as f:
                f.write(str(headphones.LATEST_VERSION))
        except IOError as e:
            logger.error(
                "Unable to write current version to version.txt, update not complete: %s",
                e
            )
            return
