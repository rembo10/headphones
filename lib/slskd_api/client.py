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

API_VERSION = 'v0'

import requests
from urllib.parse import urljoin
from functools import reduce
from base64 import b64encode
from slskd_api.apis import *


class HTTPAdapterTimeout(requests.adapters.HTTPAdapter):
    def __init__(self, timeout=None, **kwargs):
        super().__init__(**kwargs)
        self.timeout = timeout

    def send(self, *args, **kwargs):
        kwargs['timeout'] = self.timeout
        return super().send(*args, **kwargs)


class SlskdClient:
    """
    The main class that allows access to the different APIs of a slskd instance.
    An API-Key with appropriate permissions (`readwrite` for most use cases) must be set in slskd config file.
    Alternatively, provide your username and password. Requests error status raise corresponding error.
    Usage::
        slskd = slskd_api.SlskdClient(host, api_key, url_base)
        app_status = slskd.application.state()
    """

    def __init__(self,
                 host: str,
                 api_key: str = None,
                 url_base: str = '/',
                 username: str = None,
                 password: str = None,
                 token: str = None,
                 verify_ssl: bool = True,
                 timeout: float = None  # requests timeout in seconds
    ):
        api_url = reduce(urljoin, [f'{host}/', f'{url_base}/', f'api/{API_VERSION}'])

        session = requests.Session()
        session.adapters['http://'] = HTTPAdapterTimeout(timeout=timeout)
        session.adapters['https://'] = HTTPAdapterTimeout(timeout=timeout)
        session.hooks = {'response': lambda r, *args, **kwargs: r.raise_for_status()}
        session.headers.update({'accept': '*/*'})
        session.verify = verify_ssl

        header = {}

        if api_key:
            header['X-API-Key'] = api_key
        elif username and password:
            header['Authorization'] = 'Bearer ' + \
                            SessionApi(api_url, session).login(username, password).get('token', '')
        elif token:
            header['Authorization'] = 'Bearer ' + token
        else:
            raise ValueError('Please provide an API-Key, a valid token or username/password.')
        
        session.headers.update(header)

        base_args = (api_url, session)
        
        self.application = ApplicationApi(*base_args)
        self.conversations = ConversationsApi(*base_args)
        self.logs = LogsApi(*base_args)
        self.options = OptionsApi(*base_args)
        self.public_chat = PublicChatApi(*base_args)
        self.relay = RelayApi(*base_args)
        self.rooms = RoomsApi(*base_args)
        self.searches = SearchesApi(*base_args)
        self.server = ServerApi(*base_args)
        self.session = SessionApi(*base_args)
        self.shares = SharesApi(*base_args)
        self.transfers = TransfersApi(*base_args)
        self.users = UsersApi(*base_args)
    

class MetricsApi:
    """
    Getting the metrics works with a different endpoint. Default: <slskd_url>:5030/metrics.
    Metrics should be first activated in slskd config file.
    User/pass is independent from the main application and default value (slskd:slskd) should be changed.
    Usage::
        metrics_api = slskd_api.MetricsApi(host, metrics_usr='slskd', metrics_pwd='slskd')
        metrics = metrics_api.get()
    """

    def __init__(self,
                 host: str,
                 metrics_usr: str = 'slskd',
                 metrics_pwd: str = 'slskd',
                 metrics_url_base: str = '/metrics'
    ):
        self.metrics_url = urljoin(host, metrics_url_base)
        basic_auth = b64encode(bytes(f'{metrics_usr}:{metrics_pwd}', 'utf-8'))
        self.header = {
            'accept': '*/*',
            'Authorization': f'Basic {basic_auth.decode()}' 
        }

    def get(self) -> str:
        """
        Gets the Prometheus metrics as text.
        """
        response = requests.get(self.metrics_url, headers=self.header)
        return response.text
