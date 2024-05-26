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

class RoomsApi(BaseApi):
    """
    This class contains the methods to interact with the Rooms API.
    """

    def get_all_joined(self) -> list:
        """
        Gets all joined rooms.

        :return: Names of the joined rooms.
        """
        url = self.api_url + '/rooms/joined'
        response = self.session.get(url)
        return response.json()
    

    def join(self, roomName: str) -> dict:
        """
        Joins a room.

        :return: room info: name, isPrivate, users, messages
        """
        url = self.api_url + '/rooms/joined'
        response = self.session.post(url, json=roomName)
        return response.json()


    def get_joined(self, roomName: str) -> dict:
        """
        Gets the specified room.

        :return: room info: name, isPrivate, users, messages
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}'
        response = self.session.get(url)
        return response.json()
    

    def leave(self, roomName: str) -> bool:
        """
        Leaves a room.

        :return: True if successful.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}'
        response = self.session.delete(url)
        return response.ok
    

    def send(self, roomName: str, message: str) -> bool:
        """
        Sends a message to the specified room.

        :return: True if successful.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}/messages'
        response = self.session.post(url, json=message)
        return response.ok


    def get_messages(self, roomName: str) -> list:
        """
        Gets the current list of messages for the specified room.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}/messages'
        response = self.session.get(url)
        return response.json()


    def set_ticker(self, roomName: str, ticker: str) -> bool:
        """
        Sets a ticker for the specified room.

        :return: True if successful.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}/ticker'
        response = self.session.post(url, json=ticker)
        return response.ok
    

    def add_member(self, roomName: str, username: str) -> bool:
        """
        Adds a member to a private room.

        :return: True if successful.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}/members'
        response = self.session.post(url, json=username)
        return response.ok
    

    def get_users(self, roomName: str) -> list:
        """
        Gets the current list of users for the specified joined room.
        """
        url = self.api_url + f'/rooms/joined/{quote(roomName)}/users'
        response = self.session.get(url)
        return response.json()
    

    def get_all(self) -> list:
        """
        Gets a list of rooms from the server.
        """
        url = self.api_url + '/rooms/available'
        response = self.session.get(url)
        return response.json()