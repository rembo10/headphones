from headphones import db

_header = '''
	<html>
	<head>
		<title>Headphones</title>
		<link rel="stylesheet" type="text/css" href="css/style.css" />
		<link rel="icon" type="image/x-icon" href="images/favicon.ico" /> 
		<link rel="apple-touch-icon" href="images/headphoneslogo.png" />
	</head>
	<body>
	<div class="container">'''
	
_shutdownheader = '''
	<html>
	<head>
		<title>Headphones</title>
		<link rel="stylesheet" type="text/css" href="css/style.css" />
		<link rel="icon" type="image/x-icon" href="images/favicon.ico" /> 
		<link rel="apple-touch-icon" href="images/headphoneslogo.png" />
		<meta http-equiv="refresh" content="%s;url=index">
	</head>
	<body>
	<div class="container">'''
			
_logobar = '''
		<div class="logo"><a href="home"><img src="images/headphoneslogo.png" border="0">headphones</a></div>
			<div class="search"><form action="findArtist" method="GET">
			<input type="text" value="Add an artist" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="name" />
			<input type="submit" /></form></div><br />
	'''

_nav = '''<div class="nav">
					<a href="home">HOME</a>
					<a href="upcoming">UPCOMING</a>
					<a href="extras">EXTRAS</a>
					<a href="manage">MANAGE</a>    
					<a href="history">HISTORY</a>
					<a href="logs">LOGS</a>
					<a href="config">SETTINGS</a>
					<div style="float:right">
					  <a href="restart" title="Restart"><img src="images/restart.png" height="15px" width="15px" border="0"></a>
					  <a href="shutdown" title="Shutdown"><img src="images/shutdown.png" height="15px" width="15px" border="0"></a>
					</div>
			</div>'''
	
_footer = '''
	</div><div class="footer"><br /><div class="center"><form action="https://www.paypal.com/cgi-bin/webscr" method="post">
<input type="hidden" name="cmd" value="_s-xclick">
<input type="hidden" name="hosted_button_id" value="93FFC6WDV97QS">
<input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
<img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
</form><br /><div class="version">Version: %s</div>
</div></div>
	</body>
	</html>'''
	
