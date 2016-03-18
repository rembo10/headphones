# =======================================================================================
# Options from "Web Interface" Tab
# =======================================================================================

from .._viewmodel import Block
from .._viewmodel import OptionString, OptionNumber, OptionPassword, OptionBool, OptionPath, OptionDropdown, OptionUrl, OptionDropdownSelector, LabelExtension
from ..loc import _

def reg(tabname, register_block_cb, register_options_cb):

    # =======================================================================================
    # USENET SETTINGS
    # =======================================================================================
    register_block_cb(tabname,
        Block('usenet_selector', caption=_("Prefered Usenet"), options=register_options_cb(
            OptionDropdownSelector('NZB_DOWNLOADER', 'General', 0, initype=int,
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
                            OptionDropdown('NZBGET_PRIORITY', 'NZBget', 0, initype=int,
                                label=_('NZBget Priority'),
                                tooltip=_('NZBget Priority'),
                                items=(
                                    (-100, _('Very low')),
                                    (-50, _('Low')),
                                    (0, _('Normal')),
                                    (50, _('High')),
                                    (100, _('Very high')),
                                    (900, _('Force')),
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
        Block('torrent_selector', caption=_("Prefered Torrent"), options=register_options_cb(
            OptionDropdownSelector('TORRENT_DOWNLOADER', 'General', 0, initype=int,
                label=_('Torrent downloader'),
                tooltip=_('Preferred torrent downloader'),
                items=(
                    (0, _('Black Hole'),
                        register_options_cb(
                            OptionPath('TORRENTBLACKHOLE_DIR', 'General', '',
                                label=_('Black Hole Directory'),
                                caption=_('Folder your Download program watches for Torrents'),
                                tooltip=_('Black Hole Directory'),
                                # maxlength = 50,
                            ),
                            OptionDropdown('MAGNET_LINKS', 'General', 0, initype=int,
                                label=_('Magnet links'),
                                tooltip=_('Magnet links'),
                                caption=_('Note: Opening magnet URLs is not suitable for headless/console/terminal servers.<br />Embed only works for rTorrent.'),
                                items=(
                                    (0, _('Ignore')),  # TODO: title = Invoke shell command to open magnet URL
                                    (1, _('Open')),    # TODO: title = Use external service to convert magnet links into torrents.
                                    (2, _('Convert')),
                                    (3, _('Embed')),
                                )
                            ),
                        )
                    ),
                    (1, _('Transmission'),
                        register_options_cb(
                            OptionUrl('TRANSMISSION_HOST', 'Transmission', '',
                                label=_('Transmission Host'),
                                caption=_('usually http://localhost:9091'),
                                tooltip=_('Transmission Host'),
                                maxlength=128
                            ),
                            OptionString('TRANSMISSION_USERNAME', 'Transmission', '',
                                label=_('Transmission Username'),
                                tooltip=_('Transmission Username'),
                                maxlength=30
                            ),
                            OptionPassword('TRANSMISSION_PASSWORD', 'Transmission', '',
                                label=_('Transmission Password'),
                                tooltip=_('Transmission Password'),
                                maxlength=30
                            ),

                            LabelExtension(
                                cssclasses=['small'],
                                label=_('Note: With Transmission, you can specify a different download'
                                           ' directory for downloads sent from Headphones. Set it in the Music'
                                           ' Download Directory below'
                                )
                            ),
                        )
                    ),
                    (2, _('uTorrent (Beta)'),
                        register_options_cb(
                            LabelExtension(
                                cssclasses=['small', 'heading'],
                                label=_('<i class="fa fa-info-circle"></i> Note: uTorrent may keep files'
                                           ' read only when completed. Check "Preferences -> Advanced -> bt.read_only_on_complete"'
                                           ' in case of problems.'
                                )
                            ),
                            OptionUrl('UTORRENT_HOST', 'uTorrent', '',
                                label=_('uTorrent Host'),
                                caption=_('usually http://localhost:9091'),
                                maxlength=128
                            ),
                            OptionString('UTORRENT_USERNAME', 'uTorrent', '',
                                label=_('uTorrent Username'),
                                maxlength=64
                            ),
                            OptionPassword('UTORRENT_PASSWORD', 'uTorrent', '',
                                label=_('uTorrent Password'),
                                maxlength=64
                            ),
                            OptionString('UTORRENT_LABEL', 'uTorrent', '',
                                label=_('uTorrent Label'),
                                maxlength=30
                            ),
                        )
                    ),
                    (3, _('Deluge (Beta)'),
                        register_options_cb(
                            OptionUrl('DELUGE_HOST', 'Deluge', '',
                                label=_('Deluge WebUI Host and Port'),
                                caption=_('Usually http://localhost:8112 (requires WebUI plugin)'),
                                maxlength=128
                            ),
                            OptionPassword('DELUGE_PASSWORD', 'Deluge', '',
                                label=_('Deluge Password'),
                                maxlength=64
                            ),
                            LabelExtension(
                                cssclasses=['small'],
                                label=_('Note: With Deluge, you can specify a different download'
                                         ' directory for downloads sent from Headphones. Set it in'
                                         ' the Music Download Directory below'
                                )
                            ),
                            OptionString('DELUGE_LABEL', 'Deluge', '',
                                label=_('Deluge Label'),
                                caption=_('Labels shouldn\'t contain spaces (requires Label plugin)'),
                                #maxlength=64
                            ),
                            OptionPath('DELUGE_DONE_DIRECTORY', 'Deluge', '',
                                label=_('Move When Completed'),
                                caption=_('Directory where Deluge should move completed downloads'),
                                maxlength=64
                            ),
                            OptionBool('DELUGE_PAUSED', 'Deluge', False,
                                label=_('Add Torrent Paused'),
                            ),
                        )
                    ),
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

            OptionDropdown('PREFER_TORRENTS', 'General', 0, initype=int,
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
