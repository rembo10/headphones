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

class SharesApi(BaseApi):
    """
    This class contains the methods to interact with the Shares API.
    """

    def get_all(self) -> dict:
        """
        Gets the current list of shares.
        """
        url = self.api_url + '/shares'
        response = self.session.get(url)
        return response.json()
    

    def start_scan(self) -> bool:
        """
        Initiates a scan of the configured shares.

        :return: True if successful.
        """
        url = self.api_url + '/shares'
        response = self.session.put(url)
        return response.ok
    

    def cancel_scan(self) -> bool:
        """
        Cancels a share scan, if one is running.

        :return: True if successful.
        """
        url = self.api_url + '/shares'
        response = self.session.delete(url)
        return response.ok
    

    def get(self, id: str) -> dict:
        """
        Gets the share associated with the specified id.
        """
        url = self.api_url + f'/shares/{id}'
        response = self.session.get(url)
        return response.json()
    

    def all_contents(self) -> list:
        """
        Returns a list of all shared directories and files.
        """
        url = self.api_url + '/shares/contents'
        response = self.session.get(url)
        return response.json()
    

    def contents(self, id: str) -> list:
        """
        Gets the contents of the share associated with the specified id.
        """
        url = self.api_url + f'/shares/{id}/contents'
        response = self.session.get(url)
        return response.json()