import os
import headphones
import shutil
import time

from subprocess import call
from headphones import logger
from lib.mutagen.mp3 import MP3

def encode(albumPath):

	tempDirEncode=os.path.join(albumPath,"temp")
	musicFiles=[]
	musicFinalFiles=[]
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
			if any(music.endswith('.' + x) for x in ["mp3", "flac", "m4a", "wav"]):
				musicFiles.append(os.path.join(r, music))
				musicTemp = os.path.join(os.path.splitext(music)[0])+'.mp3'
				musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
				
	if headphones.ENCODER=='lame':
		encoder=os.path.join(headphones.ENCODERFOLDER,'lame')
	else:
		encoder=os.path.join(headphones.ENCODERFOLDER,'ffmpeg')
	i=0
	for music in musicFiles:
		return_code=1
		if headphones.ENCODER == 'lame':
			if not any(music.endswith('.' + x) for x in ["mp3", "wav"]):
				logger.warn('Lame cant encode "%s" format for "%s", use ffmpeg' % (os.path.splitext(music)[1],music))
			else:
				if (music.endswith('.mp3') and (MP3(music).info.bitrate/1000<=headphones.BITRATE)): 
					logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))
				else:
					cmd=encoder+' -h --resample ' + str(headphones.SAMPLINGFREQUENCY) + ' -b ' + str(headphones.BITRATE)
					cmd=cmd+' "'+os.path.join(music)+'"'
					cmd=cmd+' "'+os.path.join(musicTempFiles[i])+'"'
					return_code = call(cmd, shell=True)
					print ('Return_code: ' + str(return_code))
					if return_code==0:
						os.remove(music)
						shutil.move(musicTempFiles[i],os.path.join(albumPath))
		else:
			if (music.endswith('.mp3')):
				if ((MP3(music).info.bitrate/1000<=headphones.BITRATE)):
					logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))
			else:
				cmd=encoder+' -i'
				cmd=cmd+' "'+os.path.join(music)+'"'
				cmd=cmd+' -ac 2 -vn -ar ' + str(headphones.SAMPLINGFREQUENCY) + ' -ab ' + str(headphones.BITRATE) +'k'
				cmd=cmd+' "'+os.path.join(musicTempFiles[i])+'"'
				return_code = call(cmd, shell=True)
				print return_code
				if return_code==0:
					os.remove(music)
					shutil.move(musicTempFiles[i],os.path.join(albumPath))
		i=i+1
				
	shutil.rmtree(tempDirEncode)
	time.sleep(1)
	logger.info('Encoding for folder "%s" is completed' % (albumPath))
	for r,d,f in os.walk(albumPath):
		for music in f:
			if any(music.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				musicFinalFiles.append(os.path.join(r, music))
	return musicFinalFiles