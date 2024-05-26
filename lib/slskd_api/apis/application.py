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

class ApplicationApi(BaseApi):
    """
    This class contains the methods to interact with the Application API.
    """

    def state(self) -> dict:
        """
        Gets the current state of the application.
        """
        url = self.api_url + '/application'
        response = self.session.get(url)
        return response.json()
    

    def stop(self) -> bool:
        """
        Stops the application. Only works with token (usr/pwd login). 'Unauthorized' with API-Key.
        
        :return: True if successful.
        """
        url = self.api_url + '/application'
        response = self.session.delete(url)
        return response.ok
    

    def restart(self) -> bool:
        """
        Restarts the application. Only works with token (usr/pwd login). 'Unauthorized' with API-Key.
        
        :return: True if successful.
        """
        url = self.api_url + '/application'
        response = self.session.put(url)
        return response.ok
    

    def version(self) -> str:
        """
        Gets the current application version.
        """
        url = self.api_url + '/application/version'
        response = self.session.get(url)
        return response.json()
    

    def check_updates(self, forceCheck: bool = False) -> dict:
        """
        Checks for updates.
        """
        url = self.api_url + '/application/version/latest'
        params = dict(
            forceCheck=forceCheck
        )
        response = self.session.get(url, params=params)
        return response.json()
    

    def gc(self) -> bool:
        """
        Forces garbage collection.

        :return: True if successful.
        """
        url = self.api_url + '/application/gc'
        response = self.session.post(url)
        return response.ok
    
    
# Not supposed to be part of the external API
# More info in the Github discussion: https://github.com/slskd/slskd/discussions/910
    # def dump(self):
    #     url = self.api_url + '/application/dump'
    #     response = self.session.get(url)
    #     return response.json()