configform = form = '''
<br>
  	<center>
	  	<div class="smalltext">
		  	<a href="#web_interface" >Web Interface</a> |
		  	<a href="#download" class="smalltext">Download Settings</a> |
		  	<a href="#providers" class="smalltext">Search Providers</a> |
		  	<a href="#post_processing" class="smalltext">Quality &amp; Post Processing</a> |
		  	<a href="#advanced_settings" class="smalltext">Advanced Settings</a>
		  </div>
  	</center>
  <div class="table">
    <div class="config">
	    <form action="configUpdate" method="post">
        <a name="web_interface"><h1><u>Web Interface</u></h1></a>

        <table class="configtable" summary="Web Interface">
            <tr>
                <td>
                  <p>
                    HTTP Host: <br><br>
                    <input type="text" name="http_host" value="%s" size="30" maxlength="40"><br>
                    <i class="smalltext">i.e. localhost or 0.0.0.0</i>
                  </p>
                </td>
                <td>
                  <p>
                    HTTP Username: <br><br>
                    <input type="text" name="http_username" value="%s" size="30" maxlength="40">
                  </p>
                </td>
            </tr>

            <tr>
                <td>
                    <p>
                      HTTP Port: <br><br>
                      <input type="text" name="http_port" value="%s" size="20" maxlength="40">
                    </p>
                </td>

                <td>
                    <p>
                      HTTP Password: <br><br>
                      <input type="password" name="http_password" value="%s" size="30" maxlength="40">
                    </p>
                </td>
            </tr>

            <tr>
                <td>
                    <p>Launch Browser on Startup:<input type="checkbox" name="launch_browser" value="1" %s /></p>
                </td>
            </tr>
        </table>

        <a name="download"><h1><u>Download Settings</u></h1></a>

        <table class="configtable" summary="Download Settings">
            <tr>
                <td>
                    <p>SABnzbd Host:</p><input type="text" name="sab_host" value="%s" size="30" maxlength="40"><br>

                    <i class="smalltext">usually localhost:8080</i>
                </td>

                <td>
                    <p>SABnzbd Username:</p><input type="text" name="sab_username" value="%s" size="20" maxlength="40">
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p>SABnzbd API:</p><input type="text" name="sab_apikey" value="%s" size="46" maxlength="40">
                </td>

                <td>
                    <br>

                    <p>SABnzbd Password:</p><input type="password" name="sab_password" value="%s" size="20" maxlength="40">
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p>SABnzbd Category:</p><input type="text" name="sab_category" value="%s" size="20" maxlength="40">
                </td>

                <td>
                    <br>

                    <p>Music Download Directory:</p><input type="text" name="download_dir" value="%s" size="60"><br>

                    <i class="smalltext">Full path to the directory where SAB downloads your music<br>
                    i.e. /Users/name/Downloads/music</i>
                </td>
            </tr>
            
            <tr>
                <td>
                    <br>

                    <p>Use Black Hole:</p><input type="checkbox" name="blackhole" value=1 %s />
                </td>

                <td>
                    <br>

                    <p>Black Hole Directory:</p><input type="text" name="blackhole_dir" value="%s" size="60"><br>

                    <i class="smalltext">Folder your Download program watches for NZBs</i>
                </td>
            </tr>


            <tr>
                <td>
                    <br>

                    <p>Usenet Retention:</p><input type="text" name="usenet_retention" value="%s" size="20" maxlength="40">
                </td>
            </tr>
        </table>

        <a name="providers"><h1><u>Search Providers</u></h1></a>

        <table class="configtable" summary="Search Providers">
            <tr>
                <td>
                    <p>NZBMatrix: <input type="checkbox" name="nzbmatrix" value="1" %s /></p>
                </td>

                <td>
                    <p>
                      NZBMatrix Username: <br>
                      <input type="text" name="nzbmatrix_username" value="%s" size="30" maxlength="40">
                    </p>
                </td>

                <td>
                    <p>
                      NZBMatrix API: <br>
                      <input type="text" name="nzbmatrix_apikey" value="%s" size="46" maxlength="40">
                    </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p>Newznab: <input type="checkbox" name="newznab" value="1" %s /></p>
                </td>

                <td>
                    <br>

                    <p>
                      Newznab Host:<br>
                      <input type="text" name="newznab_host" value="%s" size="30" maxlength="40"><br>
                      <i class="smalltext">i.e. http://nzb.su</i>
                    </p>
                </td>

                <td>
                    <br>

                    <p>
                      Newznab API:<br>
                      <input type="text" name="newznab_apikey" value="%s" size="46" maxlength="40">
                    </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p>NZBs.org:<input type="checkbox" name="nzbsorg" value="1" %s /></p>
                </td>

                <td>
                    <br>

                    <p>
                      NZBs.org UID:<br>
                      <input type="text" name="nzbsorg_uid" value="%s" size="30" maxlength="40">
                    </p>
                </td>

                <td>
                    <br>

                    <p>
                      NZBs.org Hash:<br>
                      <input type="text" name="nzbsorg_hash" value="%s" size="46" maxlength="40">
                    </p>
                </td>
            </tr>
        </table>

        <a name="post_processing"><h1><u>Quality &amp; Post Processing</u></h1></a>

        <table class="configtable" summary="Quality & Post Processing">
            <tr>
                <td>
                	<b>Album Quality:</b>
                   	  <p>
                   	  <input type="radio" name="preferred_quality" value="0" %s />Highest Quality excluding Lossless<br /><br />
                      <input type="radio" name="preferred_quality" value="1" %s />Highest Quality including Lossless<br /><br />
                      <input type="radio" name="preferred_quality" value="3" %s />Lossless Only<br /><br />
                      <input type="radio" name="preferred_quality" value="2" %s />Preferred Bitrate: 
    					<input type="text" name="preferred_bitrate" value="%s" size="5" maxlength="5" />kbps <br>
                      	<i class="smalltext2"><input type="checkbox" name="detect_bitrate" value="1" %s />Auto-Detect Preferred Bitrate </i>
                	  </p>
                </td>
                <td>
                      <b>Post-Processing:</b>
                      <p>
                      	<input type="checkbox" name="move_files" value="1" %s />Move downloads to Destination Folder<br />
                      	<input type="checkbox" name="rename_files" value="1" %s />Rename files<br>
                        <input type="checkbox" name="correct_metadata" value="1" %s />Correct metadata<br>
                        <input type="checkbox" name="cleanup_files" value="1" %s />Delete leftover files (.m3u, .nfo, .sfv, .nzb, etc.)<br>
                      	<input type="checkbox" name="add_album_art" value="1" %s>Add album art as 'folder.jpg' to album folder<br>
                      	<input type="checkbox" name="embed_album_art" value="1" %s>Embed album art in each file
                      </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p><b>Path to Destination folder</b>:<br><input type="text" name="destination_dir" value="%s" size="60">
                      <br>
                      <i class="smalltext">i.e. /Users/name/Music/iTunes or /Volumes/share/music</i>
                    </p>
                </td>
            </tr>
		</table>
        <a name="advanced_settings"><h1><u>Advanced Settings</u></h1></a>
        
        <table class="configtable" summary="Advanced Settings">
            <tr>
                <td>
                	<b>Renaming Options:</b>
                    <br>

                    <p><b>Folder Format</b>:<br><input type="text" name="folder_format" value="%s" size="60">
                      <br>
                      <i class="smalltext">Use: artist, album and year, '/' for directories. <br />E.g.: artist/album [year]</i>
                    </p>
                    
                    <p><b>File Format</b>:<br><input type="text" name="file_format" value="%s" size="60">
                      <br>
                      <i class="smalltext">Use: tracknumber, title, artist, album and year</i>
                    </p>
                </td>
                <td>
                      <b>Miscellaneous:</b>
                      <p>
                      	<input type="checkbox" name="include_extras" value="1" %s />Automatically Include Extras When Adding an Artist<br />
                      <i class="smalltext">Extras includes: EPs, Compilations, Live Albums, Remix Albums and Singles</i>
                      </p>
                    <p><b>Log Directory</b>:<br><input type="text" name="log_dir" value="%s" size="60">
                    </p>
                </td>
            </tr>

        </table>

        <p class="center"><input type="submit" value="Save Changes"><br>
        (Web Interface changes require a restart to take effect)</p>
      </form>
    </div>
  </div>'''
  
  
