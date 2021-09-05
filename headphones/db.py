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

###################################
# Stolen from Sick-Beard's db.py  #
###################################

from __future__ import with_statement

import time

import sqlite3
import sys


if 'PyPy' in sys.subversion:
    import psycopg2cffi.compat
    psycopg2cffi.compat.register()

import psycopg2  # pylint: disable=import-error
import psycopg2.extensions  # pylint: disable=import-error
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

import psycopg2.extras  # pylint: disable=import-error

import os
import headphones
import threading
from itertools import chain
from headphones import logger


def dbFilename(filename="headphones.db"):
    return os.path.join(headphones.DATA_DIR, filename)


def getCacheSize():
    # this will protect against typecasting problems produced by empty string and None settings
    if not headphones.CONFIG.CACHE_SIZEMB:
        # sqlite will work with this (very slowly)
        return 0
    return int(headphones.CONFIG.CACHE_SIZEMB)


def convert_pgsql_bindparms(query):
    # FIXME make a real % parser or something here, hopefully this gets transitioned to an ORM sooner than that
    return query.replace('%s', '?')


class DBConnection_sqlite:

    dbcache = threading.local()

    def __init__(self, filename="headphones.db"):

        self.filename = filename
        """
        if not hasattr(self.dbcache, 'connection'):
            self.dbcache.connection = sqlite3.connect(dbFilename(filename), timeout=20)
            # don't wait for the disk to finish writing
            self.dbcache.connection.execute("PRAGMA synchronous = OFF")
            # journal disabled since we never do rollbacks
            self.dbcache.connection.execute("PRAGMA journal_mode = %s" % headphones.CONFIG.JOURNAL_MODE)
            # 64mb of cache memory,probably need to make it user configurable
            self.dbcache.connection.execute("PRAGMA cache_size=-%s" % (getCacheSize() * 1024))

            self.dbcache.connection.row_factory = sqlite3.Row
        self.connection = self.dbcache.connection
        """
        self.connection = sqlite3.connect(dbFilename(filename), timeout=20)
        # don't wait for the disk to finish writing
        self.connection.execute("PRAGMA synchronous = OFF")
        # default set to Write-Ahead Logging WAL
        self.connection.execute("PRAGMA journal_mode = %s" % headphones.CONFIG.JOURNAL_MODE)
        # 64mb of cache memory,probably need to make it user configurable
        self.connection.execute("PRAGMA cache_size=-%s" % (getCacheSize() * 1024))
        self.connection.row_factory = sqlite3.Row

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def action(self, query, args=None, upsert_insert_qry=None):

        if query is None:
            return

        sqlResult = None
        attempts = 0
        dberror = None

        while attempts < 10:
            try:
                with self.connection as c:

                    # log that previous attempt was locked and we're trying again
                    if dberror:
                        if args is None:
                            logger.debug('SQL: Database was previously locked, trying again. Attempt number %i. Query: %s', attempts + 1, query)
                        else:
                            logger.debug('SQL: Database was previously locked, trying again. Attempt number %i. Query: %s. Args: %s', attempts + 1, query, args)

                    # debugging
                    # try:
                    #     explain_query = 'EXPLAIN QUERY PLAN ' + query
                    #     if not args:
                    #         sql_results = c.execute(explain_query)
                    #     else:
                    #         sql_results = c.execute(explain_query, args)
                    #     if not args:
                    #         print(explain_query)
                    #     else:
                    #         print(explain_query + ' ' + str(args))
                    #     explain_results = sql_results
                    #     for row in explain_results:
                    #         print row
                    # except Exception as e:
                    #     print(e)

                    # Execute query

                    # time0 = time.time()

                    if args is None:
                        sqlResult = c.execute(query)
                        # logger.debug('SQL: ' + query)
                    else:
                        query = convert_pgsql_bindparms(query)
                        sqlResult = c.execute(query, args)
                        # logger.debug('SQL: %s. Args: %s', query, args)

                        # INSERT part of upsert query
                        if upsert_insert_qry:
                            sqlResult = c.execute(upsert_insert_qry, args)
                            # logger.debug('SQL: %s. Args: %s', upsert_insert_qry, args)

                    # debugging: loose test to log queries taking longer than 5 seconds
                    # seconds = time.time() - time0
                    # if seconds > 5:
                    #     if args is None:
                    #         logger.debug("SQL: Query ran for %s seconds: %s", seconds, query)
                    #     else:
                    #         logger.debug("SQL: Query ran for %s seconds: %s with args %s", seconds, query, args)

                    break

            except sqlite3.OperationalError, e:
                if "unable to open database file" in e.message or "database is locked" in e.message:
                    dberror = e
                    if args is None:
                        logger.debug('Database error: %s. Query: %s', e, query)
                    else:
                        logger.debug('Database error: %s. Query: %s. Args: %s', e, query, args)
                    attempts += 1
                    time.sleep(1)
                else:
                    logger.error('Database error: %s', e)
                    raise
            except sqlite3.DatabaseError, e:
                logger.error('Fatal Error executing %s :: %s', query, e)
                raise

        # log if no results returned due to lock
        if not sqlResult and attempts:
            if args is None:
                logger.warn('SQL: Query failed due to database error: %s. Query: %s', dberror, query)
            else:
                logger.warn('SQL: Query failed due to database error: %s. Query: %s. Args: %s', dberror, query, args)

        return sqlResult

    def select(self, query, args=None):

        sqlResults = self.action(query, args).fetchall()

        if sqlResults is None or sqlResults == [None]:
            return []

        return sqlResults

    def upsert(self, tableName, valueDict, keyDict):
        """
        Transactions an Update or Insert to a table based on key.
        If the table is not updated then the 'WHERE changes' will be 0 and the table inserted
        """
        def genParams(myDict):
            return [x + " = %s" for x in myDict.keys()]

        update_query = "UPDATE " + tableName + " SET " + ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))

        insert_query = ("INSERT INTO " + tableName + " (" + ", ".join(valueDict.keys() + keyDict.keys()) + ")" + " SELECT " + ", ".join(
            ["%s"] * len(valueDict.keys() + keyDict.keys())) + " WHERE changes()=0")

        try:
            self.action(update_query, valueDict.values() + keyDict.values(), upsert_insert_qry=insert_query)
        except sqlite3.IntegrityError:
            logger.info('Queries failed: %s and %s', update_query, insert_query)


