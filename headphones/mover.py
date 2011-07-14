import glob, os, shutil

import headphones

from headphones import logger

def moveFiles():
	for root, dirs, files in os.walk(headphones.DOWNLOAD_DIR):
		for file in files:
			if file[-4:].lower() == '.mp3' and os.path.isfile(file):
				print file
	        	shutil.copy2(os.path.join(root, file), 
	        	os.path.join(path_to_itunes, file))
