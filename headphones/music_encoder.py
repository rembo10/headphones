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

import time
import shutil
import subprocess
import multiprocessing

import os
import headphones
from headphones import logger
from beets.mediafile import MediaFile


# xld
import getXldProfile


def encode(albumPath):
    use_xld = headphones.CONFIG.ENCODER == 'xld'

    # Return if xld details not found
    if use_xld:
        (xldProfile, xldFormat, xldBitrate) = getXldProfile.getXldProfile(
            headphones.CONFIG.XLDPROFILE)
        if not xldFormat:
            logger.error('Details for xld profile \'%s\' not found, files will not be re-encoded',
                         xldProfile)
            return None
    else:
        xldProfile = None

    tempDirEncode = os.path.join(albumPath, "temp")
    musicFiles = []
    musicFinalFiles = []
    musicTempFiles = []
    encoder = ""

    # Create temporary directory, but remove the old one first.
    try:
        if os.path.exists(tempDirEncode):
            shutil.rmtree(tempDirEncode)
            time.sleep(1)

        os.mkdir(tempDirEncode)
    except Exception as e:
        logger.exception("Unable to create temporary directory")
        return None

    for r, d, f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                if not use_xld:
                    encoderFormat = headphones.CONFIG.ENCODEROUTPUTFORMAT.encode(
                        headphones.SYS_ENCODING)
                else:
                    xldMusicFile = os.path.join(r, music)
                    xldInfoMusic = MediaFile(xldMusicFile)
                    encoderFormat = xldFormat

                if headphones.CONFIG.ENCODERLOSSLESS:
                    ext = os.path.normpath(os.path.splitext(music)[1].lstrip(".")).lower()
                    if not use_xld and ext == 'flac' or use_xld and (
                            ext != xldFormat and (xldInfoMusic.bitrate / 1000 > 400)):
                        musicFiles.append(os.path.join(r, music))
                        musicTemp = os.path.normpath(
                            os.path.splitext(music)[0] + '.' + encoderFormat)
                        musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))
                    else:
                        logger.debug('%s is already encoded', music)
                else:
                    musicFiles.append(os.path.join(r, music))
                    musicTemp = os.path.normpath(os.path.splitext(music)[0] + '.' + encoderFormat)
                    musicTempFiles.append(os.path.join(tempDirEncode, musicTemp))

    if headphones.CONFIG.ENCODER_PATH:
        encoder = headphones.CONFIG.ENCODER_PATH.encode(headphones.SYS_ENCODING)
    else:
        if use_xld:
            encoder = os.path.join('/Applications', 'xld')
        elif headphones.CONFIG.ENCODER == 'lame':
            if headphones.SYS_PLATFORM == "win32":
                # NEED THE DEFAULT LAME INSTALL ON WIN!
                encoder = "C:/Program Files/lame/lame.exe"
            else:
                encoder = "lame"
        elif headphones.CONFIG.ENCODER == 'ffmpeg':
            if headphones.SYS_PLATFORM == "win32":
                encoder = "C:/Program Files/ffmpeg/bin/ffmpeg.exe"
            else:
                encoder = "ffmpeg"
        elif headphones.CONFIG.ENCODER == 'libav':
            if headphones.SYS_PLATFORM == "win32":
                encoder = "C:/Program Files/libav/bin/avconv.exe"
            else:
                encoder = "avconv"

    i = 0
    encoder_failed = False
    jobs = []

    for music in musicFiles:
        infoMusic = MediaFile(music)
        encode = False

        if use_xld:
            if xldBitrate and (infoMusic.bitrate / 1000 <= xldBitrate):
                logger.info('%s has bitrate <= %skb, will not be re-encoded',
                            music.decode(headphones.SYS_ENCODING, 'replace'), xldBitrate)
            else:
                encode = True
        elif headphones.CONFIG.ENCODER == 'lame':
            if not any(
                    music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.' + x) for x
                    in ["mp3", "wav"]):
                logger.warn('Lame cannot encode %s format for %s, use ffmpeg',
                            os.path.splitext(music)[1], music)
            else:
                if music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.mp3') and (
                    int(infoMusic.bitrate / 1000) <= headphones.CONFIG.BITRATE):
                    logger.info('%s has bitrate <= %skb, will not be re-encoded', music,
                                headphones.CONFIG.BITRATE)
                else:
                    encode = True
        else:
            if headphones.CONFIG.ENCODEROUTPUTFORMAT == 'ogg':
                if music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith('.ogg'):
                    logger.warn('Cannot re-encode .ogg %s',
                                music.decode(headphones.SYS_ENCODING, 'replace'))
                else:
                    encode = True
            elif headphones.CONFIG.ENCODEROUTPUTFORMAT == 'mp3' or headphones.CONFIG.ENCODEROUTPUTFORMAT == 'm4a':
                if music.decode(headphones.SYS_ENCODING, 'replace').lower().endswith(
                                '.' + headphones.CONFIG.ENCODEROUTPUTFORMAT) and (
                    int(infoMusic.bitrate / 1000) <= headphones.CONFIG.BITRATE):
                    logger.info('%s has bitrate <= %skb, will not be re-encoded', music,
                                headphones.CONFIG.BITRATE)
                else:
                    encode = True
        # encode
        if encode:
            job = (encoder, music, musicTempFiles[i], albumPath, xldProfile)
            jobs.append(job)
        else:
            musicFiles[i] = None
            musicTempFiles[i] = None

        i = i + 1

    # Encode music files
    if len(jobs) > 0:
        processes = 1

        # Use multicore if enabled
        if headphones.CONFIG.ENCODER_MULTICORE:
            if headphones.CONFIG.ENCODER_MULTICORE_COUNT == 0:
                processes = multiprocessing.cpu_count()
            else:
                processes = headphones.CONFIG.ENCODER_MULTICORE_COUNT

            logger.debug("Multi-core encoding enabled, spawning %d processes",
                         processes)

        # Use multiprocessing only if it's worth the overhead. and if it is
        # enabled. If not, then use the old fashioned way.
        if processes > 1:
            with logger.listener():
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
                logger.error("Encoded file '%s' does not exist in the destination temp directory",
                             dest)

    # No errors, move from temp to parent
    if not encoder_failed and musicTempFiles:
        i = 0
        for dest in musicTempFiles:
            if os.path.exists(dest):
                source = musicFiles[i]
                if headphones.CONFIG.DELETE_LOSSLESS_FILES:
                    os.remove(source)
                check_dest = os.path.join(albumPath, os.path.split(dest)[1])
                if os.path.exists(check_dest):
                    os.remove(check_dest)
                try:
                    shutil.move(dest, albumPath)
                except Exception as e:
                    logger.error('Could not move %s to %s: %s', dest, albumPath, e)
                    encoder_failed = True
                    break
            i += 1

    # remove temp directory
    shutil.rmtree(tempDirEncode)

    # Return with error if any encoding errors
    if encoder_failed:
        logger.error(
            "One or more files failed to encode. Ensure you have the latest version of %s installed.",
            headphones.CONFIG.ENCODER)
        return None

    time.sleep(1)
    for r, d, f in os.walk(albumPath):
        for music in f:
            if any(music.lower().endswith('.' + x.lower()) for x in headphones.MEDIA_FORMATS):
                musicFinalFiles.append(os.path.join(r, music))

    if not musicTempFiles:
        logger.info('Encoding for folder \'%s\' is not required', albumPath)

    return musicFinalFiles