class CIDictCursor(psycopg2.extras.DictCursorBase):
    """A cursor that uses a case insensitive fetching dict as the base type for rows.
    """
    def __init__(self, *args, **kwargs):
        kwargs['row_factory'] = CIDictRow
        super(CIDictCursor, self).__init__(*args, **kwargs)
        self._prefetch = 0

    def execute(self, query, vars=None):
        self.column_mapping = []
        self._query_executed = 1
        return super(CIDictCursor, self).execute(query, vars)

    def callproc(self, procname, vars=None):
        self.column_mapping = []
        self._query_executed = 1
        return super(CIDictCursor, self).callproc(procname, vars)

    def _build_index(self):
        if self._query_executed == 1 and self.description:
            for i in range(len(self.description)):
                self.column_mapping.append(self.description[i][0])
            self._query_executed = 0


class CIDictRow(dict):
    """A `!dict` subclass representing a data record."""

    __slots__ = ('_column_mapping')

    def __init__(self, cursor):
        dict.__init__(self)
        # Required for named cursors
        if cursor.description and not cursor.column_mapping:
            cursor._build_index()

        self._column_mapping = cursor.column_mapping

    def __setitem__(self, name, value):
        if type(name) == int:
            name = self._column_mapping[name]
        return dict.__setitem__(self, name, value)

    def __getitem__(self, key):
        return dict.get(self, key, dict.get(self, unicode(key).lower()))

    def __getstate__(self):
        return (self.copy(), self._column_mapping[:])

    def __setstate__(self, data):
        self.update(data[0])
        self._column_mapping = data[1]


class DBConnection_psql:
    dbcache = threading.local()

    def __init__(self, filename="headphones.db"):

        self.filename = filename
        if not hasattr(self.dbcache, 'connection'):
            self.dbcache.connection = psycopg2.connect(database='headphones', user='headphones', password='headphones', host='127.0.0.1', port='32770')
        self.connection = self.dbcache.connection

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def action(self, query, args=None):

        if query is None:
            return

        sqlResult = None

        try:
            with self.connection as c:
                cursor = c.cursor(cursor_factory=CIDictCursor)
                if args is None:
                    sqlResult = cursor.execute(query)
                else:
                    sqlResult = cursor.execute(query, args)

        except psycopg2.Warning as e:
            logger.warn('Database Error: %s', e)

        except psycopg2.OperationalError as e:
            logger.error('Database error: %s', e)
            c.rollback()
            raise

        except psycopg2.DatabaseError, e:
            logger.error('Fatal Error executing %s :: %s', query, e)
            c.rollback()
            raise

        return cursor

    def select(self, query, args=None):

        sqlResults = self.action(query, args).fetchall()

        if sqlResults is None or sqlResults == [None]:
            return []

        self.connection.commit()
        return sqlResults

    def upsert(self, tableName, valueDict, keyDict):

        def genParams(myDict):
            return (x + " = %s" for x in myDict.iterkeys())

        def genUpsertParams(myDict):
            return ('.'.join((tableName, x)) + " = %s" for x in myDict.iterkeys())

        insert_query = (
            "INSERT INTO " + tableName + " (" + ", ".join(
                chain(valueDict.iterkeys(), keyDict.iterkeys())) + ")" +
            " VALUES (" + ", ".join(["%s"] * (len(valueDict) + len(keyDict))) +
            ") ON CONFLICT ( " + ", ".join(keyDict.iterkeys()) + "  ) DO UPDATE SET " +
            ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genUpsertParams(keyDict))
        )

        vals = chain(
            valueDict.itervalues(),
            keyDict.itervalues(),
            valueDict.itervalues(),
            keyDict.itervalues())

        ret = None
        try:
            ret = self.action(insert_query, [v for v in vals])
        except psycopg2.IntegrityError:
            logger.info('Queries failed: %s and %s', 'was update_query', insert_query)
            self.connection.rollback()
            return
        except psycopg2.ProgrammingError:
            logger.exception('Bad query %s', insert_query)
            raise

        self.connection.commit()

DBConnection = DBConnection_psql
