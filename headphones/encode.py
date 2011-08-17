import os
import headphones
import argparse
import shutil
import time

from subprocess import call

def encode(albumPath):

	tempDirEncode=os.path.join(albumPath,"temp")
	musicFiles=[]
	musicTempFiles=[]
	encoder =""
	if not os.path.exists(tempDirEncode):		
		os.mkdir(tempDirEncode)
	else:
		shutil.rmtree(tempDirEncode)
		time.sleep(1)
		os.mkdir(tempDirEncode)
		
	for r,d,f in os.walk(albumPath):
		for music in f:
			if any(music.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				musicFiles.append(os.path.join(r, music))
				musicTempFiles.append(os.path.join(tempDirEncode, music))
	
	if headphones.ENCODER=='lame':
		encoder=os.path.join(headphones.ENCODERFOLDER,'lame')
	else:
		encoder=os.path.join(headphones.ENCODERFOLDER,'ffmpeg')
	i=0
	for music in musicFiles:
		return_code=1
		if headphones.ENCODER == 'lame':			
			cmd=encoder+' -h --resample ' + headphones.SAMPLINGFREQUENCY + ' -b ' + headphones.BITRATE
			cmd=cmd+' "'+os.path.join(music)+'"'
			cmd=cmd+' "'+os.path.join(musicTempFiles[i])+'"'
			return_code = call(cmd, shell=True)
			if return_code==0:
				os.remove(music)
				os.rename(musicTempFiles[i],music)
			i=i+1	
		else:			
			cmd=encoder+' -i'
			cmd=cmd+' "'+os.path.join(music)+'"'
			cmd=cmd+' -ac 2 -vn -ar ' + headphones.SAMPLINGFREQUENCY + ' -ab ' + headphones.BITRATE +'k'
			cmd=cmd+' "'+os.path.join(musicTempFiles[i])+'"'
			return_code = call(cmd, shell=True)
			print return_code
			if return_code==0:
				os.remove(music)
				os.rename(musicTempFiles[i],music)
			i=i+1
			
	shutil.rmtree(tempDirEncode)