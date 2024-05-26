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

class SessionApi(BaseApi):
    """
    This class contains the methods to interact with the Session API.
    """

    def auth_valid(self) -> bool:
        """
        Checks whether the provided authentication is valid.
        """
        url = self.api_url + '/session'
        response = self.session.get(url)
        return response.ok
    

    def login(self, username: str, password: str) -> dict:
        """
        Logs in.

        :return: Session info for the given user incl. token.
        """
        url = self.api_url + '/session'
        data = {
            'username': username,
            'password': password
        }
        response = self.session.post(url, json=data)
        return response.json()
    

    def security_enabled(self) -> bool:
        """
        Checks whether security is enabled.
        """
        url = self.api_url + '/session/enabled'
        response = self.session.get(url)
        return response.json()