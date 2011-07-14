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
Defines and runs unittests.
"""

import urllib
import hashlib
import unittest

import github

class BaseCase(unittest.TestCase):

    def _gh(self, expUrl, filename):

        def opener(url):
            self.assertEquals(expUrl, url)
            return open(filename)
        return github.GitHub(fetcher=opener)

    def _agh(self, expUrl, u, t, filename):

        def opener(url):
            self.assertEquals(expUrl, url + '?login=' + u + '&token=' + t)
            return open(filename)
        return github.GitHub(fetcher=opener)

    def _ghp(self, expUrl, u, t, **kv):

        def opener(url, data):
            h = {'login': u, 'token': t}
            h.update(kv)
            self.assertEquals(github.BaseEndpoint.BASE_URL + expUrl, url)
            self.assertEquals(sorted(data.split('&')),
                              sorted(urllib.urlencode(h).split('&')))
        return github.GitHub(u, t, fetcher=opener)

class UserTest(BaseCase):

    def __loadUserSearch(self):
        return self._gh('http://github.com/api/v2/xml/user/search/dustin',
            'data/user.search.xml').users.search('dustin')

    def __loadUser(self, which, u=None, p=None):
        if u:
            return self._agh('http://github.com/api/v2/xml/user/show/dustin'
                              + '?login=' + u + '&token=' + p,
                              u, p, 'data/' + which).users.show('dustin')

        else:
            return self._gh('http://github.com/api/v2/xml/user/show/dustin',
                             'data/' + which).users.show('dustin')

    def testUserSearch(self):
        """Test the base properties of the user object."""
        u = self.__loadUserSearch()[0]
        self.assertEquals("Dustin Sallings", u.fullname)
        self.assertEquals("dustin", u.name)
        self.assertEquals("dustin@spy.net", u.email)
        self.assertEquals("Santa Clara, CA", u.location)
        self.assertEquals("Ruby", u.language)
        self.assertEquals(35, u.actions)
        self.assertEquals(77, u.repos)
        self.assertEquals(78, u.followers)
        self.assertEquals('user-1779', u.id)
        self.assertAlmostEquals(12.231684, u.score)
        self.assertEquals('user', u.type)
        self.assertEquals('2008-02-29T17:59:09Z', u.created)
        self.assertEquals('2009-03-19T09:15:24.663Z', u.pushed)
        self.assertEquals("<<User dustin>>", repr(u))

    def testUserPublic(self):
        """Test the user show API with no authentication."""
        u = self.__loadUser('user.public.xml')
        self.assertEquals("Dustin Sallings", u.name)
        # self.assertEquals(None, u.company)
        self.assertEquals(10, u.following_count)
        self.assertEquals(21, u.public_gist_count)
        self.assertEquals(81, u.public_repo_count)
        self.assertEquals('http://bleu.west.spy.net/~dustin/', u.blog)
        self.assertEquals(1779, u.id)
        self.assertEquals(82, u.followers_count)
        self.assertEquals('dustin', u.login)
        self.assertEquals('Santa Clara, CA', u.location)
        self.assertEquals('dustin@spy.net', u.email)
        self.assertEquals('2008-02-29T09:59:09-08:00', u.created_at)

    def testUserPrivate(self):
        """Test the user show API with extra info from auth."""
        u = self.__loadUser('user.private.xml', 'dustin', 'blahblah')
        self.assertEquals("Dustin Sallings", u.name)
        # self.assertEquals(None, u.company)
        self.assertEquals(10, u.following_count)
        self.assertEquals(21, u.public_gist_count)
        self.assertEquals(81, u.public_repo_count)
        self.assertEquals('http://bleu.west.spy.net/~dustin/', u.blog)
        self.assertEquals(1779, u.id)
        self.assertEquals(82, u.followers_count)
        self.assertEquals('dustin', u.login)
        self.assertEquals('Santa Clara, CA', u.location)
        self.assertEquals('dustin@spy.net', u.email)
        self.assertEquals('2008-02-29T09:59:09-08:00', u.created_at)

        # Begin private data

        self.assertEquals("micro", u.plan.name)
        self.assertEquals(1, u.plan.collaborators)
        self.assertEquals(614400, u.plan.space)
        self.assertEquals(5, u.plan.private_repos)
        self.assertEquals(155191, u.disk_usage)
        self.assertEquals(6, u.collaborators)
        self.assertEquals(4, u.owned_private_repo_count)
        self.assertEquals(5, u.total_private_repo_count)
        self.assertEquals(0, u.private_gist_count)

    def testKeysList(self):
        """Test key listing."""
        kl = self._agh('http://github.com/api/v2/xml/user/keys?login=dustin&token=blahblah',
                       'dustin', 'blahblah', 'data/keys.xml').users.keys()
        self.assertEquals(7, len(kl))
        k = kl[0]

        self.assertEquals('some key', k.title)
        self.assertEquals(2181, k.id)
        self.assertEquals(549, k.key.find('cdEXwCSjAIFp8iRqh3GOkxGyFSc25qv/MuOBg=='))

    def testRemoveKey(self):
        """Remove a key."""
        self._ghp('user/key/remove',
                  'dustin', 'p', id=828).users.removeKey(828)

    def testAddKey(self):
        """Add a key."""
        self._ghp('user/key/add',
                  'dustin', 'p', name='my key', key='some key').users.addKey(
            'my key', 'some key')

class RepoTest(BaseCase):

    def __loadUserRepos(self):
        return self._gh('http://github.com/api/v2/xml/repos/show/verbal',
            'data/repos.xml').repos.forUser('verbal')

    def testUserRepoList(self):
        """Get a list of repos for a user."""
        rs = self.__loadUserRepos()
        self.assertEquals(10, len(rs))
        r = rs[0]
        self.assertEquals('A beanstalk client for the twisted network framework.',
                          r.description)
        self.assertEquals(2, r.watchers)
        self.assertEquals(0, r.forks)
        self.assertEquals('beanstalk-client-twisted', r.name)
        self.assertEquals(False, r.private)
        self.assertEquals('http://github.com/verbal/beanstalk-client-twisted',
                          r.url)
        self.assertEquals(True, r.fork)
        self.assertEquals('verbal', r.owner)
        # XXX:  Can't parse empty elements.  :(
        # self.assertEquals('', r.homepage)

    def testRepoSearch(self):
        """Test searching a repository."""
        rl = self._gh('http://github.com/api/v2/xml/repos/search/ruby+testing',
                      'data/repos.search.xml').repos.search('ruby testing')
        self.assertEquals(12, len(rl))

        r = rl[0]
        self.assertEquals('synthesis', r.name)
        self.assertAlmostEquals(0.3234576, r.score, 4)
        self.assertEquals(4656, r.actions)
        self.assertEquals(2048, r.size)
        self.assertEquals('Ruby', r.language)
        self.assertEquals(26, r.followers)
        self.assertEquals('gmalamid', r.username)
        self.assertEquals('repo', r.type)
        self.assertEquals('repo-3555', r.id)
        self.assertEquals(1, r.forks)
        self.assertFalse(r.fork)
        self.assertEquals('Ruby test code analysis tool employing a '
                          '"Synthesized Testing" strategy, aimed to reduce '
                          'the volume of slower, coupled, complex wired tests.',
                          r.description)
        self.assertEquals('2009-01-08T13:45:06Z', r.pushed)
        self.assertEquals('2008-03-11T23:38:04Z', r.created)

    def testBranchList(self):
        """Test branch listing for a repo."""
        bl = self._gh('http://github.com/api/v2/xml/repos/show/schacon/ruby-git/branches',
                      'data/repos.branches.xml').repos.branches('schacon', 'ruby-git')
        self.assertEquals(4, len(bl))
        self.assertEquals('ee90922f3da3f67ef19853a0759c1d09860fe3b3', bl['master'])

    def testGetOneRepo(self):
        """Fetch an individual repository."""
        r = self._gh('http://github.com/api/v2/xml/repos/show/schacon/grit',
                     'data/repo.xml').repos.show('schacon', 'grit')

        self.assertEquals('Grit is a Ruby library for extracting information from a '
                          'git repository in an object oriented manner - this fork '
                          'tries to intergrate as much pure-ruby functionality as possible',
                          r.description)
        self.assertEquals(68, r.watchers)
        self.assertEquals(4, r.forks)
        self.assertEquals('grit', r.name)
        self.assertFalse(r.private)
        self.assertEquals('http://github.com/schacon/grit', r.url)
        self.assertTrue(r.fork)
        self.assertEquals('schacon', r.owner)
        self.assertEquals('http://grit.rubyforge.org/', r.homepage)

    def testGetRepoNetwork(self):
        """Test network fetching."""
        nl = self._gh('http://github.com/api/v2/xml/repos/show/dustin/py-github/network',
                      'data/network.xml').repos.network('dustin', 'py-github')
        self.assertEquals(5, len(nl))

        n = nl[0]
        self.assertEquals('Python interface for talking to the github API',
                          n.description)
        self.assertEquals('py-github', n.name)
        self.assertFalse(n.private)
        self.assertEquals('http://github.com/dustin/py-github', n.url)
        self.assertEquals(30, n.watchers)
        self.assertEquals(4, n.forks)
        self.assertFalse(n.fork)
        self.assertEquals('dustin', n.owner)
        self.assertEquals('http://dustin.github.com/2008/12/29/github-sync.html',
                          n.homepage)

    def testSetPublic(self):
        """Test setting a repo visible."""
        self._ghp('repos/set/public/py-github', 'dustin', 'p').repos.setVisible(
            'py-github')

    def testSetPrivate(self):
        """Test setting a repo to private."""
        self._ghp('repos/set/private/py-github', 'dustin', 'p').repos.setVisible(
            'py-github', False)

    def testCreateRepository(self):
        """Test creating a repository."""
        self._ghp('repos/create', 'dustin', 'p',
                  name='testrepo',
                  description='woo',
                  homepage='',
                  public='1').repos.create(
            'testrepo', description='woo')

    def testDeleteRepo(self):
        """Test setting a repo to private."""
        self._ghp('repos/delete/mytest', 'dustin', 'p').repos.delete('mytest')

    def testFork(self):
        """Test forking'"""
        self._ghp('repos/fork/someuser/somerepo', 'dustin', 'p').repos.fork(
            'someuser', 'somerepo')

    def testAddCollaborator(self):
        """Adding a collaborator."""
        self._ghp('repos/collaborators/memcached/add/trondn',
                  'dustin', 'p').repos.addCollaborator('memcached', 'trondn')

    def testRemoveCollaborator(self):
        """Removing a collaborator."""
        self._ghp('repos/collaborators/memcached/remove/trondn',
                  'dustin', 'p').repos.removeCollaborator('memcached', 'trondn')

    def testAddDeployKey(self):
        """Add a deploy key."""
        self._ghp('repos/key/blah/add', 'dustin', 'p',
                  title='title', key='key').repos.addDeployKey('blah', 'title', 'key')

    def testRemoveDeployKey(self):
        """Remove a deploy key."""
        self._ghp('repos/key/blah/remove', 'dustin', 'p',
                  id=5).repos.removeDeployKey('blah', 5)

