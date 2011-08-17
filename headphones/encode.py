import os
import headphones
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
			cmd=encoder+' -h --resample ' + str(headphones.SAMPLINGFREQUENCY) + ' -b ' + str(headphones.BITRATE)
			cmd=cmd+' "'+os.path.join(music)+'"'
			cmd=cmd+' "'+os.path.join(musicTempFiles[i])+'"'
			return_code = call(cmd, shell=True)
			if return_code==0:
				os.remove(music)
				shutil.move(musicTempFiles[i],os.path.join(albumPath))
			i=i+1	
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