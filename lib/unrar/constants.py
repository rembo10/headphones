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


# Success result
SUCCESS = 0

#
# Open Modes
#

# headers only
RAR_OM_LIST = 0
# testing and extracting
RAR_OM_EXTRACT = 1
# headers only, include splitted volumes
RAR_OM_LIST_INCSPLIT = 2

#
# Process file operations
#

RAR_SKIP = 0
RAR_TEST = 1
RAR_EXTRACT = 2
RAR_CANCEL_EXTRACT = -1

#
# Errors
#

# End of archive
ERAR_END_ARCHIVE = 10
# Not enough memory to initialize data structures
ERAR_NO_MEMORY = 11
# Archive header broken
ERAR_BAD_DATA = 12
# File is not valid RAR archive
ERAR_BAD_ARCHIVE = 13
# Unknown encryption used for archive headers
ERAR_UNKNOWN_FORMAT = 14
# Archive/Volume open error
ERAR_EOPEN = 15
# File create error
ERAR_ECREATE = 16
# Archive/File close error
ERAR_ECLOSE = 17
# Read error
ERAR_EREAD = 18
# Write error
ERAR_EWRITE = 19
# Buffer too small, comments not completely read
ERAR_SMALL_BUF = 20
# Unknown error
ERAR_UNKNOWN = 21
# Missing password error
ERAR_MISSING_PASSWORD = 22

#
# Comments state
#

# comments not present
RAR_NO_COMMENTS = 0
# Comments read completely
RAR_COMMENTS_SUCCESS = 1


#
# Host OS
#

RAR_DOS = 0
RAR_OS2 = 1
RAR_WIN = 2
RAR_UNIX = 3


#
# Callback messages
#

UCM_CHANGEVOLUME = 0
UCM_PROCESSDATA = 1
UCM_NEEDPASSWORD = 2
UCM_CHANGEVOLUMEW = 3
UCM_NEEDPASSWORDW = 4

#
# Change volume callback message
#
RAR_VOL_ASK = 0
RAR_VOL_NOTIFY = 1
