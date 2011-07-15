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
			
_logobar = '''
		<div class="logo"><a href="home"><img src="images/headphoneslogo.png" border="0">headphones<a></div>
			<div class="search"><form action="findArtist" method="GET">
			<input type="text" value="Add an artist" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="name" />
			<input type="submit" /></form></div><br />
	'''

_nav = '''<div class="nav">
					<a href="home">HOME</a>
					<a href="upcoming">UPCOMING</a>
					<a href="manage">MANAGE</a>    
					<a href="history">HISTORY</a>
					<a href="config">SETTINGS</a>
					<div style="float:right">
					  <a href="restart" title="Restart"><img src="images/restart.png" height="15px" width="15px"></a>
					  <a href="shutdown" title="Shutdown"><img src="images/shutdown.png" height="15px" width="15px"></a>
					</div>
			</div>'''
	
_footer = '''
	</div><div class="footer"><br /><div class="center"><form action="https://www.paypal.com/cgi-bin/webscr" method="post">
<input type="hidden" name="cmd" value="_s-xclick">
<input type="hidden" name="hosted_button_id" value="93FFC6WDV97QS">
<input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
<img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
</form>
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
		  	<a href="#post_processing" class="smalltext">Quality &amp; Post Processing</a>
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

                    <p>Music Download Directory:</p><input type="text" name="download_dir" value="%s" size="60" maxlength="40"><br>

                    <i class="smalltext">Absolute or relative path to the dir where SAB downloads your music<br>
                    i.e. Downloads/music or /Users/name/Downloads/music</i>
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
                    <p><b>Album Quality:</b></p>
                    <input type="checkbox" name="prefer_lossless" value="1" %s />Prefer lossless <br>
                    <input type="checkbox" name="flac_to_mp3" value="1" %s />Convert lossless to mp3
                </td>

                <td>
                    <p>
                      <p><b>iTunes:</b></p>
                      <input type="checkbox" name="move_files" value="1" %s />Move downloads to Music Folder
                    </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p><b>Path to Music folder</b>:<br><input type="text" name="music_dir" value="%s" size="60" maxlength="200">
                      <br>
                      <i class="smalltext">i.e. /Users/name/Music/iTunes or /Volumes/share/music</i>
                    </p>
                </td>
                <td>
                      <b>Renaming &amp; Metadata:</b>
                      <p>
                        <input type="checkbox" name="rename_files" value="1" %s />Rename &amp; add metadata
                        <br>
                        <input type="checkbox" name="cleanup_files" value="1" %s />Delete leftover files
                      </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>
                    <p><b>Album Art:</b></p>
                    <input type="checkbox" name="add_album_art" value="1" %s>Add album art
                </td>
            </tr>
        </table>

        <p class="center"><input type="submit" value="Save Changes"><br>
        (Web Interface changes require a restart to take effect)</p>
      </form>
    </div>
  </div>'''