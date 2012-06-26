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

def ex(e):
    """
    Returns a string from the exception text if it exists.
    """
    
    # sanity check
    if not e.args or not e.args[0]:
        return ""

    e_message = e.args[0]
    
    # if fixStupidEncodings doesn't fix it then maybe it's not a string, in which case we'll try printing it anyway
    if not e_message:
        try:
            e_message = str(e.args[0])
        except:
            e_message = ""
    
    return e_message
    

class HeadphonesException(Exception):
    "Generic Headphones Exception - should never be thrown, only subclassed"

class NewzbinAPIThrottled(HeadphonesException):
    "Newzbin has throttled us, deal with it"
