import requests
import fanart
from fanart.errors import RequestFanartError, ResponseFanartError


class Request(object):
    def __init__(self, apikey, id, ws, type=None, sort=None, limit=None):
        '''
        .. warning:: Since the migration to fanart.tv's api v3, we cannot use
            the kwargs `type/sort/limit` as we did before, so for now this
            kwargs will be ignored.
        '''
        self._apikey = apikey
        self._id = id
        self._ws = ws
        self._type = type or fanart.TYPE.ALL
        self._sort = sort or fanart.SORT.POPULAR
        self._limit = limit or fanart.LIMIT.ALL
        self.validate()
        self._response = None

    def validate(self):
        for attribute_name in ('ws', 'type', 'sort', 'limit'):
            attribute = getattr(self, '_' + attribute_name)
            choices = getattr(fanart, attribute_name.upper() + '_LIST')
            if attribute not in choices:
                raise RequestFanartError(
                    'Not allowed {}: {} [{}]'.format(
                        attribute_name, attribute, ', '.join(choices)))

    def __str__(self):
        return '{base_url}/{ws}/{id}?api_key={apikey}'.format(
            base_url=fanart.BASEURL,
            ws=self._ws,
            id=self._id,
            apikey=self._apikey,
        )

    def response(self):
        try:
            response = requests.get(str(self))
            rjson = response.json()
            if not isinstance(rjson, dict):
                raise Exception(response.text)
            if 'error message' in rjson:
                raise Exception(rjson['status'], rjson['error message'])
            return rjson
        except Exception as e:
            raise ResponseFanartError(str(e))
