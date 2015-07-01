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

import re
import headphones

from headphones import db, helpers, logger, request
from headphones.common import USER_AGENT

def update(artist_name,release_groups):
    """ Pretty simple and crude function to find the artist page on metacritic,
    then parse that page to get critic & user scores for albums"""

    # First let's modify the artist name to fit the metacritic convention. 
    # We could just do a search, then take the top result, but at least this will
    # cut down on api calls. If it's ineffective then we'll switch to search

    replacements = {" & " : " ", "." : ""}
    mc_artist_name = helpers.replace_all(artist_name.lower(),replacements)

    mc_artist_name = mc_artist_name.replace(" ","-")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'}

    url = "http://www.metacritic.com/person/" + mc_artist_name + "?filter-options=music&sort_options=date&num_items=100"

    res = request.request_soup(url, headers=headers, parser='html.parser')

    try:
        rows = res.tbody.find_all('tr')
    except:
        logger.info("Unable to get metacritic scores for: %s" % artist_name)
        return

    myDB = db.DBConnection()

    for row in rows:
        title = row.a.string
        for rg in release_groups:
            if rg['title'].lower() == title.lower():
                scores = row.find_all("span")
                critic_score = scores[0].string
                user_score = scores[1].string
                controlValueDict = {"AlbumID": rg['id']}
                newValueDict = {'CriticScore':critic_score,'UserScore':user_score}
                myDB.upsert("albums", newValueDict, controlValueDict)



