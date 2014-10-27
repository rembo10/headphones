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

# Most of this lifted from here: https://github.com/SzieberthAdam/gneposis-cdgrab

import os
import sys
import re
import shutil
import commands
import subprocess
import time
import copy
import glob

import headphones
from headphones import logger
from mutagen.flac import FLAC

CUE_HEADER = {
    'genre': '^REM GENRE (.+?)$',
    'date': '^REM DATE (.+?)$',
    'discid': '^REM DISCID (.+?)$',
    'comment': '^REM COMMENT (.+?)$',
    'catalog': '^CATALOG (.+?)$',
    'artist': '^PERFORMER (.+?)$',
    'title': '^TITLE (.+?)$',
    'file': '^FILE (.+?) (WAVE|FLAC)$',
    'accurateripid': '^REM ACCURATERIPID (.+?)$'
}

CUE_TRACK = 'TRACK (\d\d) AUDIO$'

CUE_TRACK_INFO = {
    'artist': 'PERFORMER (.+?)$',
    'title': 'TITLE (.+?)$',
    'isrc': 'ISRC (.+?)$',
    'index': 'INDEX (\d\d) (.+?)$'
}

ALBUM_META_FILE_NAME = 'album.dat'
SPLIT_FILE_NAME = 'split.dat'

ALBUM_META_ALBUM_BY_CUE = ('artist', 'title', 'date', 'genre')

HTOA_LENGTH_TRIGGER = 3

WAVE_FILE_TYPE_BY_EXTENSION = {
    '.wav': 'Waveform Audio',
    '.wv': 'WavPack',
    '.ape': "Monkey's Audio",
    '.m4a': 'Apple Lossless',
    '.flac': 'Free Lossless Audio Codec'
}

# TODO: Only alow flac for now
#SHNTOOL_COMPATIBLE = ('Waveform Audio', 'WavPack', 'Free Lossless Audio Codec')
SHNTOOL_COMPATIBLE = ('Free Lossless Audio Codec')

def check_splitter(command):
    '''Check xld or shntools installed'''
    try:
        env = os.environ.copy()
        if 'xld' in command:
            env['PATH'] += os.pathsep + '/Applications'
        devnull = open(os.devnull)
        subprocess.Popen([command], stdout=devnull, stderr=devnull, env=env).communicate()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return False
    return True

def split_baby(split_file, split_cmd):
    '''Let's split baby'''
    logger.info('Splitting %s...', split_file.decode(headphones.SYS_ENCODING, 'replace'))
    logger.debug(subprocess.list2cmdline(split_cmd))

    # Prevent Windows from opening a terminal window
    startupinfo = None

    if headphones.SYS_PLATFORM == "win32":
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except AttributeError:
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW

    env = os.environ.copy()
    if 'xld' in split_cmd:
        env['PATH'] += os.pathsep + '/Applications'

    process = subprocess.Popen(split_cmd, startupinfo=startupinfo,

    stdin=open(os.devnull, 'rb'), stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, env=env)
    stdout, stderr = process.communicate()
    if process.returncode:
        logger.error('Split failed for %s', split_file.decode(headphones.SYS_ENCODING, 'replace'))
        out = stdout if stdout else stderr
        logger.error('Error details: %s', out.decode(headphones.SYS_ENCODING, 'replace'))
        return False
    else:
        logger.info('Split success %s', split_file.decode(headphones.SYS_ENCODING, 'replace'))
        return True

def check_list(list, ignore=0):
    '''Checks a list for None elements. If list have None (after ignore index) then it should pass only if all elements
    are None threreafter. Returns a tuple without the None entries.'''

    if ignore:
        try:
            list[int(ignore)]
        except:
            raise ValueError('non-integer ignore index or ignore index not in list')

    list1 = list[:ignore]
    list2 = list[ignore:]

    try:
        first_none = list2.index(None)
    except:
        return tuple(list1 + list2)

    for i in range(first_none, len(list2)):
        if list2[i]:
            raise ValueError('non-None entry after None entry in list at index {0}'.format(i))

    while True:
        list2.remove(None)
        try:
            list2.index(None)
        except:
            break

    return tuple(list1+list2)

def trim_cue_entry(string):
    '''Removes leading and trailing "s.'''
    if string[0] == '"' and string[-1] == '"':
        string = string[1:-1]
    return string

