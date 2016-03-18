# =======================================================================================
# Options from "Search Providers" Tab
# =======================================================================================

from .._viewmodel import Block

from .._viewmodel import OptionString, OptionNumber, OptionSwitch, OptionBool, OptionPath, OptionPassword
from .._viewmodel import OptionDropdownSelector, OptionDropdown, OptionCombobox, OptionCheckboxListExtrasCrutch # OptionCheckboxList
from .._viewmodel import TemplaterExtension, LabelExtension
from ..loc import _

def reg(tabname, register_block_cb, register_options_cb):

    # =======================================================================================
    register_block_cb(tabname,
        Block('renaming_options', caption=_("Renaming options"), options=register_options_cb(

            OptionString('FOLDER_FORMAT', 'General', 'Artist/Album [Year]',
                label=_('Folder Format'),
                caption=_('Use: $Artist/$artist, $SortArtist/$sortartist, $Album/$album, $Year/$year,'
                           ' $Type/$type (release type) and $First/$first (first letter in artist name),'
                           ' $OriginalFolder/$originalfolder (downloaded directory name). Put optional'
                           ' variables in square brackets, use single-quote marks to escape square brackets'
                           ' literally (\'[\', \']\').<br>E.g.: $Type/$First/$artist/$album \'[\'$year\']\''
                           ' = Album/G/girl talk/all day [2010]'
                ),
            ),
            OptionString('FILE_FORMAT', 'General', 'Track Artist - Album [Year] - Title',
                label=_('File Format'),
                caption=_('Use: $Disc/$disc (disc #), $Track/$track (track #), $Title/$title,'
                           ' $Artist/$artist, $Album/$album and $Year/$year. Put optional variables in'
                           ' square brackets, use single-quote marks to escape square brackets literally'
                           ' (\'[\', \']\').'
                ),
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
                label=_('<i class="fa fa-info-circle"></i> Note: this option requires the lame,'
                         ' ffmpeg or xld encoder'
                ),
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

            OptionDropdownSelector('ENCODER', 'General', 'ffmpeg', initype=str,
                label=_('Encoder'),
                tooltip=_('Name of encoder to use. Lame, FFmpeg and libav are available for most Linux'
                           ' distributions. On Ubuntu, libav replaces FFmpeg. xld is OS X-only.'
                ),
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
        Block('audio_sub_block', caption=_("Audio Properties [LAME FFMPEG LIBAV]"), options=register_options_cb(
            # FIX : I want add CUSTOM values here!!!!
            OptionCombobox('ENCODEROUTPUTFORMAT', 'General', 'mp3', #initype=str,
                label=_('Format'),
                caption=_('Use one of "mp3", "ogg", "m4a", or <strong>any custom</strong> format'),
                items=(
                    'mp3',
                    'ogg',
                    'm4a',
                )
            ),
            OptionDropdownSelector('ENCODERVBRCBR', 'General', 'cbr', initype=str,
                label=_('VBR/CBR'),
                items=(
                    ('cbr', _('cbr'), register_options_cb(
                        OptionDropdown('BITRATE', 'General', 192, initype=int,
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
                        OptionDropdown('ENCODERQUALITY', 'General', 2, initype=int,
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
            OptionDropdown('SAMPLINGFREQUENCY', 'General', 44100, initype=int,
                label=_('Sampling'),
                items=(
                    (44100, _('44.1 kHz')),
                    (48000, _('48.0 kHz')),
                )
            ),

            TemplaterExtension(template_name='DividerExtension'),

            OptionString('ADVANCEDENCODER', 'General', '',
                label=_('Arguments'),
                caption=_('<i class="fa fa-exclamation-circle"></i> Ignores all of the above options'),
                tooltip=_('Advanced Encoding Options'),
            ),
        ))
    )
    # TODO : move this block too [ XLD ]
    register_block_cb(tabname,
        Block('audio_sub_block_2', caption=_("Audio Properties [XLD]"), options=register_options_cb(
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
    # Miscellaneous
    register_block_cb(tabname,
        Block('miscellaneous', caption=_("Miscellaneous"), options=register_options_cb(
            OptionSwitch('INCLUDE_EXTRAS', 'General', False,
                label=_('Automatically include extras when adding an artist'),
                tooltip=_('Choose Which Extras to Include'),
                alignleft=True,
                options=register_options_cb(

                    # TODO : somebody, please, convert the value of this option to list of int
                    #        currently it is a string...
                    OptionCheckboxListExtrasCrutch('EXTRAS', 'General', '',
                        alignleft=True,
                        items=(
                            ("1", _("single")),
                            ("2", _("ep")),
                            ("3", _("compilation")),
                            ("4", _("soundtrack")),
                            ("5", _("live")),
                            ("6", _("remix")),
                            ("7", _("spokenword")),
                            ("8", _("audiobook")),
                            ("9", _("other")),
                            ("10", _("dj-mix")),
                            ("11", _("mixtape/street")),
                            ("12", _("broadcast")),
                            ("13", _("interview")),
                            ("14", _("demo")),
                        )
                    ),
                )
            ),
            OptionBool('OFFICIAL_RELEASES_ONLY', 'General', False,
                alignleft=True,
                label=_('Only include \'official\' extras (i.e. no bootlegs, promos, etc.)'),
            ),
            OptionBool('AUTOWANT_UPCOMING', 'General', True,
                alignleft=True,
                label=_('Automatically mark upcoming albums as wanted'),
            ),
            OptionBool('AUTOWANT_ALL', 'General', False,
                alignleft=True,
                label=_('Automatically mark all albums as wanted'),
            ),
            OptionBool('AUTOWANT_MANUALLY_ADDED', 'General', True,
                alignleft=True,
                label=_('Automatically mark manually added albums as wanted'),
                tooltip=_('Automatically mark manually added albums from search results as wanted'),
            ),
            OptionBool('WAIT_UNTIL_RELEASE_DATE', 'General', False,
                alignleft=True,
                label=_('Wait until an album\'s release date before searching'),
                tooltip=_('Wait until an album\'s release date before searching'),
            ),
            OptionBool('FREEZE_DB', 'General', False,
                alignleft=True,
                label=_('Don\'t add new artists when post-processing albums'),
                tooltip=_('Freeze the database, so new artists won\'t be added automatically. Use'
                           ' this if Headphones adds artists because due to wrong snatches. This check'
                           ' is skipped when the folder name is appended with release group ID.'
                ),
            ),
            OptionBool('DO_NOT_PROCESS_UNMATCHED', 'General', False,
                alignleft=True,
                label=_('Stop post-processing if no good metadata match found'),
                tooltip=_('Stop post-processing if no good metadata match found'),
            ),
            OptionBool('IDTAG', 'Beets', False,
                alignleft=True,
                label=_('Tag using ID3v2.3 instead of ID3v2.4'),
                tooltip=_('Tag using ID3v2.3 instead of ID3v2.4'),
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
    # SongKick
    register_block_cb(tabname,
        Block('songkick', caption=_("Songkick"), options=register_options_cb(
            OptionSwitch('SONGKICK_ENABLED', 'Songkick', True,
                label=_('Show concert info'),
                options=register_options_cb(
                    OptionString('SONGKICK_APIKEY', 'Songkick', 'nd1We7dFW2RqxPw8',
                        label=_('API Key'),
                        maxlength=128
                    ),
                    OptionSwitch('SONGKICK_FILTER_ENABLED', 'Songkick', False,
                        label=_('Filter by Metro Area'),
                        options=register_options_cb(
                            OptionString('SONGKICK_LOCATION', 'Songkick', '',
                                label=_('Metro Area ID'),
                                tooltip=_('Enter the Metro Area ID, e.g. the ID for London is 24426,'
                                           ' this can be found by clicking the link and searching/selecting'
                                           ' the city, e.g. London should find'
                                           ' http://www.songkick.com/metro_areas/24426-uk-london'
                                ),
                            ),
                            TemplaterExtension(template_name='SongkickAreaIdExtension', strings={'caption': _('Find Area ID')}),
                        )
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    # Musicbrainz
    register_block_cb(tabname,
        Block('musicbrainz', caption=_("Musicbrainz"), options=register_options_cb(
            OptionDropdownSelector('MIRROR', 'General', 'musicbrainz.org', initype=str,
                label=_('Muscbrainz Mirror'),
                items=(
                    OptionDropdownSelector.Item(value='musicbrainz.org', label=_('musicbrainz.org')),
                    OptionDropdownSelector.Item(value='custom', label=_('custom'), options=register_options_cb(
                        OptionString('CUSTOMHOST', 'General', 'localhost',
                            label=_('Host'),
                            maxlength=128
                        ),
                        OptionNumber('CUSTOMPORT', 'General', 5000,
                            label=_('Port'),
                            minvalue=0,
                            maxvalue=999999
                        ),
                        OptionSwitch('CUSTOMAUTH', 'General', False,
                            label=_('Requires Authentication'),
                            options=register_options_cb(
                                OptionString('CUSTOMUSER', 'General', '',
                                    label=_('Username'),
                                    maxlength=128
                                ),
                                OptionPassword('CUSTOMPASS', 'General', '',
                                    label=_('Password'),
                                    maxlength=64
                                ),
                            )
                        ),
                        OptionNumber('CUSTOMSLEEP', 'General', 1,
                            label=_('Sleep Interval'),
                            caption=_('in minutes'),
                            minvalue=0,
                            maxvalue=999999
                        ),
                    )),
                    OptionDropdownSelector.Item(value='headphones', label=_('headphones'), options=register_options_cb(
                        OptionString('HPUSER', 'General', '',
                            label=_('Username'),
                            cssclasses=['hpuser'],
                            maxlength=128
                        ),
                        OptionString('HPPASS', 'General', '',
                            label=_('Password'),
                            cssclasses=['hppass'],
                            maxlength=128
                        ),
                        TemplaterExtension(template_name='CodeshyRegExtension', strings={'caption': _('Don\'t have an account? Sign up!')}),
                    )),
                )
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
