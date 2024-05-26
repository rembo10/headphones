# Copyright (C) 2023 bigoulours
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .base import *

class PublicChatApi(BaseApi):
    """
    [UNTESTED] This class contains the methods to interact with the PublicChat API.
    """

    def start(self) -> bool:
        """
        Starts public chat.

        :return: True if successful.
        """
        url = self.api_url + '/publicchat'
        response = self.session.post(url)
        return response.ok
    

    def stop(self) -> bool:
        """
        Stops public chat.

        :return: True if successful.
        """
        url = self.api_url + '/publicchat'
        response = self.session.delete(url)
        return response.ok
