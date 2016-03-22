from .._viewmodel import BlockExtension
from .._viewmodel import OptionString, OptionNumber, OptionSwitch, OptionBool, OptionPath, MessageExtension, OptionDropdownSelector, OptionPercent
from ..loc import _

"""
Options from "Quality and Post Processing" Tab
"""


def reg(_extend_cb):
    opts = []
    # =======================================================================================
    opts.extend([
       BlockExtension('quality', caption=_("Quality"), options=_extend_cb(

            OptionDropdownSelector('PREFERRED_QUALITY', 'General', 0, initype=int,
                label=_('Preferred quality'),
                tooltip=_('Preferred quality'),
                items=(
                    (0, _('Highest Quality excluding Lossless')),    # TODO: title = Snatch the highest quality available, excluding lossless.
                    (1, _('Highest Quality including Lossless')),    # TODO: title = Snatch the highest quality available, including lossless.
                    (3, _('Lossless Only'),     # TODO: title = Snatch only lossless quality.
                        _extend_cb(
                            MessageExtension(
                                cssclasses=None,
                                fullwidth=True,
                                message=_('Reject if target size is not in bitrate range:')
                            ),
                            OptionNumber('LOSSLESS_BITRATE_FROM', 'General', 0,
                                label=_('From'),
                                caption=_('in kbps'),
                                tooltip=_('e.g. if album length = 40 mins, from = 350 kbps, then min'
                                           ' target size = 102.5 mb, anything less will be rejected'
                                ),
                                minvalue=0,
                                maxvalue=999999
                            ),
                            OptionNumber('LOSSLESS_BITRATE_TO', 'General', 0,
                                label=_('To'),
                                caption=_('in kbps'),
                                tooltip=_('e.g. if album length = 40 mins, to = 2000 kbps, then max'
                                           ' target size = 586 mb, anything greater will be rejected'
                                ),
                                minvalue=0,
                                maxvalue=999999
                            ),

                        )
                    ),
                    (2, _('Custom Bitrate'),    # TODO: title = Prefer certain bitrate range, including lossless fallback. Use this option if you have a lot of wrong snatches.
                        _extend_cb(
                            OptionNumber('PREFERRED_BITRATE', 'General', 0,
                                label=_('Target bitrate'),
                                caption=_('in kbps'),
                                minvalue=0,
                                maxvalue=9999999
                            ),
                            OptionPercent('PREFERRED_BITRATE_LOW_BUFFER', 'General', 0,
                                label=_('Reject if <strong>less than</strong>'),
                                caption=_('(leave blank for no limit)'),
                                minvalue=0,
                                maxvalue=100
                            ),
                            OptionPercent('PREFERRED_BITRATE_HIGH_BUFFER', 'General', 0,
                                label=_('or <strong>more than</strong>'),
                                caption=_('(leave blank for no limit)'),
                                minvalue=0,
                                maxvalue=100
                            ),
                            MessageExtension(
                                message=_('of the target size '),
                                fullwidth=False,
                            ),
                            OptionBool('PREFERRED_BITRATE_ALLOW_LOSSLESS', 'General', False,
                                alignleft=True,
                                label=_('Allow lossless if no good lossy match found'),
                            ),
                            OptionBool('DETECT_BITRATE', 'General', False,
                                alignleft=True,
                                label=_('Auto-Detect Preferred Bitrate'),
                            ),
                        )
                    ),
                )
            ),
       ))
    ])

    # =======================================================================================
    opts.extend([
       BlockExtension('search_words', caption=_("Search Words"), options=_extend_cb(
            MessageExtension(
                cssclasses=None, # ['small'],
                fullwidth=True,
                message=_('Separate words with a comma, e.g. "word1,word2,word3".')
            ),
            OptionString('IGNORED_WORDS', 'General', '',
                label=_('Ignored Words'),
                caption=_('Results with any of these words in the title will be filtered out'),
            ),
            OptionString('PREFERRED_WORDS', 'General', '',
                label=_('Preferred Words'),
                caption=_('Results with these words in the title will be preferred over results'
                           ' without them (search provider names can also be entered)'
                ),
            ),
            OptionString('REQUIRED_WORDS', 'General', '',
                label=_('Required Words'),
                caption=_('Results without these words in the title will be filtered out. You can'
                           ' use OR: "flac OR lossless OR alac, vinyl"'
                ),
            ),
            OptionBool('IGNORE_CLEAN_RELEASES', 'General', False,
                alignleft=True,
                label=_('Ignore clean/censored releases'),
                tooltip=_('Filter out releases that contain the words \'clean\',\'edited\' or'
                           ' \'censored\', as long as those words aren\'t in the search term'
                ),
            ),
        ))
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('post_processing', caption=_("Post-Processing"), options=_extend_cb(
            OptionBool('RENAME_FILES', 'General', False,
                label=_('Rename files'),
                alignleft=True,
            ),
            OptionBool('CORRECT_METADATA', 'General', False,
                label=_('Correct metadata'),
                alignleft=True,
            ),
            OptionBool('CUE_SPLIT', 'General', True,
                label=_('Split single file albums into multiple tracks'),
                alignleft=True,
                tooltip=_('Use associated .cue sheet to split single file albums into multiple tracks.'
                           ' Requires shntool with flac or xld cli (OS X) to be installed.'
                ),
            ),
            OptionBool('CLEANUP_FILES', 'General', False,
                label=_('Delete leftover files'),
                alignleft=True,
                caption=_('(.m3u, .nfo, .sfv, .nzb, etc.)'),
            ),
            OptionBool('KEEP_NFO', 'General', False,
                label=_('Keep original nfo'),
                alignleft=True,
                caption=_('(extension changed to .orig.nfo)'),
            ),
            OptionSwitch('ADD_ALBUM_ART', 'General', False,
                label=_('Add album art jpeg to album folder'),
                alignleft=True,
                options=_extend_cb(
                    OptionString('ALBUM_ART_FORMAT', 'General', 'folder',
                        label=_('Name of album art file'),
                        caption=_('will be suffixed with ".jpg"'),
                    ),
                    MessageExtension(
                        cssclasses=['small'],
                        fullwidth=True,
                        message=_('Use $Artist/$artist, $Album/$album, $Year/$year, put optional variables'
                                 ' in square brackets, use single-quote marks to escape square brackets'
                                 ' literally (\'[\', \']\').'
                        )
                    ),
                )
            ),
            OptionBool('EMBED_ALBUM_ART', 'General', False,
                label=_('Embed album art in each file'),
                alignleft=True,
            ),
            OptionBool('EMBED_LYRICS', 'General', False,
                label=_('Embed lyrics'),
                alignleft=True,
            ),
            OptionBool('RENAME_UNPROCESSED', 'General', True,
                label=_('Rename unprocesed'),
                alignleft=True,
            ),
            OptionSwitch('MOVE_FILES', 'General', False,
                label=_('Move downloads to Destination Folder'),
                alignleft=True,
                options=_extend_cb(
                    OptionBool('REPLACE_EXISTING_FOLDERS', 'General', False,
                        alignleft=True,
                        label=_('Replace existing folders?'),
                    ),
                    OptionBool('KEEP_ORIGINAL_FOLDER', 'General', False,
                        alignleft=True,
                        label=_('Keep original folder (i.e. copy)'),
                    ),
                    OptionPath('DESTINATION_DIR', 'General', '',
                        label=_('Destination Directory'),
                        caption=_('The directory where Headphones will move file to after post processing, e.g.'
                                   ' /Volumes/share/music.'
                        ),
                    ),
                    OptionPath('LOSSLESS_DESTINATION_DIR', 'General', '',
                        label=_('Lossless Destination Directory'),
                        caption=_('Optional. Set this if you have a separate directory for lossless music.'),
                    ),
                )
            ),
        ))
    ])

    return opts