def int_to_str(value, length=2):
    '''Converts integer to string eg 3 to "03"'''
    try:
        int(value)
    except:
        raise ValueError('expected an integer value')

    content = str(value)
    while len(content) < length:
        content = '0' + content
    return content

def split_file_list(ext=None):
    file_list = [None for m in range(100)]
    if ext and ext[0] != '.':
        ext = '.' + ext
    for f in os.listdir('.'):
        if f[:11] == 'split-track':
            if (ext and ext == os.path.splitext(f)[-1]) or not ext:
                filename_parser = re.search('split-track(\d\d)', f)
                track_nr = int(filename_parser.group(1))
                if cue.htoa() and not os.path.exists('split-track00'+ext):
                    track_nr -= 1
                file_list[track_nr] = WaveFile(f, track_nr=track_nr)
    return check_list(file_list, ignore=1)


class Directory:
    def __init__(self, path):
        self.path = path
        self.name = os.path.split(self.path)[-1]
        self.content = []
        self.update()

    def filter(self, classname):
        content = []
        for c in self.content:
            if c.__class__.__name__ == classname:
                content.append(c)
        return content
    
    def tracks(self, ext=None, split=False):
        content = []
        for c in self.content:
            ext_match = False
            if c.__class__.__name__ == 'WaveFile':
                if not ext or (ext and ext == c.name_ext):
                    ext_match = True
                if ext_match and c.track_nr:
                    if not split or (split and c.split_file):
                        content.append(c)
        return content
    
    def update(self):
        def check_match(filename):
            for i in self.content:
                if i.name == filename:
                    return True
            return False
        
        def identify_track_number(filename):
            if 'split-track' in filename:
                search = re.search('split-track(\d\d)', filename)
                if search:
                    n = int(search.group(1))
                    if n:
                        return n
            for n in range(0,100):
                search = re.search(int_to_str(n), filename)
                if search:
                    # TODO: not part of other value such as year
                    return n

        list_dir = glob.glob(os.path.join(self.path, '*'))
        
        # TODO: for some reason removes only one file
        rem_list = []
        for i in self.content:
            if i.name not in list_dir:
                rem_list.append(i)
        for i in rem_list:
            self.content.remove(i)
        
        for i in list_dir:
            if not check_match(i):
                # music file
                if os.path.splitext(i)[-1] in WAVE_FILE_TYPE_BY_EXTENSION.keys():
                    track_nr = identify_track_number(i)
                    if track_nr:
                        self.content.append(WaveFile(self.path + os.sep + i, track_nr=track_nr))
                    else:
                        self.content.append(WaveFile(self.path + os.sep + i))
                
                # cue file
                elif os.path.splitext(i)[-1] == '.cue':
                    self.content.append(CueFile(self.path + os.sep + i))

                # meta file
                elif i == ALBUM_META_FILE_NAME:
                    self.content.append(MetaFile(self.path + os.sep + i))
                
                # directory
                elif os.path.isdir(i):
                    self.content.append(Directory(self.path + os.sep + i))
                
                else:
                    self.content.append(File(self.path + os.sep + i))

class File:
    def __init__(self, path):
        self.path = path
        self.name = os.path.split(self.path)[-1]

        self.name_name = ''.join(os.path.splitext(self.name)[:-1])
        self.name_ext = os.path.splitext(self.name)[-1]
        self.split_file = True if self.name_name[:11] == 'split-track' else False

    def get_name(self, ext=True, cmd=False):

        if ext == True:
            content = self.name
        elif ext == False:
            content = self.name_name
        elif ext[0] == '.':
            content = self.name_name + ext
        else:
            raise ValueError('ext parameter error')

        if cmd:
            content = content.replace(' ', '\ ')

        return content

