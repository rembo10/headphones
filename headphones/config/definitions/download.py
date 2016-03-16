# =======================================================================================
# Options from "Web Interface" Tab
# =======================================================================================

from .._viewmodel import Tab, Tabs, Block
from .._viewmodel import OptionBase, OptionString, OptionNumber, OptionSwitch, OptionPassword, OptionBool, OptionPath, OptionList, OptionDropdown, OptionUrl, OptionDropdownSelector
from .._viewmodel import TemplaterExtension

def _(x):
    """ required just for marking translatable strings"""
    return x


def reg(tabname, register_block_cb, register_options_cb):

    # =======================================================================================
    # USENET SETTINGS
    # =======================================================================================
    register_block_cb(tabname,
        Block('usenet_selector', caption=_("Prefered Usenet"), options=register_options_cb(
            OptionDropdownSelector('NZB_DOWNLOADER', 'General', 0, typeconv=int,
                label=_('Usenet downloader'),
                tooltip=_('Method for downloading usenet files.'),
                items=(
                    (0, _('Sabnzbd'),
                        register_options_cb(
                            OptionUrl('SAB_HOST', 'SABnzbd', '',
                                label=_('SABnzbd Host'),
                                caption=_('usually http://localhost:8080'),
                                tooltip=_('SABnzbd host and port.'),
                                maxlength=128
                            ),
                            OptionString('SAB_USERNAME', 'SABnzbd', '',
                                label=_('SABnzbd Username'),
                                tooltip=_('SABnzbd username. Leave empty if not applicable.'),
                                maxlength=128
                            ),
                            OptionPassword('SAB_PASSWORD', 'SABnzbd', '',
                                label=_('SABnzbd Password'),
                                tooltip=_('SABnzbd password. Leave empty if not applicable.'),
                                maxlength=128
                            ),
                            OptionString('SAB_APIKEY', 'SABnzbd', '',
                                label=_('SABnzbd API key'),
                                tooltip=_('SABnzbd API key. Can be found in SABnzbd settings.'),
                                maxlength=36
                            ),
                            OptionString('SAB_CATEGORY', 'SABnzbd', '',
                                label=_('SABnzbd Category'),
                                tooltip=_('Name of SABnzbd category to add downloads to.'),
                                maxlength=128
                            ),
                        )
                    ),
                    (1, _('NZBget'),
                        register_options_cb(
                            OptionUrl('NZBGET_HOST', 'NZBget', '',
                                label=_('NZBget Host'),
                                caption=_('usually http://localhost:6789'),
                                tooltip=_('NZBget host and port.'),
                                maxlength=128
                            ),
                            OptionString('NZBGET_USERNAME', 'NZBget', 'nzbget',
                                label=_('NZBget Username'),
                                tooltip=_('NZBGet username. Leave empty if not applicable'),
                                maxlength=20
                            ),
                            OptionPassword('NZBGET_PASSWORD', 'NZBget', '',
                                label=_('NZBget Password'),
                                tooltip=_('NZBGet password. Leave empty if not applicable'),
                                maxlength=20
                            ),
                            OptionString('NZBGET_CATEGORY', 'NZBget', '',
                                label=_('NZBget Category'),
                                tooltip=_('Name of NZBget category to add downloads to.'),
                                maxlength=20
                            ),
                            OptionDropdown('NZBGET_PRIORITY', 'NZBget', 0, typeconv=int,
                                label=_('NZBget Priority'),
                                tooltip=_('NZBget Priority'),
                                items=(
                                    (-100, _('Very low')),
                                    ( -50, _('Low')),
                                    (   0, _('Normal')),
                                    (  50, _('High')),
                                    ( 100, _('Very high')),
                                    ( 900, _('Force')),
                                )
                            ),
                        )
                    ),
                    (2, _('Black Hole'),
                        register_options_cb(
                            OptionPath('BLACKHOLE_DIR', 'General', '',
                                label=_('Black Hole Directory'),
                                caption=_('Folder your Download program watches for NZBs'),
                                tooltip=_('Path to folder to put NZB files in, for downloading.'),
                            ),
                        )
                    ),
                )
            ),
        ))
    )

    # =======================================================================================

    register_block_cb(tabname,
        Block('usenet_common', caption=_("Usenet Common Settings"), options=register_options_cb(
            OptionPath('DOWNLOAD_DIR', 'General', '',
                label=_('Music Download Directory'),
                caption=_('Full path where SAB or NZBget downloads your music, e.g. <code>/Users/name/Downloads/music</code>'),
                tooltip=_('Path to folder where Headphones can find the downloads.'),
                #maxlength=50
            ),
            OptionNumber('USENET_RETENTION', 'General', 1500,
                label=_('Usenet Retention'),
                tooltip=_('Number of days of retention your usenet provider provides.'),
                minvalue=0,
                maxvalue=99999
            ),
        ))
    )

    # =======================================================================================
    # TORRENTS SETTINGS
    # =======================================================================================
    register_block_cb(tabname,
        Block('torrent_selector', caption=_("Torrents Selector"), options=register_options_cb(
            OptionDropdown('TORRENT_DOWNLOADER', 'General', 0, typeconv=int,
                label=_('Torrent downloader'),
                tooltip=_('Preferred torrent downloader'),
                items=(
                    (0, _('Black Hole')),
                    (1, _('Transmission')),
                    (2, _('uTorrent (Beta)')),
                    (3, _('Deluge (Beta)')),
                )
            ),
        ))
    )



    # =======================================================================================
    register_block_cb(tabname,
        Block('torrent_common', caption=_("Torrent Common Settings"), options=register_options_cb(
            OptionNumber('NUMBEROFSEEDERS', 'General', 10,
                label=_('Minimum seeders'),
                caption=_('Number of minimum seeders a torrent must have to be accepted'),
                tooltip=_('Minimum seeders'),
                minvalue=0,
                maxvalue=99999
            ),
            OptionPath('DOWNLOAD_TORRENT_DIR', 'General', '',
                label=_('Music Download Directory'),
                caption=_('Full path where your torrent client downloads your music e.g. /Users/name/Downloads/music.'),
                tooltip=_('Full path where your torrent client downloads your music'),
                #maxlength=50
            ),
            OptionBool('KEEP_TORRENT_FILES', 'General', False,
                label=_('Keep Files for Seeding'),
                tooltip=_('Keep Files for Seeding')
            ),

            OptionDropdown('PREFER_TORRENTS', 'General', 0, typeconv=int,
                label=_('Prefer'),
                tooltip=_('Prefered way'),
                items=(
                    (0, _('NZBs')),
                    (1, _('Torrents')),
                    (2, _('No Preference')),
                )
            ),
        ))
    )
