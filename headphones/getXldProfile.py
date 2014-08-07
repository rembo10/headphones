import os.path
import plistlib
import sys
import xml.parsers.expat as expat
import commands
from headphones import logger

def getXldProfile(xldProfile):
    xldProfileNotFound = xldProfile
    expandedPath = os.path.expanduser(
        '~/Library/Preferences/jp.tmkk.XLD.plist')
    try:
        preferences = plistlib.Plist.fromFile(expandedPath)
    except (expat.ExpatError):
        os.system("/usr/bin/plutil -convert xml1 %s" % expandedPath )
        try:
            preferences = plistlib.Plist.fromFile(expandedPath)
        except (ImportError):
            os.system("/usr/bin/plutil -convert binary1 %s" % expandedPath )
            logger.info(
                'The plist at "%s" has a date in it, and therefore is not useable.' % expandedPath)
            return(xldProfileNotFound, None, None)
    except (ImportError):
        logger.info(
            'The plist at "%s" has a date in it, and therefore is not useable.' % expandedPath)
    except:
        logger.info('Unexpected error:', sys.exc_info()[0])
        return(xldProfileNotFound, None, None)

    xldProfile = xldProfile.lower()
    profiles = preferences.get('Profiles')

    for profile in profiles:

        profilename = profile.get('XLDProfileManager_ProfileName')
        xldProfileForCmd = profilename
        profilename = profilename.lower()
        xldFormat = None
        xldBitrate = None

        if profilename == xldProfile:

            OutputFormatName = profile.get('OutputFormatName')
            ShortDesc = profile.get('ShortDesc')

            # Determine format and bitrate

            if OutputFormatName == 'WAV':
                xldFormat = 'wav'

            elif OutputFormatName == 'AIFF':
                xldFormat = 'aiff'

            elif 'PCM' in OutputFormatName:
                xldFormat = 'pcm'

            elif OutputFormatName == 'Wave64':
                xldFormat = 'w64'

            elif OutputFormatName == 'MPEG-4 AAC':
                xldFormat = 'm4a'
                if 'CBR' in ShortDesc or 'ABR' in ShortDesc or 'CVBR' in ShortDesc:
                    xldBitrate = int(profile.get('XLDAacOutput2_Bitrate'))
                elif 'TVBR' in ShortDesc:
                    XLDAacOutput2_VBRQuality = int(
                        profile.get('XLDAacOutput2_VBRQuality'))
                    if XLDAacOutput2_VBRQuality > 122:
                        xldBitrate = 320
                    elif XLDAacOutput2_VBRQuality > 113 and XLDAacOutput2_VBRQuality <= 122:
                        xldBitrate = 285
                    elif XLDAacOutput2_VBRQuality > 104 and XLDAacOutput2_VBRQuality <= 113:
                        xldBitrate = 255
                    elif XLDAacOutput2_VBRQuality > 95 and XLDAacOutput2_VBRQuality <= 104:
                        xldBitrate = 225
                    elif XLDAacOutput2_VBRQuality > 86 and XLDAacOutput2_VBRQuality <= 95:
                        xldBitrate = 195
                    elif XLDAacOutput2_VBRQuality > 77 and XLDAacOutput2_VBRQuality <= 86:
                        xldBitrate = 165
                    elif XLDAacOutput2_VBRQuality > 68 and XLDAacOutput2_VBRQuality <= 77:
                        xldBitrate = 150
                    elif XLDAacOutput2_VBRQuality > 58 and XLDAacOutput2_VBRQuality <= 68:
                        xldBitrate = 135
                    elif XLDAacOutput2_VBRQuality > 49 and XLDAacOutput2_VBRQuality <= 58:
                        xldBitrate = 115
                    elif XLDAacOutput2_VBRQuality > 40 and XLDAacOutput2_VBRQuality <= 49:
                        xldBitrate = 105
                    elif XLDAacOutput2_VBRQuality > 31 and XLDAacOutput2_VBRQuality <= 40:
                        xldBitrate = 95
                    elif XLDAacOutput2_VBRQuality > 22 and XLDAacOutput2_VBRQuality <= 31:
                        xldBitrate = 80
                    elif XLDAacOutput2_VBRQuality > 13 and XLDAacOutput2_VBRQuality <= 22:
                        xldBitrate = 75
                    elif XLDAacOutput2_VBRQuality > 4 and XLDAacOutput2_VBRQuality <= 13:
                        xldBitrate = 45
                    elif XLDAacOutput2_VBRQuality >= 0 and XLDAacOutput2_VBRQuality <= 4:
                        xldBitrate = 40

            elif OutputFormatName == 'Apple Lossless':
                xldFormat = 'm4a'

            elif OutputFormatName == 'FLAC':
                if 'ogg' in ShortDesc:
                    xldFormat = 'oga'
                else:
                    xldFormat = 'flac'

            elif OutputFormatName == 'MPEG-4 HE-AAC':
                xldFormat = 'm4a'
                xldBitrate = int(profile.get('Bitrate'))

            elif OutputFormatName == 'LAME MP3':
                xldFormat = 'mp3'
                if 'VBR' in ShortDesc:
                    VbrQuality = float(profile.get('VbrQuality'))
                    if VbrQuality < 1:
                        xldBitrate = 260
                    elif VbrQuality >= 1 and VbrQuality < 2:
                        xldBitrate = 250
                    elif VbrQuality >= 2 and VbrQuality < 3:
                        xldBitrate = 210
                    elif VbrQuality >= 3 and VbrQuality < 4:
                        xldBitrate = 195
                    elif VbrQuality >= 4 and VbrQuality < 5:
                        xldBitrate = 185
                    elif VbrQuality >= 5 and VbrQuality < 6:
                        xldBitrate = 150
                    elif VbrQuality >= 6 and VbrQuality < 7:
                        xldBitrate = 130
                    elif VbrQuality >= 7 and VbrQuality < 8:
                        xldBitrate = 120
                    elif VbrQuality >= 8 and VbrQuality < 9:
                        xldBitrate = 105
                    elif VbrQuality >= 9:
                        xldBitrate = 85
                elif 'CBR' in ShortDesc:
                    xldBitrate = int(profile.get('Bitrate'))
                elif 'ABR' in ShortDesc:
                    xldBitrate = int(profile.get('AbrBitrate'))

            elif OutputFormatName == 'Opus':
                xldFormat = 'opus'
                xldBitrate = int(profile.get('XLDOpusOutput_Bitrate'))

            elif OutputFormatName == 'Ogg Vorbis':
                xldFormat = 'ogg'
                XLDVorbisOutput_Quality = float(
                    profile.get('XLDVorbisOutput_Quality'))
                if XLDVorbisOutput_Quality <= -2:
                    xldBitrate = 32
                elif XLDVorbisOutput_Quality > -2 and XLDVorbisOutput_Quality <= -1:
                    xldBitrate = 48
                elif XLDVorbisOutput_Quality > -1 and XLDVorbisOutput_Quality <= 0:
                    xldBitrate = 64
                elif XLDVorbisOutput_Quality > 0 and XLDVorbisOutput_Quality <= 1:
                    xldBitrate = 80
                elif XLDVorbisOutput_Quality > 1 and XLDVorbisOutput_Quality <= 2:
                    xldBitrate = 96
                elif XLDVorbisOutput_Quality > 2 and XLDVorbisOutput_Quality <= 3:
                    xldBitrate = 112
                elif XLDVorbisOutput_Quality > 3 and XLDVorbisOutput_Quality <= 4:
                    xldBitrate = 128
                elif XLDVorbisOutput_Quality > 4 and XLDVorbisOutput_Quality <= 5:
                    xldBitrate = 160
                elif XLDVorbisOutput_Quality > 5 and XLDVorbisOutput_Quality <= 6:
                    xldBitrate = 192
                elif XLDVorbisOutput_Quality > 6 and XLDVorbisOutput_Quality <= 7:
                    xldBitrate = 224
                elif XLDVorbisOutput_Quality > 7 and XLDVorbisOutput_Quality <= 8:
                    xldBitrate = 256
                elif XLDVorbisOutput_Quality > 8 and XLDVorbisOutput_Quality <= 9:
                    xldBitrate = 320
                elif XLDVorbisOutput_Quality > 9:
                    xldBitrate = 400

            elif OutputFormatName == 'WavPack':
                xldFormat = 'wv'
                if ShortDesc != 'normal':
                    xldBitrate = int(profile.get('XLDWavpackOutput_BitRate'))

            # Lossless
            if xldFormat and not xldBitrate:
                xldBitrate = 400

            return(xldProfileForCmd, xldFormat, xldBitrate)

    return(xldProfileNotFound, None, None)