def command_map(args):
    """
    Wrapper for the '[multiprocessing.]map()' method, to unpack the arguments
    and wrap exceptions.
    """

    # Initialize multiprocessing logger
    if multiprocessing.current_process().name != "MainProcess":
        logger.initMultiprocessing()

    # Start encoding
    try:
        return command(*args)
    except Exception:
        logger.exception("Encoder raised an exception.")
        return False


def command(encoder, musicSource, musicDest, albumPath, xldProfile):
    """
    Encode a given music file with a certain encoder. Returns True on success,
    or False otherwise.
    """

    startMusicTime = time.time()
    cmd = []

    if xldProfile:
        xldDestDir = os.path.split(musicDest)[0]
        cmd = [encoder]
        cmd.extend([musicSource])
        cmd.extend(['--profile'])
        cmd.extend([xldProfile])
        cmd.extend(['-o'])
        cmd.extend([xldDestDir])

    # Lame
    elif headphones.CONFIG.ENCODER == 'lame':
        cmd = [encoder]
        opts = []
        if not headphones.CONFIG.ADVANCEDENCODER:
            opts.extend(['-h'])
            if headphones.CONFIG.ENCODERVBRCBR == 'cbr':
                opts.extend(['--resample', str(headphones.CONFIG.SAMPLINGFREQUENCY), '-b',
                             str(headphones.CONFIG.BITRATE)])
            elif headphones.CONFIG.ENCODERVBRCBR == 'vbr':
                opts.extend(['-v', str(headphones.CONFIG.ENCODERQUALITY)])
        else:
            advanced = (headphones.CONFIG.ADVANCEDENCODER.split())
            for tok in advanced:
                opts.extend([tok.encode(headphones.SYS_ENCODING)])
        opts.extend([musicSource])
        opts.extend([musicDest])
        cmd.extend(opts)

    # FFmpeg
    elif headphones.CONFIG.ENCODER == 'ffmpeg':
        cmd = [encoder, '-i', musicSource]
        opts = []
        if not headphones.CONFIG.ADVANCEDENCODER:
            if headphones.CONFIG.ENCODEROUTPUTFORMAT == 'ogg':
                opts.extend(['-acodec', 'libvorbis'])
            if headphones.CONFIG.ENCODEROUTPUTFORMAT == 'm4a':
                opts.extend(['-strict', 'experimental'])
            if headphones.CONFIG.ENCODERVBRCBR == 'cbr':
                opts.extend(['-ar', str(headphones.CONFIG.SAMPLINGFREQUENCY), '-ab',
                             str(headphones.CONFIG.BITRATE) + 'k'])
            elif headphones.CONFIG.ENCODERVBRCBR == 'vbr':
                opts.extend(['-aq', str(headphones.CONFIG.ENCODERQUALITY)])
            opts.extend(['-y', '-ac', '2', '-vn'])
        else:
            advanced = (headphones.CONFIG.ADVANCEDENCODER.split())
            for tok in advanced:
                opts.extend([tok.encode(headphones.SYS_ENCODING)])
        opts.extend([musicDest])
        cmd.extend(opts)

    # Libav
    elif headphones.CONFIG.ENCODER == "libav":
        cmd = [encoder, '-i', musicSource]
        opts = []
        if not headphones.CONFIG.ADVANCEDENCODER:
            if headphones.CONFIG.ENCODEROUTPUTFORMAT == 'ogg':
                opts.extend(['-acodec', 'libvorbis'])
            if headphones.CONFIG.ENCODEROUTPUTFORMAT == 'm4a':
                opts.extend(['-strict', 'experimental'])
            if headphones.CONFIG.ENCODERVBRCBR == 'cbr':
                opts.extend(['-ar', str(headphones.CONFIG.SAMPLINGFREQUENCY), '-ab',
                             str(headphones.CONFIG.BITRATE) + 'k'])
            elif headphones.CONFIG.ENCODERVBRCBR == 'vbr':
                opts.extend(['-aq', str(headphones.CONFIG.ENCODERQUALITY)])
            opts.extend(['-y', '-ac', '2', '-vn'])
        else:
            advanced = (headphones.CONFIG.ADVANCEDENCODER.split())
            for tok in advanced:
                opts.extend([tok.encode(headphones.SYS_ENCODING)])
        opts.extend([musicDest])
        cmd.extend(opts)

    # Prevent Windows from opening a terminal window
    startupinfo = None

    if headphones.SYS_PLATFORM == "win32":
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except AttributeError:
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW

    # Encode
    logger.info('Encoding %s...' % (musicSource.decode(headphones.SYS_ENCODING, 'replace')))
    logger.debug(subprocess.list2cmdline(cmd))

    process = subprocess.Popen(cmd, startupinfo=startupinfo,
                               stdin=open(os.devnull, 'rb'), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(headphones.CONFIG.ENCODER)

    # Error if return code not zero
    if process.returncode:
        logger.error(
            'Encoding failed for %s' % (musicSource.decode(headphones.SYS_ENCODING, 'replace')))
        out = stdout if stdout else stderr
        out = out.decode(headphones.SYS_ENCODING, 'replace')
        outlast2lines = '\n'.join(out.splitlines()[-2:])
        logger.error('%s error details: %s' % (headphones.CONFIG.ENCODER, outlast2lines))
        out = out.rstrip("\n")
        logger.debug(out)
        encoded = False
    else:
        logger.info('%s encoded in %s', musicSource, getTimeEncode(startMusicTime))
        encoded = True

    return encoded


def getTimeEncode(start):
    seconds = int(time.time() - start)
    hours = seconds / 3600
    seconds -= 3600 * hours
    minutes = seconds / 60
    seconds -= 60 * minutes
    return "%02d:%02d:%02d" % (hours, minutes, seconds)
