from .._viewmodel import BlockExtension
from .._viewmodel import OptionString, OptionSwitch, OptionBool, OptionUrl, OptionEmail
from .._viewmodel import OptionNumber, OptionPassword, OptionDropdown
from .._viewmodel import OptionInternal
from .._viewmodel import TemplaterExtension

from ..loc import _

"""
Options for "Notifications" Tab
"""

def reg(extend_cb):
    opts = []

    # =======================================================================================
    opts.append(
       BlockExtension('notify_boxcar2', caption=None, options=extend_cb(
            OptionSwitch('BOXCAR_ENABLED', 'Boxcar', False,
                label=_('Boxcar 2'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('BOXCAR_TOKEN', 'Boxcar', '',
                        label=_('Access Token'),
                        maxlength=64
                    ),
                    OptionBool('BOXCAR_ONSNATCH', 'Boxcar', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_email', caption=None, options=extend_cb(
            OptionSwitch('EMAIL_ENABLED', 'Email', False,
                label=_('Email'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionEmail('EMAIL_FROM', 'Email', '',
                        label=_('From'),
                        maxlength=255
                    ),
                    OptionEmail('EMAIL_TO', 'Email', '',
                        label=_('To'),
                        maxlength=255
                    ),
                    OptionString('EMAIL_SMTP_SERVER', 'Email', '',
                        label=_('SMTP Server'),
                        maxlength=255
                    ),
                    OptionString('EMAIL_SMTP_USER', 'Email', '',
                        label=_('SMTP User'),
                        maxlength=255
                    ),
                    OptionPassword('EMAIL_SMTP_PASSWORD', 'Email', '',
                        label=_('SMTP Password'),
                        maxlength=64
                    ),
                    OptionNumber('EMAIL_SMTP_PORT', 'Email', 25,
                        label=_('SMTP Port'),
                        minvalue=0,
                        maxvalue=99999
                    ),

                    OptionBool('EMAIL_SSL', 'Email', False,
                        label=_('SSL'),
                    ),
                    OptionBool('EMAIL_TLS', 'Email', False,
                        label=_('TLS'),
                    ),
                    OptionBool('EMAIL_ONSNATCH', 'Email', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )
    # =======================================================================================
    opts.append(
       BlockExtension('notify_growl', caption=None, options=extend_cb(
            OptionSwitch('GROWL_ENABLED', 'Growl', False,
                label=_('Growl'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('GROWL_HOST', 'Growl', '',
                        label=_('Growl Host:Port'),
                        caption=_('Input host and <strong>port</strong> for Growl connection'),
                        maxlength=30
                    ),
                    OptionPassword('GROWL_PASSWORD', 'Growl', '',
                        label=_('Growl Password'),
                        maxlength=64
                    ),
                    OptionBool('GROWL_ONSNATCH', 'Growl', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_xbmc', caption=None, options=extend_cb(
            OptionSwitch('XBMC_ENABLED', 'XBMC', False,
                label=_('Kodi / XBMC'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('XBMC_HOST', 'XBMC', '',
                        label=_('Host(s)'),
                        caption=_('e.g. http://localhost:8080. Separate hosts with commas'),
                    ),
                    OptionString('XBMC_USERNAME', 'XBMC', '',
                        label=_('Username'),
                        maxlength=64
                    ),
                    OptionPassword('XBMC_PASSWORD', 'XBMC', '',
                        label=_('Password'),
                        maxlength=64
                    ),
                    OptionBool('XBMC_UPDATE', 'XBMC', False,
                        label=_('Update Library'),
                    ),

                    OptionBool('XBMC_NOTIFY', 'XBMC', False,
                        label=_('Send Notifications'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_lms', caption=None, options=extend_cb(
            OptionSwitch('LMS_ENABLED', 'LMS', False,
                label=_('Logitech Media Server'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('LMS_HOST', 'LMS', '',
                        label=_('LMS Host:Port'),
                        caption=_('e.g. http://localhost:9000. Seperate hosts with commas'),
                        maxlength=64
                    ),
                )
            ),
        ))
    )
    # =======================================================================================
    opts.append(
       BlockExtension('notify_mpc', caption=None, options=extend_cb(
            OptionSwitch('MPC_ENABLED', 'MPC', False,
                label=_('MPC'),
                cssclasses=['heading'],
                alignleft=True,
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_nma', caption=None, options=extend_cb(
            OptionSwitch('NMA_ENABLED', 'NMA', False,
                label=_('NotifyMyAndroid'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('NMA_APIKEY', 'NMA', '',
                        label=_('API Key'),
                        caption=_('Separate multiple api keys with commas'),
                    ),
                    OptionDropdown('NMA_PRIORITY', 'NMA', 0, initype=int,
                        label=_('Priority'),
                        tooltip=_('Priority'),
                        items=(
                            (-2, _('Very Low')),
                            (-1, _('Moderate')),
                            (0, _('Normal')),
                            (1, _('High')),
                            (2, _('Emergency')),
                        )
                    ),
                    OptionBool('NMA_ONSNATCH', 'NMA', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_osx', caption=None, options=extend_cb(
            OptionSwitch('OSX_NOTIFY_ENABLED', 'OSX_Notify', False,
                label=_('OS X'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('OSX_NOTIFY_APP', 'OSX_Notify', '/Applications/Headphones',
                        label=_('Register Notify App'),
                        cssclasses=['-hp-notify-osx-register'],
                        caption=_('Enter the path/application name to be registered with the'
                                  ' Notification Center, default is /Applications/Headphones'
                        ),
                    ),

                    TemplaterExtension(template_name='OsxAppRegisterExtension', strings={'caption': _('Register')}),

                    OptionBool('OSX_NOTIFY_ONSNATCH', 'OSX_Notify', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_plex', caption=None, options=extend_cb(
            OptionSwitch('PLEX_ENABLED', 'Plex', False,
                label=_('Plex'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('PLEX_SERVER_HOST', 'Plex', '',
                        label=_('Plex Server Host:Port'),
                        caption=_('Host running Plex Media Server (eg. http://192.168.1.100:32400)'),
                    ),
                    OptionString('PLEX_CLIENT_HOST', 'Plex', '',
                        label=_('Plex Client Host:Port'),
                        caption=_('Host running Plex Client (eg. http://192.168.1.100:3005)'),
                    ),
                    OptionString('PLEX_USERNAME', 'Plex', '',
                        label=_('Plex Username'),
                        caption=_('Username of your Plex client API (blank for none)'),
                        maxlength=64
                    ),
                    OptionPassword('PLEX_PASSWORD', 'Plex', '',
                        label=_('Plex Password'),
                        caption=_('Password of your Plex client API (blank for none)'),
                        maxlength=64
                    ),
                    OptionString('PLEX_TOKEN', 'Plex', '',
                        label=_('Plex Token'),
                        caption=_('Plex Token (for use with Plex Home)'),
                        maxlength=128
                    ),
                    OptionBool('PLEX_UPDATE', 'Plex', False,
                        label=_('Update Plex Library'),
                    ),
                    OptionBool('PLEX_NOTIFY', 'Plex', False,
                        label=_('Send Notifications to Plex'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_prowl', caption=None, options=extend_cb(
            OptionSwitch('PROWL_ENABLED', 'Prowl', False,
                label=_('Prowl'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('PROWL_KEYS', 'Prowl', '',
                        label=_('API key'),
                        maxlength=128
                    ),
                    OptionDropdown('PROWL_PRIORITY', 'Prowl', 0, initype=int,
                        label=_('Priority'),
                        tooltip=_('Priority'),
                        items=(
                            (-2, _('Very Low')),
                            (-1, _('Moderate')),
                            (0, _('Normal')),
                            (1, _('High')),
                            (2, _('Emergency')),
                        )
                    ),
                    OptionBool('PROWL_ONSNATCH', 'Prowl', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_pushalot', caption=None, options=extend_cb(
            OptionSwitch('PUSHALOT_ENABLED', 'Pushalot', False,
                label=_('Pushalot'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('PUSHALOT_APIKEY', 'Pushalot', '',
                        label=_('Pushalot API Key'),
                        caption=_('Separate multiple API keys with commas'),
                    ),
                    OptionBool('PUSHALOT_ONSNATCH', 'Pushalot', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_pushbullet', caption=None, options=extend_cb(
            OptionSwitch('PUSHBULLET_ENABLED', 'PushBullet', False,
                label=_('Pushbullet'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('PUSHBULLET_APIKEY', 'PushBullet', '',
                        label=_('Access Token'),
                    ),
                    OptionString('PUSHBULLET_DEVICEID', 'PushBullet', '',
                        label=_('Device ID'),
                        caption=_('Leave blank to send to all devices'),
                    ),
                    OptionBool('PUSHBULLET_ONSNATCH', 'PushBullet', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_pushover', caption=None, options=extend_cb(
            OptionSwitch('PUSHOVER_ENABLED', 'Pushover', False,
                label=_('Pushover'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('PUSHOVER_KEYS', 'Pushover', '',
                        label=_('User Key'),
                        caption=_(''),
                        tooltip=_(''),
                        maxlength=None
                    ),
                    OptionDropdown('PUSHOVER_PRIORITY', 'Pushover', 0, initype=int,
                        label=_('Priority'),
                        tooltip=_('Priority'),
                        items=(
                            (-1, _('Low')),
                            (0, _('Normal')),
                            (1, _('High')),
                        )
                    ),
                    OptionString('PUSHOVER_APITOKEN', 'Pushover', '',
                        label=_('API Token'),
                        caption=_('Leave blank to use Headphones default'),
                        maxlength=64
                    ),
                    OptionBool('PUSHOVER_ONSNATCH', 'Pushover', False,
                        label=_('Notify on snatch?'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_subsonic', caption=None, options=extend_cb(
            OptionSwitch('SUBSONIC_ENABLED', 'Subsonic', False,
                label=_('Subsonic'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionUrl('SUBSONIC_HOST', 'Subsonic', '',
                        label=_('Subsonic URL'),
                        maxlength=64
                    ),
                    OptionString('SUBSONIC_USERNAME', 'Subsonic', '',
                        label=_('Username'),
                    ),
                    OptionPassword('SUBSONIC_PASSWORD', 'Subsonic', '',
                        label=_('Password'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_synoindex', caption=None, options=extend_cb(
            OptionBool('SYNOINDEX_ENABLED', 'Synoindex', False,
                label=_('Synology NAS'),
                cssclasses=['heading'],
                alignleft=True,
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_twitter', caption=None, options=extend_cb(
            OptionSwitch('TWITTER_ENABLED', 'Twitter', False,
                label=_('Twitter'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('TWITTER_PREFIX', 'Twitter', 'Headphones',
                        label=_('Prefix for tweets'),
                        maxlength=64
                    ),
                    OptionBool('TWITTER_ONSNATCH', 'Twitter', False,
                        label=_('Notify on snatch?'),
                    ),

                    TemplaterExtension(template_name='TwitterNotifyExtension', strings={
                        'request-button-caption': _('Step 1: Request Authorization'),
                        'request-message': _('Confirm Authorization. Check pop-up blocker if no response.'),
                        'verify-button-caption': _('Step 2: Verify Key'),
                        'verify-placeholder': _('Input Authorization Key'),
                        'test-button-caption': _('Test Twitter'),
                    }),

                    # These fields will be filled through OAUTH:
                    # And actually, they both are auth tokens
                    OptionInternal('TWITTER_USERNAME', 'Twitter', '', initype=str),
                    OptionInternal('TWITTER_PASSWORD', 'Twitter', '', initype=str),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
       BlockExtension('notify_telegram', caption=None, options=extend_cb(
            OptionSwitch('TELEGRAM_ENABLED', 'Telegram', False,
                label=_('Telegram'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('TELEGRAM_TOKEN', 'Telegram', '',
                        label=_('Bot Token'),
                        caption=_('Contact <a href="http://telegram.me/BotFather">@BotFather</a>'
                                  ' to create a bot and get its token'),
                        maxlength=64
                    ),
                    OptionString('TELEGRAM_USERID', 'Telegram', '',
                        label=_('User ID'),
                        caption=_('Contact <a href="http://telegram.me/myidbot">@myidbot</a>'
                                  ' to get your user ID'),
                        maxlength=64
                    ),
                    OptionBool('TELEGRAM_ONSNATCH', 'Telegram', False,
                        label=_('Notify on snatch?'),
                    ),

                )
            ),
        ))
    )
    # =======================================================================================
    return opts