class CommitTest(BaseCase):

    def testCommitList(self):
        """Test commit list."""
        cl = self._gh('http://github.com/api/v2/xml/commits/list/mojombo/grit/master',
                      'data/commits.xml').commits.forBranch('mojombo', 'grit')
        self.assertEquals(30, len(cl))

        c = cl[0]
        self.assertEquals("Regenerated gemspec for version 1.1.1", c.message)
        self.assertEquals('4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde', c.id)
        self.assertEquals('94490563ebaf733cbb3de4ad659eb58178c2e574', c.tree)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.committed_date)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.authored_date)
        self.assertEquals('http://github.com/mojombo/grit/commit/4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde',
                          c.url)
        self.assertEquals(1, len(c.parents))
        self.assertEquals('5071bf9fbfb81778c456d62e111440fdc776f76c', c.parents[0].id)
        self.assertEquals('Tom Preston-Werner', c.author.name)
        self.assertEquals('tom@mojombo.com', c.author.email)
        self.assertEquals('Tom Preston-Werner', c.committer.name)
        self.assertEquals('tom@mojombo.com', c.committer.email)

    def testCommitListForFile(self):
        """Test commit list for a file."""
        cl = self._gh('http://github.com/api/v2/xml/commits/list/mojombo/grit/master/grit.gemspec',
                      'data/commits.xml').commits.forFile('mojombo', 'grit', 'grit.gemspec')
        self.assertEquals(30, len(cl))

        c = cl[0]
        self.assertEquals("Regenerated gemspec for version 1.1.1", c.message)
        self.assertEquals('4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde', c.id)
        self.assertEquals('94490563ebaf733cbb3de4ad659eb58178c2e574', c.tree)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.committed_date)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.authored_date)
        self.assertEquals('http://github.com/mojombo/grit/commit/4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde',
                          c.url)
        self.assertEquals(1, len(c.parents))
        self.assertEquals('5071bf9fbfb81778c456d62e111440fdc776f76c', c.parents[0].id)
        self.assertEquals('Tom Preston-Werner', c.author.name)
        self.assertEquals('tom@mojombo.com', c.author.email)
        self.assertEquals('Tom Preston-Werner', c.committer.name)
        self.assertEquals('tom@mojombo.com', c.committer.email)

    def testIndividualCommit(self):
        """Grab a single commit."""
        h = '4c86fa592fcc7cb685c6e9d8b6aebe8dcbac6b3e'
        c = self._gh('http://github.com/api/v2/xml/commits/show/dustin/memcached/' + h,
                     'data/commit.xml').commits.show('dustin', 'memcached', h)
        self.assertEquals(['internal_tests.c'], c.removed)
        self.assertEquals(set(['cache.c', 'cache.h', 'testapp.c']), set(c.added))
        self.assertEquals('Create a generic cache for objects of same size\n\n'
                          'The suffix pool could be thread-local and use the generic cache',
                          c.message)

        self.assertEquals(6, len(c.modified))
        self.assertEquals('.gitignore', c.modified[0].filename)
        self.assertEquals(140, len(c.modified[0].diff))

        self.assertEquals(['ee0c3d5ae74d0862b4d9990e2ad13bc79f8c34df'],
                          [p.id for p in c.parents])
        self.assertEquals('http://github.com/dustin/memcached/commit/' + h, c.url)
        self.assertEquals('Trond Norbye', c.author.name)
        self.assertEquals('Trond.Norbye@sun.com', c.author.email)
        self.assertEquals(h, c.id)
        self.assertEquals('2009-04-17T16:15:52-07:00', c.committed_date)
        self.assertEquals('2009-03-27T10:30:16-07:00', c.authored_date)
        self.assertEquals('94b644163f6381a9930e2d7c583fae023895b903', c.tree)
        self.assertEquals('Dustin Sallings', c.committer.name)
        self.assertEquals('dustin@spy.net', c.committer.email)

    def testWatchRepo(self):
        """Test watching a repo."""
        self._ghp('repos/watch/dustin/py-github', 'dustin', 'p').repos.watch(
            'dustin', 'py-github')

    def testWatchRepo(self):
        """Test watching a repo."""
        self._ghp('repos/unwatch/dustin/py-github', 'dustin', 'p').repos.unwatch(
            'dustin', 'py-github')