def displayAlbums(ArtistID, Type=None):

	myDB = db.DBConnection()

	results = myDB.select('SELECT AlbumTitle, ReleaseDate, AlbumID, Status, ArtistName, AlbumASIN from albums WHERE ArtistID=? AND Type=? order by ReleaseDate DESC', [ArtistID, Type])

	if not len(results):
		return
		
	typeheadings = {'Album' : 'Official Albums',
					'Compilation': 'Compilations',
					'EP': 'EPs',
					'Live':	'Live Albums',
					'Remix': 'Remixes',
					'Single': 'Singles'}
	
	page = ['''<p class="mediumcentered">%s</p>
			<table border="0" cellpadding="3">
				<tr>
					<th align="left" width="30"></th>
					<th align="left" width="120">Album Name</th>
					<th align="center" width="100">Release Date</th>
					<th align="center" width="180">Status</th>
					<th align="center">Have</th>
				</tr>''' % typeheadings[Type]]
	i = 0
	while i < len(results):
		totaltracks = len(myDB.select('SELECT TrackTitle from tracks WHERE AlbumID=?', [results[i][2]]))
		havetracks = len(myDB.select('SELECT TrackTitle from have WHERE ArtistName like ? AND AlbumTitle like ?', [results[i][4], results[i][0]]))
		try:
			percent = (havetracks*100)/totaltracks
			if percent > 100:
				percent = 100
		except ZeroDivisionError:
				percent = 100
		if results[i][3] == 'Skipped':
			newStatus = '''%s [<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">want</a>]''' % (results[i][3], results[i][2], ArtistID)
		elif results[i][3] == 'Wanted':
			newStatus = '''<b>%s</b>[<A class="external" href="unqueueAlbum?AlbumID=%s&ArtistID=%s">skip</a>]''' % (results[i][3], results[i][2], ArtistID)				
		elif results[i][3] == 'Downloaded':
			newStatus = '''<b>%s</b>[<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">retry</a>][<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s&new=True">new</a>]''' % (results[i][3], results[i][2], ArtistID, results[i][2], ArtistID)
		elif results[i][3] == 'Snatched':
			newStatus = '''<b>%s</b>[<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s">retry</a>][<A class="external" href="queueAlbum?AlbumID=%s&ArtistID=%s&new=True">new</a>]''' % (results[i][3], results[i][2], ArtistID, results[i][2], ArtistID)
		else:
			newStatus = '%s' % (results[i][3])
		page.append('''<tr>
							<td align="left"><img src="http://ec1.images-amazon.com/images/P/%s.01.MZZZZZZZ.jpg" height="50" width="50"></td>
							<td align="left" width="240"><a href="albumPage?AlbumID=%s">%s</a> 
									(<A class="external" href="http://musicbrainz.org/release-group/%s.html">link</a>)</td>
							<td align="center" width="160">%s</td>
							<td align="center">%s</td>
							<td><div class="progress-container"><div style="width: %s%%"><div class="smalltext3">%s/%s</div></div></div></td>
					</tr>''' % (results[i][5], results[i][2], results[i][0], results[i][2], results[i][1], newStatus, percent, havetracks, totaltracks))	
		i = i+1
	page.append('</table><br />')
		
	return ''.join(page)