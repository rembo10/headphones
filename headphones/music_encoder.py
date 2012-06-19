#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

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
    startAlbumTime=time.time()
    ifencoded=0
    
    if not os.path.exists(tempDirEncode):       
        os.mkdir(tempDirEncode)
    else:
        shutil.rmtree(tempDirEncode)
        time.sleep(1)
        os.mkdir(tempDirEncode)
        
    for r,d,f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                if (headphones.ENCODERLOSSLESS):
                    if (music.lower().endswith('.flac')):
                        musicFiles.append(os.path.join(r, music))
                        musicTemp = os.path.normpath(os.path.splitext(music)[0]+'.'+headphones.ENCODEROUTPUTFORMAT).encode(headphones.SYS_ENCODING)
                        musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
                    else:
                        logger.warn('Music "%s" is already encoded' % (music))
                else:
                    musicFiles.append(os.path.join(r, music))
                    musicTemp = os.path.normpath(os.path.splitext(music)[0]+'.'+headphones.ENCODEROUTPUTFORMAT).encode(headphones.SYS_ENCODING)
                    musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
                            
    if headphones.ENCODER=='lame':
        encoder=os.path.join(headphones.ENCODERFOLDER,'lame')
    elif headphones.ENCODER=='ffmpeg':
        encoder=os.path.join(headphones.ENCODERFOLDER,'ffmpeg')
    i=0
    for music in musicFiles:        
        infoMusic=MediaFile(music)
        if headphones.ENCODER == 'lame':
            if not any(music.lower().endswith('.' + x) for x in ["mp3", "wav"]):
                logger.warn('Lame cant encode "%s" format for "%s", use ffmpeg' % (os.path.splitext(music)[1],music))
            else:
                if (music.lower().endswith('.mp3') and (infoMusic.bitrate/1000<=headphones.BITRATE)): 
                    logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
        else:
            if headphones.ENCODEROUTPUTFORMAT=='ogg':
                if music.lower().endswith('.ogg'):
                    logger.warn('Can not reencode .ogg music "%s"' % (music))
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
            elif (headphones.ENCODEROUTPUTFORMAT=='mp3' or headphones.ENCODEROUTPUTFORMAT=='m4a'):
                if (music.lower().endswith('.'+headphones.ENCODEROUTPUTFORMAT) and (infoMusic.bitrate/1000<=headphones.BITRATE)):
                    logger.warn('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music,headphones.BITRATE))      
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
        i=i+1
        
    shutil.rmtree(tempDirEncode)
    time.sleep(1)   
    for r,d,f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                musicFinalFiles.append(os.path.join(r, music))
    
    if ifencoded==0:
        logger.info('Encoding for folder "%s" is not needed' % (albumPath))
    
    return musicFinalFiles
    
def command(encoder,musicSource,musicDest,albumPath):
    return_code=1
    cmd=''
    startMusicTime=time.time()
    if headphones.ENCODER == 'lame':
        if headphones.ADVANCEDENCODER =='':
            cmd=encoder + ' -h'     
            if headphones.ENCODERVBRCBR=='cbr':
                cmd=cmd+ ' --resample ' + str(headphones.SAMPLINGFREQUENCY) + ' -b ' + str(headphones.BITRATE)
            elif headphones.ENCODERVBRCBR=='vbr':
                cmd=cmd+' -V'+str(headphones.ENCODERQUALITY)
            cmd=cmd+ ' ' + headphones.ADVANCEDENCODER
        else:
            cmd=cmd+' '+ headphones.ADVANCEDENCODER
        cmd=cmd+ ' "' + musicSource + '"'
        cmd=cmd+ ' "' + musicDest +'"'
        
    elif headphones.ENCODER == 'ffmpeg':
        cmd=encoder+ ' -i'
        cmd=cmd+ ' "' + musicSource + '"'
        if headphones.ADVANCEDENCODER =='':
            if headphones.ENCODEROUTPUTFORMAT=='ogg':
                cmd=cmd+ ' -acodec libvorbis'
            if headphones.ENCODEROUTPUTFORMAT=='m4a':
                cmd=cmd+ ' -strict experimental'
            if headphones.ENCODERVBRCBR=='cbr':
                cmd=cmd+ ' -ar ' + str(headphones.SAMPLINGFREQUENCY) + ' -ab ' + str(headphones.BITRATE) + 'k'
            elif headphones.ENCODERVBRCBR=='vbr':
                cmd=cmd+' -aq ' + str(headphones.ENCODERQUALITY)
            cmd=cmd+ ' -y -ac 2 -vn'
        else:
            cmd=cmd+' '+ headphones.ADVANCEDENCODER
        cmd=cmd+ ' "' + musicDest + '"'
    print cmd
    time.sleep(10)
    return_code = call(cmd, shell=True)
    if (return_code==0) and (os.path.exists(musicDest)):
        os.remove(musicSource)
        shutil.move(musicDest,albumPath)
        logger.info('Music "%s" encoded in %s' % (musicSource,getTimeEncode(startMusicTime)))
        
def getTimeEncode(start):
    seconds =int(time.time()-start)
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return "%02d:%02d:%02d" % (hours, minutes, seconds)
