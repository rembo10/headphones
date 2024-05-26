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

class ServerApi(BaseApi):
    """
    This class contains the methods to interact with the Server API.
    """

    def connect(self) -> bool:
        """
        Connects the client.

        :return: True if successful.
        """
        url = self.api_url + '/server'
        response = self.session.put(url)
        return response.ok
    

    def disconnect(self) -> bool:
        """
        Disconnects the client.

        :return: True if successful.
        """
        url = self.api_url + '/server'
        response = self.session.delete(url, json='')
        return response.ok
    

    def state(self) -> dict:
        """
        Retrieves the current state of the server.
        """
        url = self.api_url + '/server'
        response = self.session.get(url)
        return response.json()