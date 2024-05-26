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

class ConversationsApi(BaseApi):
    """
    This class contains the methods to interact with the Conversations API.
    """

    def acknowledge(self, username: str, id: int) -> bool:
        """
        Acknowledges the given message id for the given username.

        :return: True if successful.
        """
        url = self.api_url + f'/conversations/{quote(username)}/{id}'
        response = self.session.put(url)
        return response.ok
    

    def acknowledge_all(self, username: str) -> bool:
        """
        Acknowledges all messages from the given username.

        :return: True if successful.
        """
        url = self.api_url + f'/conversations/{quote(username)}'
        response = self.session.put(url)
        return response.ok
    

    def delete(self, username: str) -> bool:
        """
        Closes the conversation associated with the given username.

        :return: True if successful.
        """
        url = self.api_url + f'/conversations/{quote(username)}'
        response = self.session.delete(url)
        return response.ok
    

    def get(self, username: str, includeMessages: bool = True) -> dict:
        """
        Gets the conversation associated with the specified username.
        """
        url = self.api_url + f'/conversations/{quote(username)}'
        params = dict(
            includeMessages=includeMessages
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def send(self, username: str, message: str) -> bool:
        """
        Sends a private message to the specified username.

        :return: True if successful.
        """
        url = self.api_url + f'/conversations/{quote(username)}'
        response = self.session.post(url, json=message)
        return response.ok
    

    def get_all(self, includeInactive: bool = False, unAcknowledgedOnly : bool = False) -> list:
        """
        Gets all active conversations.
        """
        url = self.api_url + '/conversations'
        params = dict(
            includeInactive=includeInactive,
            unAcknowledgedOnly=unAcknowledgedOnly
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def get_messages(self, username: str, unAcknowledgedOnly : bool = False) -> list:
        """
        Gets all messages associated with the specified username.
        """
        url = self.api_url + f'/conversations/{quote(username)}/messages'
        params = dict(
            username=username,
            unAcknowledgedOnly=unAcknowledgedOnly
        )
        response = self.session.get(url, params=params)
        return response.json()
    