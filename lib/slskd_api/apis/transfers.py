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
from typing import Union

class TransfersApi(BaseApi):
    """
    This class contains the methods to interact with the Transfers API.
    """

    def cancel_download(self, username: str, id:str, remove: bool = False) -> bool:
        """
        Cancels the specified download.

        :return: True if successful.
        """
        url = self.api_url + f'/transfers/downloads/{quote(username)}/{id}'
        params = dict(
            remove=remove
        )
        response = self.session.delete(url, params=params)
        return response.ok
    

    def get_download(self, username: str, id: str) -> dict:
        """
        Gets the specified download.
        """
        url = self.api_url + f'/transfers/downloads/{quote(username)}/{id}'
        response = self.session.get(url)
        return response.json()
    

    def remove_completed_downloads(self) -> bool:
        """
        Removes all completed downloads, regardless of whether they failed or succeeded.

        :return: True if successful.
        """
        url = self.api_url + '/transfers/downloads/all/completed'
        response = self.session.delete(url)
        return response.ok
    

    def cancel_upload(self, username: str, id: str, remove: bool = False) -> bool:
        """
        Cancels the specified upload.

        :return: True if successful.
        """
        url = self.api_url + f'/transfers/uploads/{quote(username)}/{id}'
        params = dict(
            remove=remove
        )
        response = self.session.delete(url, params=params)
        return response.ok
    

    def get_upload(self, username: str, id: str) -> dict:
        """
        Gets the specified upload.
        """
        url = self.api_url + f'/transfers/uploads/{quote(username)}/{id}'
        response = self.session.get(url)
        return response.json()
    

    def remove_completed_uploads(self) -> bool:
        """
        Removes all completed uploads, regardless of whether they failed or succeeded.

        :return: True if successful.
        """
        url = self.api_url + '/transfers/uploads/all/completed'
        response = self.session.delete(url)
        return response.ok
    

    def enqueue(self, username: str, files: list) -> bool:
        """
        Enqueues the specified download.

        :param username: User to download from.
        :param files: A list of dictionaries in the same form as what's returned 
            by :py:func:`~slskd_api.apis.SearchesApi.search_responses`:
            [{'filename': <filename>, 'size': <filesize>}...]
        :return: True if successful.
        """
        url = self.api_url + f'/transfers/downloads/{quote(username)}'
        response = self.session.post(url, json=files)
        return response.ok
    

    def get_downloads(self, username: str) -> dict:
        """
        Gets all downloads for the specified username.
        """
        url = self.api_url + f'/transfers/downloads/{quote(username)}'
        response = self.session.get(url)
        return response.json()
    

    def get_all_downloads(self, includeRemoved: bool = False) -> list:
        """
        Gets all downloads.
        """
        url = self.api_url + '/transfers/downloads/'
        params = dict(
            includeRemoved=includeRemoved
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def get_queue_position(self, username: str, id: str) -> Union[int,str]:
        """
        Gets the download for the specified username matching the specified filename, and requests the current place in the remote queue of the specified download.
        
        :return: Queue position or error message
        """
        url = self.api_url + f'/transfers/downloads/{quote(username)}/{id}/position'
        response = self.session.get(url)
        return response.json()
    

    def get_all_uploads(self, includeRemoved: bool = False) -> list:
        """
        Gets all uploads.
        """
        url = self.api_url + '/transfers/uploads/'
        params = dict(
            includeRemoved=includeRemoved
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def get_uploads(self, username: str) -> dict:
        """
        Gets all uploads for the specified username.
        """
        url = self.api_url + f'/transfers/uploads/{quote(username)}'
        response = self.session.get(url)
        return response.json()