class CueFile(File):
    def __init__(self, path):

        def header_parser():
            global line_content
            c = self.content.splitlines()
            header_dict = {}
            #remaining_headers = CUE_HEADER
            remaining_headers = copy.copy(CUE_HEADER)
            line_index = 0
            match = True
            while match:
                match = False
                saved_match = None
                line_content = c[line_index]
                for e in remaining_headers:
                    search_result = re.search(remaining_headers[e], line_content, re.I)
                    if search_result:
                        search_content = trim_cue_entry(search_result.group(1))
                        header_dict[e] = search_content
                        saved_match = e
                        match = True
                        line_index += 1
                if saved_match:
                    del remaining_headers[saved_match]
            return header_dict, line_index

        def track_parser(start_line):
            c = self.content.splitlines()
            line_index = start_line
            line_content = c[line_index]
            search_result = re.search(CUE_TRACK, line_content, re.I)
            if not search_result:
                raise ValueError('inconsistent CUE sheet, TRACK expected at line {0}'.format(line_index+1))
            track_nr = int(search_result.group(1))
            line_index += 1
            next_track = False
            track_meta = {}
            # we make room for future indexes
            track_meta['index'] = [None for m in range(100)]

            while not next_track:
                if line_index < len(c):
                    line_content = c[line_index]

                    artist_search = re.search(CUE_TRACK_INFO['artist'], line_content, re.I)
                    title_search = re.search(CUE_TRACK_INFO['title'], line_content, re.I)
                    isrc_search = re.search(CUE_TRACK_INFO['isrc'], line_content, re.I)
                    index_search = re.search(CUE_TRACK_INFO['index'], line_content, re.I)

                    if artist_search:
                        if trim_cue_entry(artist_search.group(1)) != self.header['artist']:
                            track_meta['artist'] = trim_cue_entry(artist_search.group(1))
                        line_index += 1
                    elif title_search:
                        track_meta['title'] = trim_cue_entry(title_search.group(1))
                        line_index += 1
                    elif isrc_search:
                        track_meta['isrc'] = trim_cue_entry(isrc_search.group(1))
                        line_index += 1
                    elif index_search:
                        track_meta['index'][int(index_search.group(1))] = index_search.group(2)
                        line_index += 1
                    elif re.search(CUE_TRACK, line_content, re.I):
                        next_track = True
                    elif line_index == len(c)-1 and not line_content:
                        # last line is empty
                        line_index += 1
                    elif re.search('FLAGS DCP$', line_content, re.I):
                        track_meta['dcpflag'] = True
                        line_index += 1
                    else:
                        raise ValueError('unknown entry in track error, line {0}'.format(line_index+1))
                else:
                    next_track = True

            track_meta['index'] = check_list(track_meta['index'], ignore=1)

            return track_nr, track_meta, line_index

        File.__init__(self, path)

        try:
            with open(self.name) as cue_file:
                self.content = cue_file.read()
        except:
            self.content = None

        if not self.content:
            try:
                 with open(self.name, encoding="cp1252") as cue_file:
                     self.content = cue_file.read()
            except:
                raise ValueError('Cant encode CUE Sheet.')

        if self.content[0] == '\ufeff':
            self.content = self.content[1:]

        header = header_parser()

        self.header = header[0]

        line_index = header[1]

        # we make room for tracks
        tracks = [None for m in range(100)]

        while line_index < len(self.content.splitlines()):
            parsed_track = track_parser(line_index)
            line_index = parsed_track[2]
            tracks[parsed_track[0]] = parsed_track[1]

        self.tracks = check_list(tracks, ignore=1)

    def get_meta(self):
        content = ''
        for i in ALBUM_META_ALBUM_BY_CUE:
            if self.header.get(i):
                content += i + '\t' + self.header[i] + '\n'
            else:
                content += i + '\t' + '\n'

        for i in range(len(self.tracks)):
            if self.tracks[i]:
                if self.tracks[i].get('artist'):
                    content += 'track'+int_to_str(i) + 'artist' + '\t' + self.tracks[i].get('artist') + '\n'
                if self.tracks[i].get('title'):
                    content += 'track'+int_to_str(i) + 'title' + '\t' + self.tracks[i].get('title') + '\n'
        return content

    def htoa(self):
        '''Returns true if Hidden Track exists.'''
        if int(self.tracks[1]['index'][1][-5:-3]) >= HTOA_LENGTH_TRIGGER:
            return True
        return False

    def breakpoints(self):
        '''Returns track break points. Identical as CUETools' cuebreakpoints, with the exception of my standards for HTOA.'''
        content = ''
        for t in range(len(self.tracks)):
            if t == 1 and not self.htoa():
                content += ''
            elif t >= 1:
                t_index = self.tracks[t]['index']
                content += t_index[1]
                if (t < len(self.tracks) - 1):
                    content += '\n'
        return content