class IssueTest(BaseCase):

    def testListIssues(self):
        """Test listing issues."""
        il = self._gh('http://github.com/api/v2/xml/issues/list/schacon/simplegit/open',
                      'data/issues.list.xml').issues.list('schacon', 'simplegit')
        self.assertEquals(1, len(il))
        i = il[0]

        self.assertEquals('schacon', i.user)
        self.assertEquals('2009-04-17T16:19:02-07:00', i.updated_at)
        self.assertEquals('something', i.body)
        self.assertEquals('new', i.title)
        self.assertEquals(2, i.number)
        self.assertEquals(0, i.votes)
        self.assertEquals(1.0, i.position)
        self.assertEquals('2009-04-17T16:18:50-07:00', i.created_at)
        self.assertEquals('open', i.state)

    def testShowIssue(self):
        """Show an individual issue."""
        i = self._gh('http://github.com/api/v2/xml/issues/show/dustin/py-github/1',
                     'data/issues.show.xml').issues.show('dustin', 'py-github', 1)

        self.assertEquals('dustin', i.user)
        self.assertEquals('2009-04-17T18:37:04-07:00', i.updated_at)
        self.assertEquals('http://develop.github.com/p/general.html', i.body)
        self.assertEquals('Add auth tokens', i.title)
        self.assertEquals(1, i.number)
        self.assertEquals(0, i.votes)
        self.assertEquals(1.0, i.position)
        self.assertEquals('2009-04-17T17:00:58-07:00', i.created_at)
        self.assertEquals('closed', i.state)

    def testAddLabel(self):
        """Adding a label to an issue."""
        self._ghp('issues/label/add/dustin/py-github/todo/33', 'd', 'pw').issues.add_label(
            'dustin', 'py-github', 33, 'todo')

    def testRemoveLabel(self):
        """Removing a label from an issue."""
        self._ghp('issues/label/remove/dustin/py-github/todo/33',
                  'd', 'pw').issues.remove_label(
            'dustin', 'py-github', 33, 'todo')

    def testCloseIssue(self):
        """Closing an issue."""
        self._ghp('issues/close/dustin/py-github/1', 'd', 'pw').issues.close(
            'dustin', 'py-github', 1)

    def testReopenIssue(self):
        """Reopening an issue."""
        self._ghp('issues/reopen/dustin/py-github/1', 'd', 'pw').issues.reopen(
            'dustin', 'py-github', 1)

    def testCreateIssue(self):
        """Creating an issue."""
        self._ghp('issues/open/dustin/py-github', 'd', 'pw',
                  title='test title', body='').issues.new(
            'dustin', 'py-github', title='test title')

    def testEditIssue(self):
        """Editing an existing issue."""
        self._ghp('issues/edit/dustin/py-github/1', 'd', 'pw',
                  title='new title', body='new body').issues.edit(
            'dustin', 'py-github', 1, 'new title', 'new body')

