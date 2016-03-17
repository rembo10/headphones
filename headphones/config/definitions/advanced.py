# =======================================================================================
# Options from "Search Providers" Tab
# =======================================================================================

from .._viewmodel import Block
from .._viewmodel import OptionString, OptionNumber, OptionSwitch, OptionBool, OptionPath, LabelExtension, OptionDropdownSelector, OptionDropdown, OptionCombobox # , OptionPassword

def _(x):
    """ required just for marking translatable strings"""
    return x

def reg(tabname, register_block_cb, register_options_cb):

    # =======================================================================================
    register_block_cb(tabname,
        Block('renaming_options', caption=_("Renaming options"), options=register_options_cb(

            OptionString('FOLDER_FORMAT', 'General', 'Artist/Album [Year]',
                label=_('Folder Format'),
                caption=_(('Use: $Artist/$artist, $SortArtist/$sortartist, $Album/$album, $Year/$year,'
                           ' $Type/$type (release type) and $First/$first (first letter in artist name),'
                           ' $OriginalFolder/$originalfolder (downloaded directory name). Put optional'
                           ' variables in square brackets, use single-quote marks to escape square brackets'
                           ' literally (\'[\', \']\').<br>E.g.: $Type/$First/$artist/$album \'[\'$year\']\''
                           ' = Album/G/girl talk/all day [2010]'
                )),
            ),
            OptionString('FILE_FORMAT', 'General', 'Track Artist - Album [Year] - Title',
                label=_('File Format'),
                caption=_(('Use: $Disc/$disc (disc #), $Track/$track (track #), $Title/$title,'
                           ' $Artist/$artist, $Album/$album and $Year/$year. Put optional variables in'
                           ' square brackets, use single-quote marks to escape square brackets literally'
                           ' (\'[\', \']\').'
                )),
            ),
            OptionBool('FILE_UNDERSCORES', 'General', False,
                label=_('Use underscores instead of spaces'),
            ),
        ))
    )

    # =======================================================================================
    register_block_cb(tabname,
        Block('reencoding_options', caption=_("Re-Encoding Options"), options=register_options_cb(
            LabelExtension(
                label=_(('<i class="fa fa-info-circle"></i> Note: this option requires the lame,'
                         ' ffmpeg or xld encoder'
                )),
                cssclasses=['heading'],
                fullwidth=True,
            ),
            OptionSwitch('MUSIC_ENCODER', 'General', False,
                label=_('Re-encode downloads during postprocessing'),
                options=register_options_cb(
                    OptionBool('ENCODERLOSSLESS', 'General', True,
                        label=_('Only re-encode lossless files (.flac)'),
                    ),
                    OptionBool('DELETE_LOSSLESS_FILES', 'General', True,
                        label=_('Delete original lossless files after encoding'),
                    ),
                ),
            ),

            OptionSwitch('ENCODER_MULTICORE', 'General', False,
                label=_('Enable multi-core'),
                caption=_(''),
                tooltip=_(''),
                options=register_options_cb(
                    OptionNumber('ENCODER_MULTICORE_COUNT', 'General', 0,
                        label=_('Multi-core count'),
                        caption=_('Set equal to the number of cores, or 0 for auto'),
                        minvalue=0,
                        maxvalue=None
                    ),
                ),
            ),

            OptionDropdownSelector('ENCODER', 'General', 'ffmpeg', typeconv=str,
                label=_('Encoder'),
                tooltip=_(('Name of encoder to use. Lame, FFmpeg and libav are available for most Linux'
                           ' distributions. On Ubuntu, libav replaces FFmpeg. xld is OS X-only.'
                )),
                items=(
                    ('lame', _('lame'), register_options_cb(
                    )),
                    ('ffmpeg', _('ffmpeg'), register_options_cb(
                    )),
                    ('libav', _('libav'), register_options_cb(
                    )),
                    ('xld', _('xld'), register_options_cb(
                    )),
                )
            )
        ))
    )

    # TODO : move this block
    register_block_cb(tabname,
        Block('audio_sub_block', caption=_("Audio Properties"), options=register_options_cb(
            # FIX : I want add CUSTOM values here!!!!
            OptionCombobox('ENCODEROUTPUTFORMAT', 'General', 'mp3', #typeconv=str,
                label=_('Format'),
                caption=_('Use one of "mp3", "ogg", "m4a", or <strong>any custom</strong> format'),
                items=(
                    'mp3',
                    'ogg',
                    'm4a',
                )
            ),
            OptionDropdownSelector('ENCODERVBRCBR', 'General', 'cbr', typeconv=str,
                label=_('VBR/CBR'),
                items=(
                    ('cbr', _('cbr'), register_options_cb(
                        OptionDropdown('BITRATE', 'General', 192, typeconv=int,
                            label=_('Bitrate'),
                            items=(
                                (64, _('64')),
                                (128, _('128')),
                                (192, _('192')),
                                (256, _('256')),
                                (320, _('320')),
                            )
                        ),
                    )),
                    ('vbr', _('vbr'), register_options_cb(
                        OptionDropdown('ENCODERQUALITY', 'General', 2, typeconv=int,
                            label=_('Quality'),
                            items=(
                                (0, _('0')),
                                (1, _('1')),
                                (2, _('2')),
                                (3, _('3')),
                                (4, _('4')),
                                (5, _('5')),
                                (6, _('6')),
                                (7, _('7')),
                                (8, _('8')),
                                (9, _('9')),
                            )
                        ),
                    )),
                )
            ),
            OptionDropdown('SAMPLINGFREQUENCY', 'General', 44100, typeconv=int,
                label=_('Sampling'),
                items=(
                    (44100, _('44.1 kHz')),
                    (48000, _('48.0 kHz')),
                )
            ),

            # TODO : use special separator!!!!!!
            LabelExtension(
                label='<hr />',
                fullwidth=True,
            ),

            OptionString('ADVANCEDENCODER', 'General', '',
                label=_('Arguments'),
                caption=_('Ignores all of the above options'),
                tooltip=_('Advanced Encoding Options'),
            ),
        ))
    )
    # TODO : move this block too [ XLD ]
    register_block_cb(tabname,
        Block('audio_sub_block_2', caption=_("Audio Properties XLD"), options=register_options_cb(
            OptionString('XLDPROFILE', 'General', '',
                label=_('XLD Profile'),
            )
        ))
    )

    # =======================================================================================
    # REAL Advanced block
    register_block_cb(tabname,
        Block('advanced_encoding_options', caption=_("Advanced Encoding Options"), options=register_options_cb(
            OptionPath('ENCODER_PATH', 'General', '',
                label=_('Path to Encoder'),
            ),
        ))
    )

    # =======================================================================================
    register_block_cb(tabname,
        Block('git', caption=_("GitHub"), options=register_options_cb(
            OptionSwitch('CHECK_GITHUB', 'General', True,
                label=_('GitHub Updater Enabled'),
                tooltip=_('Enable autoupdates for Headphones through GitHub '),

                options=register_options_cb(
                    OptionString('GIT_USER', 'General', 'rembo10',
                        label=_('GitHub Username'),
                        tooltip=_('Username, used to check updates on GitHub.com'),
                        maxlength=64,
                    ),
                    OptionNumber('CHECK_GITHUB_INTERVAL', 'General', 360,
                        label=_('Check interval'),
                        caption=_('in minutes'),
                        tooltip=_('Interval between checks for updates'),
                        minvalue=0,
                        maxvalue=9999
                    ),
                    OptionBool('CHECK_GITHUB_ON_STARTUP', 'General', True,
                        label=_('Check on startup'),
                        tooltip=_('Perform check for updates on startup'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    register_block_cb(tabname,
        Block('directories', caption=_("Directories"), options=register_options_cb(
            OptionPath('LOG_DIR', 'General', '',
                label=_('Log Directory'),
                maxlength=64,
            ),
            OptionPath('CACHE_DIR', 'General', '',
                label=_('Cache Directory'),
                maxlength=64,
            ),
            OptionNumber('CACHE_SIZEMB', 'Advanced', 32,
                label=_('Cache Size'),
                caption=_('in MB'),
                minvalue=0
            ),

            # TODO : MOVE TO POST PROCESSING BLOCK OF POST PROCESSING TAB
            OptionSwitch('FILE_PERMISSIONS_ENABLED', 'General', True,
                label=_('File Permissions Enabled'),
                tooltip=_('Change file permissions during post-processing'),

                options=register_options_cb(
                    # TODO: Convert to OptionFilePermission
                    OptionString('FILE_PERMISSIONS', 'General', '0644',
                        label=_('File Permissions'),
                        tooltip=_('Desired file permissions'),
                        maxlength=4
                    ),
                )
            ),
            OptionSwitch('FOLDER_PERMISSIONS_ENABLED', 'General', True,
                label=_('Folder Permissions Enabled'),
                tooltip=_('Change folder permissions during post-processing'),

                options=register_options_cb(
                    # TODO: Convert to OptionFilePermission
                    OptionString('FOLDER_PERMISSIONS', 'General', '0755',
                        label=_('Folder Permissions'),
                        tooltip=_('Desired folder permissions'),
                        maxlength=4
                    ),
                )
            ),
        )
    ))
    # =======================================================================================
