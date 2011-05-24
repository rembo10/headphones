from configobj import ConfigObj

def configCreate(path):
	config = ConfigObj()
	config.filename = path
	config['General'] = {}
	config['General']['http_host'] = '0.0.0.0'
	config['General']['http_port'] = 8181
	config['General']['http_username'] = ''
	config['General']['http_password'] = ''
	config['General']['launch_browser'] = 0
	config['General']['include_lossless'] = 0
	config['General']['flac_to_mp3'] = 0
	config['General']['move_to_itunes'] = 0
	config['General']['path_to_itunes'] = ''
	config['General']['rename_mp3s'] = 0
	config['General']['cleanup'] = 0
	config['General']['add_album_art'] = 0
	config['General']['music_download_dir'] = ''
	config['General']['usenet_retention'] = 500
	config['SABnzbd'] = {}
	config['SABnzbd']['sab_host'] = ''
	config['SABnzbd']['sab_username'] = ''
	config['SABnzbd']['sab_password'] = ''
	config['SABnzbd']['sab_apikey'] = ''
	config['SABnzbd']['sab_category'] = ''
	config['NZBMatrix'] = {}
	config['NZBMatrix']['nzbmatrix'] = 0
	config['NZBMatrix']['nzbmatrix_username'] = ''
	config['NZBMatrix']['nzbmatrix_apikey'] = ''

	config.write()