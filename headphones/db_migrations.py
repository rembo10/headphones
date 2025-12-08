#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

"""
Database schema migrations for Headphones.
Add migration functions here when schema changes are needed.
"""

import headphones
from headphones import db, logger


def check_and_run_migrations():
    """Run any pending database migrations."""
    myDB = db.DBConnection()
    
    # Check if SourceOrigin column exists in tracks table
    try:
        result = myDB.action("PRAGMA table_info(tracks)").fetchall()
        columns = [row['name'] for row in result]
        if 'SourceOrigin' not in columns:
            logger.info("Adding SourceOrigin column to tracks table")
            myDB.action("ALTER TABLE tracks ADD COLUMN SourceOrigin TEXT DEFAULT NULL")
    except Exception as e:
        logger.error(f"Error checking tracks table: {e}")
    
    # Check if SourceOrigin column exists in alltracks table
    try:
        result = myDB.action("PRAGMA table_info(alltracks)").fetchall()
        columns = [row['name'] for row in result]
        if 'SourceOrigin' not in columns:
            logger.info("Adding SourceOrigin column to alltracks table")
            myDB.action("ALTER TABLE alltracks ADD COLUMN SourceOrigin TEXT DEFAULT NULL")
    except Exception as e:
        logger.error(f"Error checking alltracks table: {e}")
    
    # Check if SourceOrigin column exists in have table
    try:
        result = myDB.action("PRAGMA table_info(have)").fetchall()
        columns = [row['name'] for row in result]
        if 'SourceOrigin' not in columns:
            logger.info("Adding SourceOrigin column to have table")
            myDB.action("ALTER TABLE have ADD COLUMN SourceOrigin TEXT DEFAULT NULL")
    except Exception as e:
        logger.error(f"Error checking have table: {e}")