class MetaFile(File):
    def __init__(self, path):
        File.__init__(self, path)
        with open(self.path) as meta_file:
            self.rawcontent = meta_file.read()

        content = {}
        content['tracks'] = [None for m in range(100)]
 
        for l in self.rawcontent.splitlines():
            parsed_line = re.search('^(.+?)\t(.+?)$', l)
            if parsed_line:
                if parsed_line.group(1)[:5] == 'track':
                    parsed_track = re.search('^track(\d\d)(.+?)$', parsed_line.group(1))
                    if not parsed_track:
                        raise ValueError('Syntax error in album meta file')
                    if not content['tracks'][int(parsed_track.group(1))]:
                        content['tracks'][int(parsed_track.group(1))] = dict()
                    content['tracks'][int(parsed_track.group(1))][parsed_track.group(2)] = parsed_line.group(2)
                else:
                    content[parsed_line.group(1)] = parsed_line.group(2)
 
        content['tracks'] = check_list(content['tracks'], ignore=1)
 
        self.content = content
                          
    def flac_tags(self, track_nr):
        common_tags = dict()
        freeform_tags = dict()

        # common flac tags
        common_tags['artist'] = self.content['artist']
        common_tags['album'] = self.content['title']
        common_tags['title'] = self.content['tracks'][track_nr]['title']
        common_tags['tracknumber'] = str(track_nr)
        common_tags['tracktotal'] = str(len(self.content['tracks'])-1)
        if 'date' in self.content:
            common_tags['date'] = self.content['date']
        if 'genre' in meta.content:
            common_tags['genre'] = meta.content['genre']

        #freeform tags
        #freeform_tags['country'] = self.content['country']
        #freeform_tags['releasedate'] = self.content['releasedate']

        return common_tags, freeform_tags

    def folders(self):
        artist = self.content['artist']
        album = self.content['date'] + ' - ' + self.content['title'] + ' (' +  self.content['label'] + ' - ' + self.content['catalog'] + ')'
        return artist, album
    
    def complete(self):
        '''Check MetaFile for containing all data'''
        self.__init__(self.path)
        for l in self.rawcontent.splitlines():
            if re.search('^[0-9A-Za-z]+?\t$', l):
                return False
        return True
    
    def count_tracks(self):
        '''Returns tracks count'''
        return len(self.content['tracks']) - self.content['tracks'].count(None)

class WaveFile(File):
    def __init__(self, path, track_nr=None):
        File.__init__(self, path)

        self.track_nr = track_nr
        self.type = WAVE_FILE_TYPE_BY_EXTENSION[self.name_ext]

    def filename(self, ext=None, cmd=False):
        title = meta.content['tracks'][self.track_nr]['title']

        if ext:                
            if ext[0] != '.':
                ext = '.' + ext
        else:
            ext = self.name_ext

        f_name = int_to_str(self.track_nr) + ' - ' + title + ext

        if cmd:
            f_name = f_name.replace(' ', '\ ')

        f_name = f_name.replace('!', '')
        f_name = f_name.replace('?', '')
        f_name = f_name.replace('/', ';')

        return f_name

    def tag(self):
        if self.type == 'Free Lossless Audio Codec':
            f = FLAC(self.name)
            tags = meta.flac_tags(self.track_nr)
            for t in tags[0]:
                f[t] = tags[0][t]
            f.save()

    def mutagen(self):
        if self.type == 'Free Lossless Audio Codec':
            return FLAC(self.name)