class ObjectTest(BaseCase):

    def testTree(self):
        """Test tree fetching."""
        h = '1ddd3f99f0b96019042239375b3ad4d45796ffba'
        tl = self._gh('http://github.com/api/v2/xml/tree/show/dustin/py-github/' + h,
                      'data/tree.xml').objects.tree('dustin', 'py-github', h)
        self.assertEquals(8, len(tl))
        self.assertEquals('setup.py', tl['setup.py'].name)
        self.assertEquals('6e290379ec58fa00ac9d1c2a78f0819a21397445',
                          tl['setup.py'].sha)
        self.assertEquals('100755', tl['setup.py'].mode)
        self.assertEquals('blob', tl['setup.py'].type)

        self.assertEquals('src', tl['src'].name)
        self.assertEquals('5fb9175803334c82b3fd66f1b69502691b91cf4f',
                          tl['src'].sha)
        self.assertEquals('040000', tl['src'].mode)
        self.assertEquals('tree', tl['src'].type)

    def testBlob(self):
        """Test blob fetching."""
        h = '1ddd3f99f0b96019042239375b3ad4d45796ffba'
        blob = self._gh('http://github.com/api/v2/xml/blob/show/dustin/py-github/'
                        + h + '/setup.py',
                        'data/blob.xml').objects.blob('dustin', 'py-github', h, 'setup.py')
        self.assertEquals('setup.py', blob.name)
        self.assertEquals(1842, blob.size)
        self.assertEquals('6e290379ec58fa00ac9d1c2a78f0819a21397445', blob.sha)
        self.assertEquals('100755', blob.mode)
        self.assertEquals('text/plain', blob.mime_type)
        self.assertEquals(1842, len(blob.data))
        self.assertEquals(1641, blob.data.index('Production/Stable'))

    def testRawBlob(self):
        """Test raw blob fetching."""
        h = '6e290379ec58fa00ac9d1c2a78f0819a21397445'
        blob = self._gh('http://github.com/api/v2/xml/blob/show/dustin/py-github/' + h,
                        'data/setup.py').objects.raw_blob('dustin', 'py-github', h)
        self.assertEquals('e2dc8aea9ae8961f4f5923f9febfdd0a',
                          hashlib.md5(blob).hexdigest())


if __name__ == '__main__':
    unittest.main()
