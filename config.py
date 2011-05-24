import os
from configobj import ConfigObj
from headphones import config_file

config = ConfigObj(config_file)

General = config['General']
http_host = General['http_host']
http_port = General['http_port']
http_username = General['http_username']
http_password = General['http_password']
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

form = '''<div class="table"><div class="config">
	<form action="configUpdate" method="post">
	<h1><u>Web Interface</u></h1>
	<table class="configtable"><tr><td><p>HTTP Host:</p>
	<input type="text" name="http_host" value="%s" size="30" maxlength="40"/><br />
	<p class="smalltext">i.e. localhost or 0.0.0.0</td>
	<td><p>HTTP Username:</p>
	<input type="text" name="http_username" value="%s" size="30" maxlength="40"/></td></tr>
	<tr><td><br /><p>HTTP Port:</p>
	<input type="text" name="http_port" value="%s" size="20" maxlength="40"/></td>	
	<td><br /><p>HTTP Password:</p>
	<input type="password" name="http_password" value="%s" size="30" maxlength="40"/></td></tr>
	<tr><td><br /><p>Launch Browser on Startup:</p>
    <input type="checkbox" name="launch_browser" value="1" %s/>Enabled</td></tr></table>
	<h1><u>Download Settings</u></h1>
    <table class="configtable"><tr><td><p>SABnzbd Host:</p>
    <input type="text" name="sab_host" value="%s" size="30" maxlength="40"/><br />
    <p class="smalltext">usually localhost:8080</td>
    <td><p>SABnzbd Username:</p>
    <input type="text" name="sab_username" value="%s" size="20" maxlength="40"/></td></tr>
    <tr><td><br /><p>SABnzbd API:</p>
    <input type="text" name="sab_apikey" value="%s" size="46" maxlength="40"/></td>
    <td><br /><p>SABnzbd Password:</p>
    <input type="password" name="sab_password" value="%s" size="20" maxlength="40"/></td></tr>
    <tr><td><br /><p>SABnzbd Category:</p>
    <input type="text" name="sab_category" value="%s" size="20" maxlength="40"/></td>
    <td><br /><p>Music Download Directory:</p>
    <input type="text" name="music_download_dir" value="%s" size="60" maxlength="40"/><br />
    <p class="smalltext">Absolute or relative path to the dir where SAB downloads your music<br />
    i.e. Downloads/music or /Users/name/Downloads/music</td></tr>
    <tr><td><br /><p>Usenet Retention:</p>
    <input type="text" name="usenet_retention" value="%s" size="20" maxlength="40"/></td></tr></table>
	<h1><u>Search Providers</u></h1>
	<table class="configtable"><tr><td><p>Enable NZBMatrix:</p>
    <input type="checkbox" name="nzbmatrix" value="1" %s/>Enabled<br /></td>
    <td><p>NZBMatrix Username:</p>
    <input type="text" name="nzbmatrix_username" value="%s" size="30" maxlength="40"/><br /></td>
    <td><p>NZBMatrix API:</p>
    <input type="text" name="nzbmatrix_apikey" value="%s" size="46" maxlength="40"/></td></tr></table>
    <h1><u>Quality & Post Processing</u></h1>
    <table class="configtable"><tr><td><p>Album Quality:</p>
    <input type="checkbox" name="include_lossless" value="1" %s/>Include lossless 
    <input type="checkbox" name="flac_to_mp3" value="1" %s/>Convert lossless to mp3</td>
    <td><p>iTunes:</p>
    <input type="checkbox" name="move_to_itunes" value="1" %s/>Move downloads to iTunes</td></tr>
    <tr><td><br /><p>Path to iTunes folder:</p>
    <input type="text" name="path_to_itunes" value="%s" size="60" maxlength="40"/><br />
    <p class="smalltext">i.e. Music/iTunes or /Users/name/Music/iTunes</p></td>
    <td><p>Renaming & Metadata:</p>
    <input type="checkbox" name="rename_mp3s" value="1" %s/>Rename & add metadata<br /><br />
    <input type="checkbox" name="cleanup" value="1" %s/>Delete leftover files</td></td></tr>
    <tr><td><br /><p>Album Art:</p>
    <input type="checkbox" name="add_album_art" value="1" %s/>Add album art</td></tr></table>
    <p class="center"><input type="submit" value="     Save Changes    "/></p></form></div></div>''' % (http_host, http_username, 
    http_port, http_password, var_to_chk(launch_browser), sab_host, sab_username, sab_apikey, sab_password,
    sab_category, music_download_dir, usenet_retention, var_to_chk(nzbmatrix), nzbmatrix_username, nzbmatrix_apikey,
    var_to_chk(include_lossless), var_to_chk(flac_to_mp3), var_to_chk(move_to_itunes), path_to_itunes, var_to_chk(rename_mp3s),
    var_to_chk(cleanup), var_to_chk(add_album_art))