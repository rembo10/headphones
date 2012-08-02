#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

from cherrypy.filters.basefilter import BaseFilter
import cherrypy



class HTTPSFilter(BaseFilter):

    """This filter is based on a guide at http://www.turbogears.org/1.0/docs/Install/RedirectHttpsRequests.html

    It's purpose is to allow Headphones to issue redirects with the
    correct protocol (HTTP/HTTPS) when being served behind a
    HTTPS-handling proxy.
    """

    def before_request_body(self):
        forwarded_ssl_triggers = {
            'X-Forwarded-Protocol': 'SSL',
            'X-Forwarded-Ssl': 'On',
        }
        request = cherrypy.request
        headers = request.headers
        forwarded_ssl = reduce(
            lambda x, y: x | headers.get(y).lower() == forwarded_ssl_triggers[y].lower(),
            forwarded_ssl_triggers.keys(),
            False
        )
        if forwarded_ssl:
            # base = config.get('https_filter.secure_base_url')
            # if base is None:
            #     if config.get('base_url_filter.use_x_forwarded_host', False):
            #         base = headers.get('X-Forwarded-Host', 'localhost')
            #     else:
            #         base = 'localhost'
            # request.base = 'https://' + base
            request.headers['X-ForwardedSslDetected'] = Yes
