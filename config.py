import os
from configobj import ConfigObj
from headphones import config_file

config = ConfigObj(config_file)

General = config['General']
http_host = General['http_host']
http_port = General['http_port']
http_username = General['http_username']
http_password = General['http_password']
try:
	http_root = General['http_root']
except KeyError:
	General['http_root'] = ''
	config.write()
launch_browser = General['launch_browser']
usenet_retention = General['usenet_retention']
include_lossless = General['include_lossless']
flac_to_mp3 = General['flac_to_mp3']
move_to_itunes = General['move_to_itunes']
path_to_itunes = General['path_to_itunes']
rename_mp3s = General['rename_mp3s']
cleanup = General['cleanup']
add_album_art = General['add_album_art']
music_download_dir = General['music_download_dir']
NZBMatrix = config['NZBMatrix']
nzbmatrix = NZBMatrix['nzbmatrix']
nzbmatrix_username = NZBMatrix['nzbmatrix_username']
nzbmatrix_apikey = NZBMatrix['nzbmatrix_apikey']
Newznab = config['Newznab']
newznab = Newznab['newznab']
newznab_host = Newznab['newznab_host']
newznab_apikey = Newznab['newznab_apikey']
NZBsorg = config['NZBsorg']
nzbsorg = NZBsorg['nzbsorg']
nzbsorg_uid = NZBsorg['nzbsorg_uid']
nzbsorg_hash = NZBsorg['nzbsorg_hash']
SABnzbd = config['SABnzbd']
sab_username = SABnzbd['sab_username']
sab_password = SABnzbd['sab_password']
sab_apikey = SABnzbd['sab_apikey']
sab_category = SABnzbd['sab_category']
sab_host = SABnzbd['sab_host']

def var_to_chk(variable):
	if variable == '1':
		return 'Checked'
	else:
		return ''

form = '''
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

                    <p>Music Download Directory:</p><input type="text" name="music_download_dir" value="%s" size="60" maxlength="40"><br>

                    <i class="smalltext">Absolute or relative path to the dir where SAB downloads your music<br>
                    i.e. Downloads/music or /Users/name/Downloads/music</i>
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
                    <input type="checkbox" name="include_lossless" value="1" %s />Include lossless <br>
                    <input type="checkbox" name="flac_to_mp3" value="1" %s />Convert lossless to mp3
                </td>

                <td>
                    <p>
                      <p><b>iTunes:</b></p>
                      <input type="checkbox" name="move_to_itunes" value="1" %s />Move downloads to iTunes
                    </p>
                </td>
            </tr>

            <tr>
                <td>
                    <br>

                    <p><b>Path to Music folder</b>:<br><input type="text" name="path_to_itunes" value="%s" size="60" maxlength="40">
                      <br>
                      <i class="smalltext">i.e. /Users/name/Music/iTunes or /Volumes/share/music</i>
                    </p>
                </td>
                <td>
                      <b>Renaming &amp; Metadata:</b>
                      <p>
                        <input type="checkbox" name="rename_mp3s" value="1" %s />Rename &amp; add metadata
                        <br>
                        <input type="checkbox" name="cleanup" value="1" %s />Delete leftover files
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
        (For now, all changes require a restart to take effect)</p>
      </form>
    </div>
  </div>''' % (http_host, http_username, http_port, http_password, var_to_chk(launch_browser), sab_host, sab_username, sab_apikey, sab_password, sab_category, music_download_dir, usenet_retention, var_to_chk(nzbmatrix), nzbmatrix_username, nzbmatrix_apikey, var_to_chk(newznab), newznab_host,  newznab_apikey, var_to_chk(nzbsorg), nzbsorg_uid, nzbsorg_hash, var_to_chk(include_lossless), var_to_chk(flac_to_mp3), var_to_chk(move_to_itunes),  path_to_itunes, var_to_chk(rename_mp3s), var_to_chk(cleanup), var_to_chk(add_album_art))
    
