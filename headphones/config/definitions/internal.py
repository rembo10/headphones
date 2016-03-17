# =======================================================================================
# Special internal option, which will never be visible in UI
# =======================================================================================

from ..typeconv import path, boolext
from .._viewmodel import OptionInternal, OptionDeprecated

# def _(x):
#     """ required just for marking translatable strings"""
#     return x

def reg(tabname, register_block_cb, register_options_cb):

    register_options_cb(
        OptionInternal('CONFIG_VERSION', 'General', 0, typeconv=int),
        OptionInternal('INTERFACE', 'General', 'default', typeconv=str),
        OptionInternal('SOFT_CHROOT', 'General', '', typeconv=path),

        # TODO : move git to advanced tab (if necessary) and make it visible
        OptionInternal('GIT_BRANCH', 'General', 'master', typeconv=str),
        # TODO : this is list of paths!
        OptionInternal('GIT_PATH', 'General', '', typeconv=str), # full path to `git` binary.
        OptionInternal('DO_NOT_OVERRIDE_GIT_BRANCH', 'General', False, typeconv=boolext),

        OptionInternal('HTTP_PROXY', 'General', False, typeconv=boolext),
        OptionInternal('HTTP_ROOT', 'General', '/', typeconv=str),

    )

    # ==============================================================================
    # DEPRECATED BLOCK
    #
    # This options are required to be able to read an old version of the config file and
    # upgrade it
    register_options_cb(
        OptionDeprecated('BLACKHOLE', 'General', False, typeconv=boolext),
        OptionDeprecated('OPEN_MAGNET_LINKS', 'General', False, typeconv=boolext),
        OptionDeprecated('ENCODERFOLDER', 'General', '', typeconv=path),
    )
