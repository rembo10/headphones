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

class RelayApi(BaseApi):
    """
    [UNTESTED] This class contains the methods to interact with the Relay API.
    """

    def connect(self) -> bool:
        """
        Connects to the configured controller.

        :return: True if successful.
        """
        url = self.api_url + '/relay/agent'
        response = self.session.put(url)
        return response.ok
    

    def disconnect(self) -> bool:
        """
        Disconnects from the connected controller.

        :return: True if successful.
        """
        url = self.api_url + '/relay/agent'
        response = self.session.delete(url)
        return response.ok
    

    def download_file(self, token: str) -> bool:
        """
        Downloads a file from the connected controller.

        :return: True if successful.
        """
        url = self.api_url + f'/relay/controller/downloads/{token}'
        response = self.session.get(url)
        return response.ok
    

    def upload_file(self, token: str) -> bool:
        """
        Uploads a file from the connected controller.

        :return: True if successful.
        """
        url = self.api_url + f'/relay/controller/files/{token}'
        response = self.session.post(url)
        return response.ok
    

    def upload_share_info(self, token: str) -> bool:
        """
        Uploads share information to the connected controller.

        :return: True if successful.
        """
        url = self.api_url + f'/relay/controller/shares/{token}'
        response = self.session.post(url)
        return response.ok