from .._viewmodel import BlockExtension
from .._viewmodel import OptionString, OptionSwitch, OptionUrl, OptionList
from .._viewmodel import OptionNumber, OptionFloat, OptionPassword
from .._viewmodel import TemplaterExtension

from ..loc import _

# =======================================================================================
"""
Options from "Search Providers" Tab
"""
# =======================================================================================

def reg(extend_cb):

    opts = []

    # =======================================================================================
    # NZB
    # =======================================================================================
    opts.append(
        BlockExtension('search_headphones', caption=None, options=extend_cb(
            OptionSwitch('HEADPHONES_INDEXER', 'General', False,
                label=_('Headphones Indexer'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('HPUSER', 'General', '',
                        label=_('Username'),
                        caption=_('Headphones VIP Server username'),
                        cssclasses=['-hp-hp-user'],
                        maxlength=128
                    ),
                    OptionPassword('HPPASS', 'General', '',
                        label=_('Password'),
                        caption=_('Headphones VIP Server password'),
                        cssclasses=['-hp-hp-pass'],
                        maxlength=128,
                    ),
                    TemplaterExtension(template_name='CodeshyRegExtension', strings={'caption': _('Don\'t have an account? Sign up!')}),
                )
            ),
        ))
    )

    # =======================================================================================
    # TODO : #13 newznab
    extend_cb(
        OptionList('EXTRA_NEWZNABS', 'Newznab', '',
            label=_('zzEXTRA_NEWZNABSzz'),
            caption=_(''),
            tooltip=_(''),
        ),
        OptionNumber('NEWZNAB', 'Newznab', 0,
            label=_('zzNEWZNABzz'),
            caption=_(''),
            tooltip=_(''),
            minvalue=None,
            maxvalue=None
        ),
        OptionString('NEWZNAB_APIKEY', 'Newznab', '',
            label=_('zzNEWZNAB_APIKEYzz'),
            caption=_(''),
            tooltip=_(''),
            maxlength=None
        ),
        OptionNumber('NEWZNAB_ENABLED', 'Newznab', 1,
            label=_('zzNEWZNAB_ENABLEDzz'),
            caption=_(''),
            tooltip=_(''),
            minvalue=None,
            maxvalue=None
        ),
        OptionString('NEWZNAB_HOST', 'Newznab', '',
            label=_('zzNEWZNAB_HOSTzz'),
            caption=_(''),
            tooltip=_(''),
            maxlength=None
        ),
    )
    # =======================================================================================
    opts.append(
        BlockExtension('search_nzbsorg', caption=None, options=extend_cb(
            OptionSwitch('NZBSORG', 'NZBsorg', False,
                label=_('NZBs.org'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('NZBSORG_HASH', 'NZBsorg', '',
                        label=_('NZBs.org API Key'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_omgwtfnzbs', caption=None, options=extend_cb(
            OptionSwitch('OMGWTFNZBS', 'omgwtfnzbs', False,
                label=_('omgwtfnzbs'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('OMGWTFNZBS_UID', 'omgwtfnzbs', '',
                        label=_('omgwtfnzbs UID'),
                        maxlength=32
                    ),
                    OptionString('OMGWTFNZBS_APIKEY', 'omgwtfnzbs', '',
                        label=_('omgwtfnzbs API Key'),
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    # Torrents
    # =======================================================================================
    opts.append(
        BlockExtension('search_piratebay', caption=None, options=extend_cb(
            OptionSwitch('PIRATEBAY', 'Piratebay', False,
                label=_('The Pirate Bay'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionUrl('PIRATEBAY_PROXY_URL', 'Piratebay', '',
                        label=_('Proxy URL'),
                        caption=_('Optional. Leave empty for default.'),
                    ),
                    OptionFloat('PIRATEBAY_RATIO', 'Piratebay', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding.'
                        ),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_kat', caption=None, options=extend_cb(
            OptionSwitch('KAT', 'Kat', False,
                label=_('Kick Ass Torrents'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionUrl('KAT_PROXY_URL', 'Kat', '',
                        label=_('Proxy URL'),
                        caption=_('Optional. Leave empty for default.'),
                    ),
                    OptionFloat('KAT_RATIO', 'Kat', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job'
                                  ' will remove torrent when post processed and finished seeding'
                        ),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_waffles', caption=None, options=extend_cb(
            OptionSwitch('WAFFLES', 'Waffles', False,
                label=_('Waffles.fm'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('WAFFLES_UID', 'Waffles', '',
                        label=_('UID Number'),
                        maxlength=64
                    ),
                    OptionPassword('WAFFLES_PASSKEY', 'Waffles', '',
                        label=_('Passkey'),
                        maxlength=64
                    ),
                    OptionFloat('WAFFLES_RATIO', 'Waffles', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'
                        ),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_rutracker', caption=None, options=extend_cb(
            OptionSwitch('RUTRACKER', 'Rutracker', False,
                label=_('rutracker.org'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('RUTRACKER_USER', 'Rutracker', '',
                        label=_('Username'),
                        maxlength=64
                    ),
                    OptionPassword('RUTRACKER_PASSWORD', 'Rutracker', '',
                        label=_('Password'),
                        maxlength=64
                    ),
                    OptionFloat('RUTRACKER_RATIO', 'Rutracker', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_what_cd', caption=None, options=extend_cb(
            OptionSwitch('WHATCD', 'What.cd', False,
                label=_('What.cd'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionString('WHATCD_USERNAME', 'What.cd', '',
                        label=_('Username'),
                        maxlength=64
                    ),
                    OptionPassword('WHATCD_PASSWORD', 'What.cd', '',
                        label=_('Password'),
                        maxlength=None
                    ),
                    OptionFloat('WHATCD_RATIO', 'What.cd', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_strike', caption=None, options=extend_cb(
            OptionSwitch('STRIKE', 'Strike', False,
                label=_('Strike Search'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionFloat('STRIKE_RATIO', 'Strike', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    # TODO : #13 torznabs
    extend_cb(
        OptionList('EXTRA_TORZNABS', 'Torznab', [],
            label=_('zzEXTRA_TORZNABSzz'),
            caption=_(''),
            tooltip=_(''),
        ),
        OptionNumber('TORZNAB', 'Torznab', 0,
            label=_('zzTORZNABzz'),
            caption=_(''),
            tooltip=_(''),
            minvalue=None,
            maxvalue=None
        ),
        OptionString('TORZNAB_APIKEY', 'Torznab', '',
            label=_('zzTORZNAB_APIKEYzz'),
            caption=_(''),
            tooltip=_(''),
            maxlength=None
        ),
        OptionNumber('TORZNAB_ENABLED', 'Torznab', 1,
            label=_('zzTORZNAB_ENABLEDzz'),
            caption=_(''),
            tooltip=_(''),
            minvalue=None,
            maxvalue=None
        ),
        OptionString('TORZNAB_HOST', 'Torznab', '',
            label=_('zzTORZNAB_HOSTzz'),
            caption=_(''),
            tooltip=_(''),
            maxlength=None
        ),
    )
    # =======================================================================================
    opts.append(
        BlockExtension('search_oldpiratebay', caption=None, options=extend_cb(
            OptionSwitch('OLDPIRATEBAY', 'Old Piratebay', False,
                label=_('Old Pirate Bay'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionUrl('OLDPIRATEBAY_URL', 'Old Piratebay', '',
                        label=_('URL'),
                        maxlength=None
                    ),
                    OptionFloat('OLDPIRATEBAY_RATIO', 'Old Piratebay', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    opts.append(
        BlockExtension('search_mininova', caption=None, options=extend_cb(
            OptionSwitch('MININOVA', 'Mininova', False,
                label=_('Mininova'),
                cssclasses=['heading'],
                alignleft=True,
                options=extend_cb(
                    OptionFloat('MININOVA_RATIO', 'Mininova', None,
                        label=_('Seed Ratio'),
                        caption=_('Stop seeding when ratio met, 0 = unlimited. Scheduled job will'
                                  ' remove torrent when post processed and finished seeding'),
                        minvalue=0,
                        maxvalue=999999,
                    ),
                )
            ),
        ))
    )

    # =======================================================================================
    return opts
