import os
import headphones
import shutil
import time

from subprocess import call
from headphones import logger
from lib.beets.mediafile import MediaFile

try:
    import argparse
except ImportError:
    import lib.argparse as argparse

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
			if any(music.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				musicFiles.append(os.path.join(r, music))
				musicTemp = os.path.splitext(music)[0]+'.'+headphones.ENCODEROUTPUTFORMAT
				musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
				
	if headphones.ENCODER=='lame':
		encoder=os.path.join(headphones.ENCODERFOLDER,'lame')
	elif headphones.ENCODER=='ffmpeg':
		encoder=os.path.join(headphones.ENCODERFOLDER,'ffmpeg')
	i=0
	for music in musicFiles:		
		infoMusic=MediaFile(music)

		if headphones.ENCODER == 'lame':
			if not any(music.endswith('.' +headphones.ENCODEROUTPUTFORMAT) for x in ["mp3", "wav"]):
				logger.warn('Lame cant encode "%s" format for "%s", use ffmpeg' % (os.path.splitext(music)[1],music))
			else:
				if (music.endswith('.mp3') and (infoMusic.bitrate/1000<=headphones.BITRATE)): 
					logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))
				else:
					command(encoder,music,musicTempFiles[i],albumPath)
		else:
			if headphones.ENCODEROUTPUTFORMAT=='ogg':
				if music.endswith('.ogg'):
					logger.warn('Can not reencode .ogg music "%s"' % (music))
				else:
					command(encoder,music,musicTempFiles[i],albumPath)
			elif (headphones.ENCODEROUTPUTFORMAT=='mp3' or headphones.ENCODEROUTPUTFORMAT=='m4a'):
				if (music.endswith('.'+headphones.ENCODEROUTPUTFORMAT) and (infoMusic.bitrate/1000<=headphones.BITRATE)):
					logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))		
				else:
					command(encoder,music,musicTempFiles[i],albumPath)
		i=i+1
				
	shutil.rmtree(tempDirEncode)
	time.sleep(1)
	logger.info('Encoding for folder "%s" is completed' % (albumPath))
	for r,d,f in os.walk(albumPath):
		for music in f:
			if any(music.endswith('.' + x) for x in headphones.MEDIA_FORMATS):
				musicFinalFiles.append(os.path.join(r, music))
	return musicFinalFiles
	
def command(encoder,musicSource,musicDest,albumPath):
	return_code=1
	cmd=''
	if headphones.ENCODER == 'lame':
		cmd=encoder + ' -h --resample ' + str(headphones.SAMPLINGFREQUENCY) + ' -b ' + str(headphones.BITRATE)
		cmd=cmd+ ' ' + headphones.ADVANCEDENCODER
		cmd=cmd+ ' "' + musicSource + '"'
		cmd=cmd+ ' "' + musicDest +'"'
	elif headphones.ENCODER == 'ffmpeg':
		cmd=encoder+ ' -i'
		cmd=cmd+ ' "' + musicSource + '"'
		if headphones.ENCODEROUTPUTFORMAT=='ogg':
			cmd=cmd+ ' -acodec libvorbis'
		if headphones.ENCODEROUTPUTFORMAT=='m4a':
			cmd=cmd+ ' -strict experimental'
		cmd=cmd+ ' -y -ac 2 -map_metadata 0:0,s0 -vn -ar ' + str(headphones.SAMPLINGFREQUENCY) + ' -ab ' + str(headphones.BITRATE) + 'k'
		cmd=cmd+ ' ' + headphones.ADVANCEDENCODER
		cmd=cmd+ ' "' + musicDest + '"'
	return_code = call(cmd, shell=True)
	if (return_code==0) and (os.path.exists(musicDest)):
		os.remove(musicSource)
		shutil.move(musicDest,albumPath)