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


        # ==============================================================================
        # DEPRECATED BLOCK
        #
        # This options are required to be able to read an old version of the config file and
        # upgrade it

        OptionDeprecated('BLACKHOLE', 'General', False, initype=boolext),
        OptionDeprecated('OPEN_MAGNET_LINKS', 'General', False, initype=boolext),
        OptionDeprecated('ENCODERFOLDER', 'General', '', initype=path),
    ]

    return opts
