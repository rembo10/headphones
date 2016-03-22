# =======================================================================================
# Options from "Web Interface" Tab
# =======================================================================================

from .._viewmodel import BlockExtension, MessageExtension
from .._viewmodel import OptionString, OptionNumber, OptionSwitch, OptionPassword, OptionBool, OptionPath, OptionUrl
from .._viewmodel import TemplaterExtension

from ..loc import _


def reg(_extend_cb):

    opts = []
    # =======================================================================================
    opts.extend([
       BlockExtension('basic', caption=_("Basic"), options=_extend_cb(

           OptionUrl('HTTP_HOST', 'General', 'localhost',
                label=_('HTTP Host'),
                caption=_('Use 0.0.0.0 to allow outside connections'),
                tooltip=_('Host to bind web server to'),
                maxlength=64
                ),
           OptionNumber('HTTP_PORT', 'General', 8181,
                label=_('HTTP Port'),
                tooltip=_('Port to bind web server to. Note that ports below 1024 may require root. Default : 8181'),
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
                options=_extend_cb(
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
    ])

    # =======================================================================================
    opts.extend([
       BlockExtension('api', caption=_("API"), options=_extend_cb(
            OptionSwitch('API_ENABLED', 'General', False,
                label=_('Enable API'),
                tooltip=_('Allow remote applications to interface with Headphones'),
                options=_extend_cb(
                    OptionString('API_KEY', 'General', '',
                        label=_('API key'),
                        cssclasses=['-hp-api-key'],
                        maxlength=32,
                        options=_extend_cb(
                            TemplaterExtension('ApiKeyExtension', strings={'button': _('Generate'), 'caption': _('Current API key: ')})
                        ),
                    ),
                )
            ),
      )),
    ])

    # =======================================================================================
    opts.extend([
        BlockExtension('interval', caption=_("Interval"), options=_extend_cb(
            MessageExtension(
                message=_('An interval of 0 will disable a task.'),
                icon='<i class="fa fa-info-circle"></i>',
            ),
            OptionNumber('SEARCH_INTERVAL', 'General', 1440,
                label=_('Search Interval'),
                caption=_('in minutes, minimum is 360 minutes'),
                tooltip=_('Time between two searches for new downloads.'),
                minvalue=0,
                maxvalue=999999
            ),
            OptionNumber('DOWNLOAD_SCAN_INTERVAL', 'General', 5,
                label=_('Download Scan Interval'),
                caption=_('in minutes'),
                tooltip=_('Time between scans for downloaded files.'),
                minvalue=0,
                maxvalue=999999
            ),
            OptionNumber('LIBRARYSCAN_INTERVAL', 'General', 24,
                label=_('Library Scan Interval'),
                caption=_('in hours'),
                tooltip=_('Time between two library update scans.'),
                minvalue=0,
                maxvalue=999999
            ),
            OptionNumber('UPDATE_DB_INTERVAL', 'General', 24,
                label=_('MusicBrainz Update Interval'),
                caption=_('in hours'),
                tooltip=_('Time between two MusicBrainz updates.'),
                minvalue=0,
                maxvalue=999999
            ),
            OptionNumber('MB_IGNORE_AGE', 'General', 365,
                label=_('Ignore Album Updates'),
                caption=_('in days'),
                tooltip=_('Ignore MusicBrainz album updates older then certain number of days.'),
                minvalue=0,
                maxvalue=999999
            ),
            OptionNumber('TORRENT_REMOVAL_INTERVAL', 'General', 720,
                label=_('Torrent Removal Interval'),
                caption=_('in minutes'),
                tooltip=_('Remove Torrent + data if Post Processed and finished Seeding'),
                minvalue=0,
                maxvalue=999999,
            ),
        ))
    ])

    return opts
