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

import json

from headphones import db, helpers, logger, request


def update(artistid, artist_name, release_groups):
    """ Pretty simple and crude function to find the artist page on metacritic,
    then parse that page to get critic & user scores for albums"""

    # First let's modify the artist name to fit the metacritic convention.
    # We could just do a search, then take the top result, but at least this will
    # cut down on api calls. If it's ineffective then we'll switch to search

    replacements = {" & ": " ", ".": ""}
    mc_artist_name = helpers.clean_musicbrainz_name(artist_name, return_as_string=False)
    mc_artist_name = mc_artist_name.replace("'", " ")
    mc_artist_name = helpers.replace_all(artist_name.lower(), replacements)
    mc_artist_name = mc_artist_name.replace(" ", "-")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2243.2 Safari/537.36'}

    url = "http://www.metacritic.com/person/" + mc_artist_name + "?filter-options=music&sort_options=date&num_items=100"

    res = request.request_soup(url, headers=headers, whitelist_status_code=404)

    rows = None

    try:
        table = res.find("table", class_="credits person_credits")
        rows = table.tbody.find_all('tr')
    except:
        logger.info("Unable to get metacritic scores for: %s" % artist_name)

    myDB = db.DBConnection()
    artist = myDB.action('SELECT * FROM artists WHERE ArtistID=?', [artistid]).fetchone()

    score_list = []

    # If we couldn't get anything from MetaCritic for whatever reason,
    # let's try to load scores from the db
    if not rows:
        if artist['MetaCritic']:
            score_list = json.loads(artist['MetaCritic'])
        else:
            return

    # If we did get scores, let's update the db with them
    else:
        for row in rows:
            title = row.a.string
            scores = row.find_all("span")
            critic_score = scores[0].string
            user_score = scores[1].string
            score_dict = {'title': title, 'critic_score': critic_score, 'user_score': user_score}
            score_list.append(score_dict)

        # Save scores to the database
        controlValueDict = {"ArtistID": artistid}
        newValueDict = {'MetaCritic': json.dumps(score_list)}
        myDB.upsert("artists", newValueDict, controlValueDict)

    for score in score_list:
        title = score['title']
        # Iterate through the release groups we got passed to see if we can find
        # a match
        for rg in release_groups:
            if rg['title'].lower() == title.lower():
                critic_score = score['critic_score']
                user_score = score['user_score']
                controlValueDict = {"AlbumID": rg['id']}
                newValueDict = {'CriticScore': critic_score, 'UserScore': user_score}
                myDB.upsert("albums", newValueDict, controlValueDict)
