# API Reference
The API is still pretty new and needs some serious cleaning up on the backend but should be reasonably functional. There are no error codes yet.

## General structure
The API endpoint is `http://ip:port + HTTP_ROOT + /api?apikey=$apikey&cmd=$command`

Data response in JSON formatted. If executing a command like "delArtist" or "addArtist" you'll get back an "OK", else, you'll get the data you requested.

## API methods

### getIndex
Fetch data from index page. Returns: ArtistName, ArtistSortName, ArtistID, Status, DateAdded, [LatestAlbum, ReleaseDate, AlbumID], HaveTracks, TotalTracks, IncludeExtras, LastUpdated, [ArtworkURL, ThumbURL]: a remote url to the artwork/thumbnail.

To get the cached image path, see getArtistArt command. ThumbURL is added/updated when an artist is added/updated. If your using the database method to get the artwork, it's more reliable to use the ThumbURL than the ArtworkURL)

### getArtist&id=$artistid
Fetch artist data. returns the artist object (see above) and album info: Status, AlbumASIN, DateAdded, AlbumTitle, ArtistName, ReleaseDate, AlbumID, ArtistID, Type, ArtworkURL: hosted image path. For cached image, see getAlbumArt command)

### getAlbum&id=$albumid
Fetch data from album page. Returns the album object, a description object and a tracks object. Tracks contain: AlbumASIN, AlbumTitle, TrackID, Format, TrackDuration (ms), ArtistName, TrackTitle, AlbumID, ArtistID, Location, TrackNumber, CleanName (stripped of punctuation /styling), BitRate)

### getUpcoming
Returns: Status, AlbumASIN, DateAdded, AlbumTitle, ArtistName, ReleaseDate, AlbumID, ArtistID, Type

### getWanted
Returns: Status, AlbumASIN, DateAdded, AlbumTitle, ArtistName, ReleaseDate, AlbumID, ArtistID, Type

### getSimilar
Returns similar artists  - with a higher "Count" being more likely to be similar. Returns: Count, ArtistName, ArtistID

### getHistory
Returns: Status, DateAdded, Title, URL (nzb), FolderName, AlbumID, Size (bytes)

### getLogs
Not working yet

### findArtist&name=$artistname[&limit=$limit]
Perform artist query on musicbrainz. Returns: url, score, name, uniquename (contains disambiguation info), id)

### findAlbum&name=$albumname[&limit=$limit]
Perform album query on musicbrainz. Returns: title, url (artist), id (artist), albumurl, albumid, score, uniquename (artist - with disambiguation)

### addArtist&id=$artistid
Add an artist to the db by artistid)

### addAlbum&id=$releaseid
Add an album to the db by album release id

### delArtist&id=$artistid
Delete artist from db by artistid)

### pauseArtist&id=$artistid
Pause an artist in db)

### resumeArtist&id=$artistid
Resume an artist in db)

### refreshArtist&id=$artistid
Refresh info for artist in db from musicbrainz

### queueAlbum&id=$albumid[&new=True&lossless=True]
Mark an album as wanted and start the searcher. Optional paramters: 'new' looks for new versions, 'lossless' looks only for lossless versions

### unqueueAlbum&id=$albumid
Unmark album as wanted / i.e. mark as skipped

### forceSearch
force search for wanted albums - not launched in a separate thread so it may take a bit to complete
### forceProcess[&dir=/path/to/folder]
Force post process albums in download directory - also not launched in a separate thread
### forceActiveArtistsUpdate
force Active Artist Update - also not launched in a separate thread

### getVersion
Returns some version information: git_path, install_type, current_version, installed_version, commits_behind

### checkGithub
Updates the version information above and returns getVersion data

### shutdown
Shut down headphones

### restart
Restart headphones

### update
Update headphones - you may want to check the install type in get version and not allow this if type==exe

### getArtistArt&id=$artistid
Returns either a relative path to the cached image, or a remote url if the image can't be saved to the cache dir

getAlbumArt&id=$albumid
see above

### getArtistInfo&id=$artistid
Returns Summary and Content, both formatted in html.

### getAlbumInfo&id=$albumid
See above, returns Summary and Content.

### getArtistThumb&id=$artistid
Returns either a relative path to the cached thumbnail artist image, or an http:// address if the cache dir can't be written to.

### getAlbumThumb&id=$albumid
See above.

### choose_specific_download&id=$albumid
Gives you a list of results from searcher.searchforalbum(). Basically runs a normal search, but rather than sorting them and downloading the best result, it dumps the data, which you can then pass on to download_specific_release(). Returns a list of dictionaries with params: title, size, url, provider & kind - all of these values must be passed back to download_specific_release

### download_specific_release&id=albumid&title=$title&size=$size&url=$url&provider=$provider&kind=$kind
Allows you to manually pass a choose_specific_download release back to searcher.send_to_downloader()