def split(albumpath):

    os.chdir(albumpath)
    base_dir = Directory(os.getcwd())
    cue = None
    wave = None

    # determining correct cue file
    # if perfect match found
    for _cue in base_dir.filter('CueFile'):
        for _wave in base_dir.filter('WaveFile'):
            if _cue.header['file'] == _wave.name:
                logger.info('CUE Sheet found: {0}'.format(_cue.name))
                logger.info('Music file found: {0}'.format(_wave.name))
                cue = _cue
                wave = _wave
    # if no perfect match found then try without extensions
    if not cue and not wave:
        logger.info('No match for music files, trying to match without extensions...')
        for _cue in base_dir.filter('CueFile'):
            for _wave in base_dir.filter('WaveFile'):
                if ''.join(os.path.splitext(_cue.header['file'])[:-1]) == _wave.name_name:
                    logger.info('Possible CUE Sheet found: {0}'.format(_cue.name))
                    logger.info('CUE Sheet refers music file: {0}'.format(_cue.header['file']))
                    logger.info('Possible Music file found: {0}'.format(_wave.name))
                    cue = _cue
                    wave = _wave
                    cue.header['file'] = wave.name
    # if still no match then raise an exception
    if not cue and not wave:
        raise ValueError('No music file match found!')

    # Split with xld or shntool
    splitter = 'shntool'
    xldprofile = None

    # use xld profile to split cue
    if headphones.CONFIG.ENCODER == 'xld' and headphones.CONFIG.MUSIC_ENCODER and headphones.CONFIG.XLDPROFILE:
        import getXldProfile
        xldprofile, xldformat, _ = getXldProfile.getXldProfile(headphones.CONFIG.XLDPROFILE)
        if not xldformat:
            raise ValueError('Details for xld profile "%s" not found, cannot split cue' % (xldprofile))
        else:
            if headphones.CONFIG.ENCODERFOLDER:
                splitter = os.path.join(headphones.CONFIG.ENCODERFOLDER, 'xld')
            else:
                splitter = 'xld'
    # use standard xld command to split cue
    elif sys.platform == 'darwin':
        splitter = 'xld'
        if not check_splitter(splitter):
            splitter = 'shntool'

    if splitter == 'shntool' and not check_splitter(splitter):
            raise ValueError('Command not found, ensure shntools with FLAC or xld (OS X) installed')

    # Determine if file can be split (only flac allowed for shntools)
    if 'xld' in splitter and wave.name_ext not in WAVE_FILE_TYPE_BY_EXTENSION.keys() or \
            wave.type not in SHNTOOL_COMPATIBLE:
        raise ValueError('Cannot split, audio file has unsupported extension')

    # generate temporary metafile describing the cue
    if not base_dir.filter('MetaFile'):
        with open(ALBUM_META_FILE_NAME, mode='w') as meta_file:
            meta_file.write(cue.get_meta())
        base_dir.content.append(MetaFile(os.path.abspath(ALBUM_META_FILE_NAME)))
    # check metafile for completeness
    if not base_dir.filter('MetaFile'):
        raise ValueError('Meta file {0} missing!'.format(ALBUM_META_FILE_NAME))
    else:
        global meta
        meta = base_dir.filter('MetaFile')[0]

    # Split with xld
    if 'xld' in splitter:
        cmd = [splitter]
        cmd.extend([wave.name])
        cmd.extend(['-c'])
        cmd.extend([cue.name])
        if xldprofile:
            cmd.extend(['--profile'])
            cmd.extend([xldprofile])
        else:
            cmd.extend(['-f'])
            cmd.extend(['flac'])
        cmd.extend(['-o'])
        cmd.extend([base_dir.path])
        split = split_baby(wave.name, cmd)
    else:
        # Split with shntool
        with open(SPLIT_FILE_NAME, mode='w') as split_file:
            split_file.write(cue.breakpoints())

        cmd = ['shntool']
        cmd.extend(['split'])
        cmd.extend(['-f'])
        cmd.extend([SPLIT_FILE_NAME])
        cmd.extend(['-o'])
        cmd.extend(['flac'])
        cmd.extend([wave.name])
        split = split_baby(wave.name, cmd)
        os.remove(SPLIT_FILE_NAME)
        base_dir.update()

        # tag FLAC files
        if split and meta.count_tracks() == len(base_dir.tracks(ext='.flac', split=True)):
            for t in base_dir.tracks(ext='.flac', split=True):
                logger.info('Tagging {0}...'.format(t.name))
                t.tag()

        # rename FLAC files
        if split and meta.count_tracks() == len(base_dir.tracks(ext='.flac', split=True)):
            for t in base_dir.tracks(ext='.flac', split=True):
                if t.name != t.filename():
                    logger.info('Renaming {0} to {1}...'.format(t.name, t.filename()))
                    os.rename(t.name, t.filename())

    os.remove(ALBUM_META_FILE_NAME)

    if not split:
        raise ValueError('Failed to split, check logs')
    else:
        # Rename original file
        os.rename(wave.name, wave.name + '.original')
        return True


