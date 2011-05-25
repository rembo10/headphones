import glob, os, shutil
from configobj import ConfigObj
from headphones import config_file

config = ConfigObj(config_file)

General = config['General']
move_to_itunes = General['move_to_itunes']
path_to_itunes = General['path_to_itunes']
rename_mp3s = General['rename_mp3s']
cleanup = General['cleanup']
add_album_art = General['add_album_art']
music_download_dir = General['music_download_dir']

def moveFiles():
	for root, dirs, files in os.walk(music_download_dir):
		for file in files:
			if file[-4:].lower() == '.mp3' and os.path.isfile(file):
				print file
	        	shutil.copy2(os.path.join(root, file), 
	        	os.path.join(path_to_itunes, file))
