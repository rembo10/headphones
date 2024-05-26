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

class OptionsApi(BaseApi):
    """
    This class contains the methods to interact with the Options API.
    """

    def get(self) -> dict:
        """
        Gets the current application options.
        """
        url = self.api_url + '/options'
        response = self.session.get(url)
        return response.json()
    

    def get_startup(self) -> dict:
        """
        Gets the application options provided at startup.
        """
        url = self.api_url + '/options/startup'
        response = self.session.get(url)
        return response.json()

  
    def debug(self) -> str:
        """
        Gets the debug view of the current application options.
        debug and remote_configuration must be set to true.
        Only works with token (usr/pwd login). 'Unauthorized' with API-Key.
        """
        url = self.api_url + '/options/debug'
        response = self.session.get(url)
        return response.json()


    def yaml_location(self) -> str:
        """
        Gets the path of the yaml config file. remote_configuration must be set to true.
        Only works with token (usr/pwd login). 'Unauthorized' with API-Key.
        """
        url = self.api_url + '/options/yaml/location'
        response = self.session.get(url)
        return response.json()
    

    def download_yaml(self) -> str:
        """
        Gets the content of the yaml config file as text. remote_configuration must be set to true.
        Only works with token (usr/pwd login). 'Unauthorized' with API-Key.
        """
        url = self.api_url + '/options/yaml'
        response = self.session.get(url)
        return response.json()
    

    def upload_yaml(self, yaml_content: str) -> bool:
        """
        Sets the content of the yaml config file. remote_configuration must be set to true.
        Only works with token (usr/pwd login). 'Unauthorized' with API-Key.

        :return: True if successful.
        """
        url = self.api_url + '/options/yaml'
        response = self.session.post(url, json=yaml_content)
        return response.ok
    

    def validate_yaml(self, yaml_content: str) -> str:
        """
        Validates the provided yaml string. remote_configuration must be set to true.
        Only works with token (usr/pwd login). 'Unauthorized' with API-Key.

        :return: Empty string if validation successful. Error message otherwise.
        """
        url = self.api_url + '/options/yaml/validate'
        response = self.session.post(url, json=yaml_content)
        return response.text