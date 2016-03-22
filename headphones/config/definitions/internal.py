# =======================================================================================
# Special internal option, which will never be visible in UI
# =======================================================================================

from ..typeconv import path, boolext
from .._viewmodel import OptionInternal, OptionDeprecated

def reg(_extend_cb):
    opts = [
        OptionInternal('CONFIG_VERSION', 'General', 0, initype=int),
        OptionInternal('INTERFACE', 'General', 'default', initype=str),
        OptionInternal('SOFT_CHROOT', 'General', '', initype=path),

        # TODO : move git to advanced tab (if necessary) and make it visible
        OptionInternal('GIT_BRANCH', 'General', 'master', initype=str),
        # TODO : this is list of paths!
        OptionInternal('GIT_PATH', 'General', '', initype=str), # full path to `git` binary.
        OptionInternal('DO_NOT_OVERRIDE_GIT_BRANCH', 'General', False, initype=boolext),

        OptionInternal('HTTP_PROXY', 'General', False, initype=boolext),
        OptionInternal('HTTP_ROOT', 'General', '/', initype=str),

        # From "# > Manage > Scan Music Library"
        OptionInternal('AUTO_ADD_ARTISTS', 'General', True, initype=boolext),
        OptionInternal('LIBRARYSCAN', 'General', True, initype=boolext),
        # TODO : move to settings!! (this will make SoftChroot implementation much beautiful)
        OptionInternal('MUSIC_DIR', 'General', '', initype=path),

        # TODO: test, that config.ini contains line:
        # ignored_files = ,
        OptionInternal('IGNORED_FILES', 'Advanced', [], initype=list),
        OptionInternal('IGNORED_FOLDERS', 'Advanced', [], initype=list),

        OptionInternal('CUE_SPLIT_FLAC_PATH', 'General', '', initype=path),
        OptionInternal('CUE_SPLIT_SHNTOOL_PATH', 'General', '', initype=path),

        OptionInternal('JOURNAL_MODE', 'Advanced', 'wal', initype=str),

        # From "# > Manage > Imports > Import Last.FM Artists"
        OptionInternal('LASTFM_USERNAME', 'General', '', initype=str),
        # ==============================================================================
        # DEPRECATED BLOCK
        #
        # This options are REQUIRED to upgrade any old versions of the config.ini

        OptionDeprecated('BLACKHOLE', 'General', False, initype=boolext),
        OptionDeprecated('OPEN_MAGNET_LINKS', 'General', False, initype=boolext),
        OptionDeprecated('ENCODERFOLDER', 'General', '', initype=path),

        # from SEARCH PROVIDERS tab
        OptionDeprecated('NZBSORG_UID', 'NZBsorg', '', initype=str),
    ]

    return opts
