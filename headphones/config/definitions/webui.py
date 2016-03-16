# =======================================================================================
# Options from "Web Interface" Tab
# =======================================================================================

from .._viewmodel import Tab, Tabs, Block
from .._viewmodel import OptionBase, OptionString, OptionNumber, OptionSwitch, OptionPassword, OptionBool, OptionPath, OptionList, OptionUrl, LabelExtension
from .._viewmodel import TemplaterExtension

def _(x):
    """ required just for marking translatable strings"""
    return x


def reg(tabname, register_block_cb, register_options_cb):

    # =======================================================================================
    register_block_cb(tabname,
       Block('basic', caption=_("Basic"), options=register_options_cb(

           OptionUrl('HTTP_HOST', 'General', 'localhost',
                label=_('HTTP Host'),
                caption=_('Use 0.0.0.0 to allow outside connections'),
                tooltip=_('Host to bind web server to'),
                maxlength=64
                ),
           OptionNumber('HTTP_PORT', 'General', 8181,
                label=_('HTTP Port'),
                tooltip=_('Port to bind web server to. Note that ports below 1024 may require root.'),
                minvalue=1,
                maxvalue=99999),
           OptionString('HTTP_USERNAME', 'General', '',
                label=_('HTTP Username'),
                tooltip=_('Username for web server authentication. Leave empty to disable.'),
                ),
           OptionPassword('HTTP_PASSWORD', 'General', '',
                label=_('HTTP Password'),
                tooltip=_('Password for web server authentication. Leave empty to disable.'),
                maxlength=64
                ),
           OptionBool('LAUNCH_BROWSER', 'General', True,
                label=_('Launch Browser on Startup'),
                tooltip=_('Launch browser pointed to Headphones, on startup.'),
                ),

           OptionSwitch('ENABLE_HTTPS', 'General', False,
                label=_('Enable HTTPS'),
                tooltip=_('Enable HTTPS for web server for encrypted communication'),
                options=register_options_cb(
                    # TODO : check default value
                    OptionPath('HTTPS_CERT', 'General', '',
                        label=_('HTTPS Cert')
                    ),
                    # TODO : check default value
                    OptionPath('HTTPS_KEY', 'General', '',
                        label=_('HTTPS Key'),
                    ),
                )),
       ))
    )

    # =======================================================================================
    register_block_cb(tabname,
       Block('api', caption=_("API"), options=register_options_cb(
            OptionSwitch('API_ENABLED', 'General', False,
                label=_('Enable API'),
                tooltip=_('Allow remote applications to interface with Headphones'),
                options=register_options_cb(
                    OptionString('API_KEY', 'General', '',
                        label=_('API key'),
                        maxlength=32,
                        options=register_options_cb(
                            TemplaterExtension('ApiKeyExtension', strings={'button':_('Generate'), 'caption':_('Current API key: ')})
                        ),
                    ),
                )
            ),
      )),
    )

    # =======================================================================================
    register_block_cb(tabname,
        Block('interval', caption=_("Interval"), options=register_options_cb(
            LabelExtension(
                label=_('An interval of 0 will disable a task.'),
                cssclasses=('small')
            ),
            OptionNumber('SEARCH_INTERVAL', 'General', 1440,
                label=_('Search Interval'),
                caption=_('in minutes, minimum is 360 minutes'),
                tooltip=_('Time between two searches for new downloads.'),
                minvalue=0,
                maxvalue=9999),
            OptionNumber('DOWNLOAD_SCAN_INTERVAL', 'General', 5,
                label=_('Download Scan Interval'),
                caption=_('in minutes'),
                tooltip=_('Time between scans for downloaded files.'),
                minvalue=0,
                maxvalue=9999),
            OptionNumber('LIBRARYSCAN_INTERVAL', 'General', 24,
                label=_('Library Scan Interval'),
                caption=_('in hours'),
                tooltip=_('Time between two library update scans.'),
                minvalue=0,
                maxvalue=9999),
            OptionNumber('UPDATE_DB_INTERVAL', 'General', 24,
                label=_('MusicBrainz Update Interval'),
                caption=_('in hours'),
                tooltip=_('Time between two MusicBrainz updates.'),
                minvalue=0,
                maxvalue=9999),
            OptionNumber('MB_IGNORE_AGE', 'General', 365,
                label=_('Ignore Album Updates'),
                caption=_('in days'),
                tooltip=_('Ignore MusicBrainz album updates older then certain number of days.'),
                minvalue=0,
                maxvalue=9999),
        ))
    )
