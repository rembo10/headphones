#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Grab all of a user's projects from github.
"""

import os
import sys
import subprocess

import github

def check_for_old_format(path, url):
    p = subprocess.Popen(['git', '--git-dir=' + path, 'config',
        'remote.origin.fetch'], stdout = subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stdout.strip() != '+refs/*:refs/*':
        print "Not properly configured for mirroring, repairing."
        subprocess.call(['git', '--git-dir=' + path, 'remote', 'rm', 'origin'])
        add_mirror(path, url)

def add_mirror(path, url):
    subprocess.call(['git', '--git-dir=' + path, 'remote', 'add', '--mirror',
            'origin', url])

def sync(path, url, repo_name):
    p = os.path.join(path, repo_name) + ".git"
    print "Syncing %s -> %s" % (repo_name, p)
    if not os.path.exists(p):
        subprocess.call(['git', 'clone', '--bare', url, p])
        add_mirror(p, url)
    check_for_old_format(p, url)
    subprocess.call(['git', '--git-dir=' + p, 'fetch', '-f'])

def sync_user_repo(path, repo):
    sync(path, "git://github.com/%s/%s" % (repo.owner, repo.name), repo.name)

def usage():
    sys.stderr.write("Usage:  %s username destination_url\n" % sys.argv[0])
    sys.stderr.write(
        """Ensures you've got the latest stuff for the given user.

Also, if the file $HOME/.github-private exists, it will be read for
additional projects.

Each line must be a simple project name (e.g. py-github), a tab character,
and a git URL.
""")

if __name__ == '__main__':
    try:
        user, path = sys.argv[1:]
    except ValueError:
        usage()
        exit(1)

    privfile = os.path.join(os.getenv("HOME"), ".github-private")
    if os.path.exists(privfile):
        f = open(privfile)
        for line in f:
            name, url = line.strip().split("\t")
            sync(path, url, name)

    gh = github.GitHub()

    for repo in gh.repos.forUser(user):
        sync_user_repo(path, repo)
