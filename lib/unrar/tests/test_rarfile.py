# -*- coding: utf-8 -*-

# Copyright (C) 2012  Matias Bordese
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile
import unittest

from unrar.rarfile import (
    BadRarFile,
    RarFile,
    RarInfo,
    b,
    is_rarfile,
)


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))


class TestIsRarFile(unittest.TestCase):

    def test_rar_israrfile(self):
        rar_filename = os.path.join(TESTS_DIR, 'test_rar.rar')
        self.assertTrue(is_rarfile(rar_filename))

    def test_no_rar_israrfile(self):
        another_file = os.path.join(TESTS_DIR, '__init__.py')
        self.assertFalse(is_rarfile(another_file))

    def test_no_exists_israrfile(self):
        another_file = os.path.join(TESTS_DIR, 'foo.rar')
        self.assertFalse(is_rarfile(another_file))


class TestRarFile(unittest.TestCase):

    def setUp(self):
        super(TestRarFile, self).setUp()
        self.rar = self._open_rarfile()

    def _open_rarfile(self):
        rar_filename = os.path.join(TESTS_DIR, 'test_rar.rar')
        rar = RarFile(rar_filename)
        return rar

    def test_namelist(self):
        names = self.rar.namelist()
        self.assertEqual(names, ['test_file.txt'])

    def test_testrar(self):
        self.assertIsNone(self.rar.testrar())

    def test_getinfo(self):
        info = self.rar.getinfo('test_file.txt')
        self.assertIsInstance(info, RarInfo)
        self.assertEqual(info.filename, 'test_file.txt')
        self.assertEqual(info.file_size, 17)

    def test_getinfo_no_file(self):
        with self.assertRaises(KeyError) as ctx:
            self.rar.getinfo('foo.txt')

        self.assertEqual(
            ctx.exception.args[0],
            "There is no item named 'foo.txt' in the archive")

    def test_infolist(self):
        infolist = self.rar.infolist()
        self.assertEqual(len(infolist), 1)
        self.assertEqual(infolist[0], self.rar.getinfo('test_file.txt'))

    def test_extract(self):
        dest_dir = tempfile.gettempdir()
        path = self.rar.extract('test_file.txt', path=dest_dir)
        self.addCleanup(os.remove, path)
        with open(path, 'r') as extracted_file:
            extracted_data = extracted_file.read()
            self.assertEqual(extracted_data, "This is for test.")

    def test_extractall(self):
        dest_dir = tempfile.gettempdir()
        self.rar.extractall(path=dest_dir)
        extracted_path = os.path.join(dest_dir, 'test_file.txt')
        self.addCleanup(os.remove, extracted_path)
        with open(extracted_path, 'r') as extracted_file:
            extracted_data = extracted_file.read()
            self.assertEqual(extracted_data, "This is for test.")

    def test_extract_to_memory(self):
        extracted_file = self.rar.open('test_file.txt')
        extracted_data = extracted_file.read()
        # data are bytes
        self.assertEqual(extracted_data, b("This is for test."))

    def test_read_to_memory(self):
        extracted_data = self.rar.read('test_file.txt')
        # data are bytes
        self.assertEqual(extracted_data, b("This is for test."))


class TestPasswordRarFile(TestRarFile):

    def _open_rarfile(self):
        rar_filename = os.path.join(TESTS_DIR, 'test_password.rar')
        rar = RarFile(rar_filename, pwd='password')
        return rar


class TestRarSetPasswordFile(TestRarFile):

    def _open_rarfile(self):
        rar_filename = os.path.join(TESTS_DIR, 'test_password.rar')
        rar = RarFile(rar_filename)
        rar.setpassword('password')
        return rar


class TestCorruptedRar(TestRarFile):

    def _open_rarfile(self):
        rar_filename = os.path.join(TESTS_DIR, 'test_corrupted.rar')
        rar = RarFile(rar_filename)
        rar.setpassword('testing')
        return rar

    def test_testrar(self):
        self.assertEqual(self.rar.testrar(), 'test_file.txt')

    def test_extract(self):
        with self.assertRaises(BadRarFile):
            super(TestCorruptedRar, self).test_extract()

    def test_extractall(self):
        with self.assertRaises(BadRarFile):
            super(TestCorruptedRar, self).test_extractall()

    def test_extract_to_memory(self):
        with self.assertRaises(BadRarFile):
            super(TestCorruptedRar, self).test_extract_to_memory()

    def test_read_to_memory(self):
        with self.assertRaises(BadRarFile):
            super(TestCorruptedRar, self).test_read_to_memory()
