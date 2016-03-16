# =======================================================================================
# Options from "Search Providers" Tab
# =======================================================================================

from .._viewmodel import Block
from .._viewmodel import OptionBase, OptionString, OptionNumber, OptionSwitch, OptionPassword, OptionBool, OptionPath, OptionList
from .._viewmodel import TemplaterExtension

def _(x):
    """ required just for marking translatable strings"""
    return x

def reg(tabname, register_block_cb, register_options_cb):

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
                    # Convert to OptionFilePermission
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
                    # Convert to OptionFilePermission
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
