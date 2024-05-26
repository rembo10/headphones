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
import uuid
from typing import Optional

class SearchesApi(BaseApi):
    """
    Class that handles operations on searches.
    """

    def search_text(self,
                    searchText: str,
                    id: Optional[str] = None,
                    fileLimit: int = 10000,
                    filterResponses: bool = True,
                    maximumPeerQueueLength: int = 1000000,
                    minimumPeerUploadSpeed: int = 0,
                    minimumResponseFileCount: int = 1,
                    responseLimit: int = 100,
                    searchTimeout: int = 15000
        ) -> dict:
        """
        Performs a search for the specified request.

        :param searchText: Search query
        :param id: uuid of the search. One will be generated if None.
        :param fileLimit: Max number of file results
        :param filterResponses: Filter unreachable users from the results
        :param maximumPeerQueueLength: Max queue length
        :param minimumPeerUploadSpeed: Min upload speed in bit/s
        :param minimumResponseFileCount: Min number of matching files per user
        :param responseLimit: Max number of users results
        :param searchTimeout: Search timeout in ms
        :return: Info about the search (no results!)
        """

        url = self.api_url + '/searches'

        try:
            id = str(uuid.UUID(id)) # check if given id is a valid uuid
        except:
            id = str(uuid.uuid1())  # otherwise generate a new one

        data = {
            "id": id,
            "fileLimit": fileLimit,
            "filterResponses": filterResponses,
            "maximumPeerQueueLength": maximumPeerQueueLength,
            "minimumPeerUploadSpeed": minimumPeerUploadSpeed,
            "minimumResponseFileCount": minimumResponseFileCount,
            "responseLimit": responseLimit,
            "searchText": searchText,
            "searchTimeout": searchTimeout,
        }
        response = self.session.post(url, json=data)
        return response.json()
    

    def get_all(self) -> list:
        """
        Gets the list of active and completed searches.
        """
        url = self.api_url + '/searches'
        response = self.session.get(url)
        return response.json()
    

    def state(self, id: str, includeResponses: bool = False) -> dict:
        """
        Gets the state of the search corresponding to the specified id.

        :param id: uuid of the search.
        :param includeResponses: Include responses (search result list) in the returned dict
        :return: Info about the search
        """
        url = self.api_url + f'/searches/{id}'
        params = dict(
            includeResponses=includeResponses
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def stop(self, id: str) -> bool:
        """
        Stops the search corresponding to the specified id.

        :return: True if successful.
        """
        url = self.api_url + f'/searches/{id}'
        response = self.session.put(url)
        return response.ok
    

    def delete(self, id: str):
        """
        Deletes the search corresponding to the specified id.

        :return: True if successful.
        """
        url = self.api_url + f'/searches/{id}'
        response = self.session.delete(url)
        return response.ok
    

    def search_responses(self, id: str) -> list:
        """
        Gets search responses corresponding to the specified id.
        """
        url = self.api_url + f'/searches/{id}/responses'
        response = self.session.get(url)
        return response.json()