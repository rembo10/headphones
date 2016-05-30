# =======================================================================================
# Options from "Search Providers" Tab
# =======================================================================================

from .._viewmodel import BlockExtension
from .._viewmodel import OptionString, OptionNumber, OptionSwitch, OptionBool, OptionPath, OptionPassword, OptionPercent, OptionInternal
from .._viewmodel import OptionDropdownSelector, OptionDropdown, OptionCombobox, OptionCheckboxListExtrasCrutch  # OptionCheckboxList
from .._viewmodel import TemplaterExtension, MessageExtension

from ..typeconv import boolext

from ..loc import _


def reg(_extend_cb):

    opts = []

    # =======================================================================================
    opts.extend([
        BlockExtension('renaming_options', caption=_("Renaming options"), options=_extend_cb(

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
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('reencoding_options', caption=_("Re-Encoding Options"), options=_extend_cb(
            MessageExtension(
                message=_('Note: this option requires the lame,'
                          ' ffmpeg or xld encoder'
                          ),
                icon='<i class="fa fa-info-circle"></i>',
                fullwidth=True,
            ),
            OptionSwitch('MUSIC_ENCODER', 'General', False,
                         label=_('Re-encode downloads during postprocessing'),
                         options=_extend_cb(
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
                         options=_extend_cb(
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
                                       OptionDropdownSelector.Item('lame', _('lame'), csssuffix='encoder-lame-ffmpeg-libav-embed'),
                                       OptionDropdownSelector.Item('libav', _('libav'), csssuffix='encoder-lame-ffmpeg-libav-embed'),
                                       OptionDropdownSelector.Item('ffmpeg', _('ffmpeg'), csssuffix='encoder-lame-ffmpeg-libav-embed', options=_extend_cb(
                                           # DONE : I want add CUSTOM values here!!!!
                                           OptionCombobox('ENCODEROUTPUTFORMAT', 'General', 'mp3',  # initype=str,
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
                                                                      ('cbr', _('cbr'), _extend_cb(
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
                                                                      ('vbr', _('vbr'), _extend_cb(
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
                                       )),

                                       OptionDropdownSelector.Item('xld', _('xld'), _extend_cb(
                                           OptionString('XLDPROFILE', 'General', '',
                                                        label=_('XLD Profile'),
                                                        )
                                       )),
                                   )
                                   )
        ))
    ])

    # =======================================================================================
    # REAL Advanced block
    opts.extend([
        BlockExtension('advanced_encoding_options', caption=_("Advanced Encoding Options"), options=_extend_cb(
            OptionPath('ENCODER_PATH', 'General', '',
                       label=_('Path to Encoder'),
                       ),
        ))
    ])

    # =======================================================================================
    # Miscellaneous
    opts.extend([
        BlockExtension('miscellaneous', caption=_("Miscellaneous"), options=_extend_cb(
            OptionSwitch('INCLUDE_EXTRAS', 'General', False,
                         label=_('Automatically include extras when adding an artist'),
                         tooltip=_('Choose Which Extras to Include'),
                         alignleft=True,
                         options=_extend_cb(

                             # TODO : somebody, please, convert the value of this option to list of int
                             #        currently it is a string, not a list - JUST COMMA SEPARATED STRING...
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
            OptionInternal('RENAME_FROZEN', 'General', True, initype=boolext),
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
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('directories', caption=_("Directories"), options=_extend_cb(
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

                         options=_extend_cb(
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

                         options=_extend_cb(
                             # TODO: Convert to OptionFilePermission
                             OptionString('FOLDER_PERMISSIONS', 'General', '0755',
                                          label=_('Folder Permissions'),
                                          tooltip=_('Desired folder permissions'),
                                          maxlength=4
                                          ),
                         )
                         ),
        ))
    ])

    # =======================================================================================
    # SongKick
    opts.extend([
        BlockExtension('songkick', caption=_("Songkick"), options=_extend_cb(
            OptionSwitch('SONGKICK_ENABLED', 'Songkick', True,
                         label=_('Show concert info'),
                         options=_extend_cb(
                             OptionString('SONGKICK_APIKEY', 'Songkick', 'nd1We7dFW2RqxPw8',
                                          label=_('API Key'),
                                          maxlength=128
                                          ),
                             OptionSwitch('SONGKICK_FILTER_ENABLED', 'Songkick', False,
                                          label=_('Filter by Metro Area'),
                                          options=_extend_cb(
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
    ])

    # =======================================================================================
    # Musicbrainz
    opts.extend([
        BlockExtension('musicbrainz', caption=_("Musicbrainz"), options=_extend_cb(
            OptionDropdownSelector('MIRROR', 'General', 'musicbrainz.org', initype=str,
                                   label=_('Musicbrainz Mirror'),
                                   items=(
                                       OptionDropdownSelector.Item(value='musicbrainz.org', label=_('musicbrainz.org')),
                                       OptionDropdownSelector.Item(value='custom', label=_('custom'), options=_extend_cb(
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
                                                        options=_extend_cb(
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

                                       # THIS options already registered on "search tab"
                                       # so we will not call extend_cb
                                       # !!!!!
                                       OptionDropdownSelector.Item(value='headphones', label=_('headphones'), options=_extend_cb(
                                           MessageExtension(message=_('You could set settings of the this mirror on the block'
                                                                      ' <code>Settings > Search Providers > Headphones Indexer</code>'
                                                                      ),
                                                            icon='<i class="fa fa-comments-o"></i>',
                                                            ),
                                           # OptionString('HPUSER', 'General', '',
                                           #     label=_('Username'),
                                           #     cssclasses=['-hp-hp-user'],
                                           #     maxlength=128
                                           # ),
                                           # OptionPassword('HPPASS', 'General', '',
                                           #     label=_('Password'),
                                           #     cssclasses=['-hp-hp-pass'],
                                           #     maxlength=128
                                           # ),
                                           # TemplaterExtension(template_name='CodeshyRegExtension', strings={'caption': _('Don\'t have an account? Sign up!')}),
                                       )),
                                   )
                                   ),
        ))
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('advanced_ssl', caption=_("SSL"), options=_extend_cb(
            OptionBool('VERIFY_SSL_CERT', 'Advanced', True,
                       label=_('Enable verification of SSL certificates'),
                       caption=_('Note: disabling could pose a <strong>security issue!</strong>. Could be truly disabled only with'
                                 ' python &gt; 2.7.9'
                                 ),
                       tooltip=_('This patch for systems with broken SSL (like QNAP)'),
                       ),
        ))
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('git', caption=_("GitHub"), options=_extend_cb(
            OptionSwitch('CHECK_GITHUB', 'General', True,
                         label=_('GitHub Updater Enabled'),
                         tooltip=_('Enable autoupdates for Headphones through GitHub '),

                         options=_extend_cb(
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
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('advanced_http_paths', caption=_("Advanced HTTP"), options=_extend_cb(
            OptionSwitch('HTTP_PROXY', 'General', False,
                         label=_('Behind proxy'),
                         caption=_('Headphones works behind proxy, HP will modify url appropriately'),
                         options=_extend_cb(
                             OptionDropdown('HTTP_PROXY_HEADER_HOST', 'General', '', initype=str,
                                label=_('HTTP header with external hostname'),
                                tooltip=_('The name of HTTP header, which will be used by'
                                          ' CherryPy.tool.proxy.local to determine the external proxy name'),
                                caption=_('For example, Apache uses "X-Forwarded-Host"'),
                                items=(
                                    ('', _('Default behaviour')),
                                    ('X-Forwarded-Host', _('Apache [X-Forwarded-Host]')),
                                    ('X-Host', _('Lighttpd [X-Host]')),
                                    ('Host', _('Nginx [Host]')),
                                )
                             ),
                         ),
            ),
            OptionString('HTTP_ROOT', 'General', '/',
                         label=_('HTTP root'),
                         caption=_('The base part of the URL, without hostname. Just path to home-page of HP.'),
                         ),
        )),
    ])

    opts.extend([
        BlockExtension('advanced_forgotten', caption=_("Strange hidden options"), options=_extend_cb(
            MessageExtension(
                message=_('This is a block of forgotten settings. Previously, they did not have any'
                          ' visible representation in UI, but they are used by app\'s modules. <strong>'
                          'Help them to find an appropriate place on the settings page</strong>'
                          ),
                icon='<i class="fa fa-question-circle"></i>',
                fullwidth=True,
            ),

            OptionPercent('ALBUM_COMPLETION_PCT', 'Advanced', 80,
                          label=_('Album completion'),
                          caption=_('This is used to see how many tracks you have from an album - to mark it as downloaded. Default is 80%'),
                          minvalue=0,
                          maxvalue=150
                          ),
        ))
    ])

    # =======================================================================================

    return opts
