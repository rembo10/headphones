# =======================================================================================
# Options from "Search Providers" Tab
# =======================================================================================

from headphones.config.viewmodel import Block
from headphones.config.viewmodel import OptionBase, OptionString, OptionNumber, OptionSwitch, OptionPassword, OptionBool, OptionPath, OptionList
from headphones.config.viewmodel import TemplaterExtension

def _(x):
    """ required just for marking translatable strings"""
    return x

def reg(tabname, register_block_cb, register_options_cb):

    register_block_cb(tabname,
        Block('git', caption=_("GitHub"), options=register_options_cb(
            OptionSwitch('CHECK_GITHUB', 'General', True,
                label=_('GitHub Updater Enabled'),
                tooltip=_('Enable autoupdates for Headphones through GitHub '),

                options=register_options_cb(
                    OptionString('GIT_USER', 'General', 'rembo10'
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

