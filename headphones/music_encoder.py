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

# xld
      
if headphones.ENCODER == 'xld':
    import getXldProfile
    XLD = True
else:
    XLD = False

def encode(albumPath):

    # Return if xld details not found
    
    if XLD:
        global xldProfile
        (xldProfile, xldFormat, xldBitrate) = getXldProfile.getXldProfile(headphones.XLDPROFILE)
        if not xldFormat:
            logger.error(u'Details for xld profile "%s" not found, will not be reencoded' % (xldProfile))
            return None

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
                
                if not XLD:
                    encoderFormat = headphones.ENCODEROUTPUTFORMAT.encode(headphones.SYS_ENCODING)
                else:
                    xldMusicFile = os.path.join(r, music)
                    xldInfoMusic = MediaFile(xldMusicFile)
                    encoderFormat = xldFormat
                
                if (headphones.ENCODERLOSSLESS):
                    ext = os.path.normpath(os.path.splitext(music)[1].lstrip(".")).lower()
                    if not XLD and ext == 'flac' or XLD and (ext != xldFormat and (xldInfoMusic.bitrate / 1000 > 500)):
                        musicFiles.append(os.path.join(r, music))
                        musicTemp = os.path.normpath(os.path.splitext(music)[0] + '.' + encoderFormat)
                        musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
                    else:
                        logger.debug('Music "%s" is already encoded' % (music))
                else:
                    musicFiles.append(os.path.join(r, music))
                    musicTemp = os.path.normpath(os.path.splitext(music)[0] + '.' + encoderFormat)
                    musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))

    if headphones.ENCODER_PATH:
        encoder = headphones.ENCODER_PATH.encode(headphones.SYS_ENCODING)
    else:
        if XLD:
            encoder = os.path.join('/Applications', 'xld')                            
        elif headphones.ENCODER =='lame':
            if headphones.SYS_PLATFORM == "win32":
                ## NEED THE DEFAULT LAME INSTALL ON WIN!
                encoder = "C:/Program Files/lame/lame.exe"
            else:
                encoder="lame"
        elif headphones.ENCODER =='ffmpeg':
            if headphones.SYS_PLATFORM == "win32":
                encoder = "C:/Program Files/ffmpeg/bin/ffmpeg.exe"
            else:
                encoder="ffmpeg"

    i=0
    for music in musicFiles:        
        infoMusic=MediaFile(music)
        
        if XLD:
            if xldBitrate and (infoMusic.bitrate / 1000 <= xldBitrate):
                logger.info('Music "%s" has bitrate <= "%skbit", will not be reencoded' % (music.decode(headphones.SYS_ENCODING, 'replace'), xldBitrate))      
            else:
                command(encoder,music,musicTempFiles[i],albumPath)
                ifencoded=1
        elif headphones.ENCODER == 'lame':
            if not any(music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.' + x) for x in ["mp3", "wav"]):
                logger.warn(u'Lame cant encode "%s" format for "%s", use ffmpeg' % (os.path.splitext(music)[1].decode(headphones.SYS_ENCODING, 'replace'),music.decode(headphones.SYS_ENCODING, 'replace')))
            else:
                if (music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.mp3') and (int(infoMusic.bitrate/1000)<=headphones.BITRATE)): 
                    logger.info('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music.decode(headphones.SYS_ENCODING, 'replace'),headphones.BITRATE))
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
        else:
            if headphones.ENCODEROUTPUTFORMAT=='ogg':
                if music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.ogg'):
                    logger.warn('Can not reencode .ogg music "%s"' % (music.decode(headphones.SYS_ENCODING, 'replace')))
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
            elif (headphones.ENCODEROUTPUTFORMAT=='mp3' or headphones.ENCODEROUTPUTFORMAT=='m4a'):
                if (music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.'+headphones.ENCODEROUTPUTFORMAT) and (int(infoMusic.bitrate/1000)<=headphones.BITRATE)):
                    logger.info('Music "%s" has bitrate<="%skbit" will not be reencoded' % (music.decode(headphones.SYS_ENCODING, 'replace'),headphones.BITRATE))      
                else:
                    command(encoder,music,musicTempFiles[i],albumPath)
                    ifencoded=1
        i=i+1
        
    time.sleep(1)   
    for r,d,f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                musicFinalFiles.append(os.path.join(r, music))
    
    if ifencoded==0:
        logger.info('Encoding for folder "%s" is not needed' % (albumPath.decode(headphones.SYS_ENCODING, 'replace')))
    
    return musicFinalFiles
    
def command(encoder,musicSource,musicDest,albumPath):
    
    return_code=1
    cmd=''
    startMusicTime=time.time()

    if XLD:
        xldDestDir = os.path.split(musicDest)[0]
        cmd = '"' + encoder + '"'
        cmd = cmd + ' "' + musicSource + '"'
        cmd = cmd + ' --profile'
        cmd = cmd + ' "' + xldProfile + '"'
        cmd = cmd + ' -o'
        cmd = cmd + ' "' + xldDestDir + '"'
        
    elif headphones.ENCODER == 'lame':
        if headphones.ADVANCEDENCODER =='':
            cmd='"' + encoder + '"' + ' -h'     
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
        cmd='"' + encoder + '"' + ' -i'
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

    logger.debug(cmd)
    try:
        return_code = call(cmd, shell=True)

        if (return_code==0) and (os.path.exists(musicDest)):
            if headphones.DELETE_LOSSLESS_FILES:
                os.remove(musicSource)
            shutil.move(musicDest,albumPath)
            logger.info('Music "%s" encoded in %s' % (musicSource,getTimeEncode(startMusicTime)))

    except subprocess.CalledProcessError, e:
        logger.warn('Music "%s" encoding error : %s' % (musicSource, e.output))

def getTimeEncode(start):
    seconds =int(time.time()-start)
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return "%02d:%02d:%02d" % (hours, minutes, seconds)
