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
import multiprocessing

import subprocess
from headphones import logger
from beets.mediafile import MediaFile

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
            logger.error(u'Details for xld profile %s not found, files will not be re-encoded' % (xldProfile))
            return None

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
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                
                if not XLD:
                    encoderFormat = headphones.ENCODEROUTPUTFORMAT.encode(headphones.SYS_ENCODING)
                else:
                    xldMusicFile = os.path.join(r, music)
                    xldInfoMusic = MediaFile(xldMusicFile)
                    encoderFormat = xldFormat
                
                if (headphones.ENCODERLOSSLESS):
                    ext = os.path.normpath(os.path.splitext(music)[1].lstrip(".")).lower()
                    if not XLD and ext == 'flac' or XLD and (ext != xldFormat and (xldInfoMusic.bitrate / 1000 > 400)):
                        musicFiles.append(os.path.join(r, music))
                        musicTemp = os.path.normpath(os.path.splitext(music)[0] + '.' + encoderFormat)
                        musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
                    else:
                        logger.debug('%s is already encoded' % (music))
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
    encoder_failed = False
    jobs = []

    for music in musicFiles:        
        infoMusic=MediaFile(music)
        encode = False

        if XLD:
            if xldBitrate and (infoMusic.bitrate / 1000 <= xldBitrate):
                logger.info('%s has bitrate <= %skb, will not be re-encoded' % (music.decode(headphones.SYS_ENCODING, 'replace'), xldBitrate))
            else:
                encode = True
        elif headphones.ENCODER == 'lame':
            if not any(music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.' + x) for x in ["mp3", "wav"]):
                logger.warn(u'Lame cannot encode %s format for %s, use ffmpeg' % (os.path.splitext(music)[1].decode(headphones.SYS_ENCODING, 'replace'),music.decode(headphones.SYS_ENCODING, 'replace')))
            else:
                if (music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.mp3') and (int(infoMusic.bitrate / 1000) <= headphones.BITRATE)):
                    logger.info('%s has bitrate <= %skb, will not be re-encoded' % (music.decode(headphones.SYS_ENCODING, 'replace'),headphones.BITRATE))
                else:
                    encode = True
        else:
            if headphones.ENCODEROUTPUTFORMAT=='ogg':
                if music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.ogg'):
                    logger.warn('Cannot re-encode .ogg %s' % (music.decode(headphones.SYS_ENCODING, 'replace')))
                else:
                    encode = True
            elif (headphones.ENCODEROUTPUTFORMAT=='mp3' or headphones.ENCODEROUTPUTFORMAT=='m4a'):
                if (music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.'+headphones.ENCODEROUTPUTFORMAT) and (int(infoMusic.bitrate / 1000 ) <= headphones.BITRATE)):
                    logger.info('%s has bitrate <= %skb, will not be re-encoded' % (music.decode(headphones.SYS_ENCODING, 'replace'),headphones.BITRATE))
                else:
                    encode = True
        # encode
        if encode:
            job = (encoder, music, musicTempFiles[i], albumPath)
            jobs.append(job)
        else:
            musicFiles[i] = None
            musicTempFiles[i] = None

        i=i+1

    # Encode music files
    if len(jobs) > 0:
        if headphones.ENCODER_MULTICORE:
            if headphones.ENCODER_MULTICORE_COUNT == 0:
                processes = multiprocessing.cpu_count()
            else:
                processes = headphones.ENCODER_MULTICORE_COUNT

            logger.debug("Multi-core encoding enabled, %d processes" % processes)
        else:
            processes = 1

        # Use multiprocessing only if it's worth the overhead. and if it is
        # enabled. If not, then use the old fashioned way.
        if processes > 1:
            pool = multiprocessing.Pool(processes=processes)
            results = pool.map_async(command_map, jobs)

            # No new processes will be created, so close it and wait for all
            # processes to finish
            pool.close()
            pool.join()

            # Retrieve the results
            results = results.get()
        else:
            results = map(command_map, jobs)

        # The results are either True or False, so determine if one is False
        encoder_failed = not all(results)

    musicFiles = filter(None, musicFiles)
    musicTempFiles = filter(None, musicTempFiles)

    # check all files to be encoded now exist in temp directory
    if not encoder_failed and musicTempFiles:
        for dest in musicTempFiles:
            if not os.path.exists(dest):
                encoder_failed = True
                logger.error('Encoded file %s does not exist in the destination temp directory' % (dest.decode(headphones.SYS_ENCODING, 'replace')))

    # No errors, move from temp to parent
    if not encoder_failed and musicTempFiles:
        i = 0
        for dest in musicTempFiles:
            if os.path.exists(dest):
                source = musicFiles[i]
                if headphones.DELETE_LOSSLESS_FILES:
                    os.remove(source)
                check_dest = os.path.join(albumPath, os.path.split(dest)[1])
                if os.path.exists(check_dest):
                    os.remove(check_dest)
                try:
                    shutil.move(dest, albumPath)
                except Exception, e:
                    logger.error('Could not move %s to %s : %s' % (dest.decode(headphones.SYS_ENCODING, 'replace'), albumPath.decode(headphones.SYS_ENCODING, 'replace'), e))
                    encoder_failed = True
                    break
            i += 1

    # remove temp directory
    shutil.rmtree(tempDirEncode)

    # Return with error if any encoding errors
    if encoder_failed:
        logger.error('One or more files failed to encode, check debuglog and ensure you have the latest version of %s installed' % (headphones.ENCODER))
        return None

    time.sleep(1)
    for r,d,f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                musicFinalFiles.append(os.path.join(r, music))
    
    if not musicTempFiles:
        logger.info('Encoding for folder %s is not required' % (albumPath.decode(headphones.SYS_ENCODING, 'replace')))
    
    return musicFinalFiles

def command_map(args):
    return command(*args)

def command(encoder,musicSource,musicDest,albumPath):

    cmd=[]
    startMusicTime=time.time()

    if XLD:
        xldDestDir = os.path.split(musicDest)[0]
        cmd = [encoder]
        cmd.extend([musicSource])
        cmd.extend(['--profile'])
        cmd.extend([xldProfile])
        cmd.extend(['-o'])
        cmd.extend([xldDestDir])

    elif headphones.ENCODER == 'lame':
        cmd = [encoder]
        opts = []
        if headphones.ADVANCEDENCODER =='':
            opts.extend(['-h'])
            if headphones.ENCODERVBRCBR=='cbr':
                opts.extend(['--resample', str(headphones.SAMPLINGFREQUENCY), '-b', str(headphones.BITRATE)])
            elif headphones.ENCODERVBRCBR=='vbr':
                opts.extend(['-v', str(headphones.ENCODERQUALITY)])
        else:
            advanced = (headphones.ADVANCEDENCODER.split())
            for tok in advanced:
                opts.extend([tok.encode(headphones.SYS_ENCODING)])
        opts.extend([musicSource])
        opts.extend([musicDest])
        cmd.extend(opts)

    elif headphones.ENCODER == 'ffmpeg':
        cmd = [encoder, '-i', musicSource]
        opts = []
        if headphones.ADVANCEDENCODER =='':
            if headphones.ENCODEROUTPUTFORMAT=='ogg':
                opts.extend(['-acodec', 'libvorbis'])
            if headphones.ENCODEROUTPUTFORMAT=='m4a':
                opts.extend(['-strict', 'experimental'])
            if headphones.ENCODERVBRCBR=='cbr':
                opts.extend(['-ar', str(headphones.SAMPLINGFREQUENCY), '-ab', str(headphones.BITRATE) + 'k'])
            elif headphones.ENCODERVBRCBR=='vbr':
                opts.extend(['-aq', str(headphones.ENCODERQUALITY)])
            opts.extend(['-y', '-ac', '2', '-vn'])
        else:
            advanced = (headphones.ADVANCEDENCODER.split())
            for tok in advanced:
                opts.extend([tok.encode(headphones.SYS_ENCODING)])
        opts.extend([musicDest])
        cmd.extend(opts)

    # Encode

    logger.info('Encoding %s...' % (musicSource.decode(headphones.SYS_ENCODING, 'replace')))
    logger.debug(subprocess.list2cmdline(cmd))

    # stop windows opening the cmd
    startupinfo = None
    if headphones.SYS_PLATFORM == "win32":
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except AttributeError:
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW

    p = subprocess.Popen(cmd, startupinfo=startupinfo, stdin=open(os.devnull, 'rb'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate(headphones.ENCODER)

    # error if return code not zero
    if p.returncode:
        logger.error('Encoding failed for %s' % (musicSource.decode(headphones.SYS_ENCODING, 'replace')))
        out = stdout if stdout else stderr
        out = out.decode(headphones.SYS_ENCODING, 'replace')
        outlast2lines = '\n'.join(out.splitlines()[-2:])
        logger.error('%s error details: %s' % (headphones.ENCODER, outlast2lines))
        out = out.rstrip("\n")
        logger.debug(out)
        encoded = False
    else:
        logger.info('%s encoded in %s' % (musicSource.decode(headphones.SYS_ENCODING, 'replace'),getTimeEncode(startMusicTime)))
        encoded = True

    return encoded

def getTimeEncode(start):
    seconds =int(time.time()-start)
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return "%02d:%02d:%02d" % (hours, minutes, seconds)

