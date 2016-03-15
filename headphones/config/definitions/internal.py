# =======================================================================================
# Special internal option, which will never be visible in UI
# =======================================================================================

from ..typeconv import path, boolext
from .._viewmodel import OptionInternal

def _(x):
    """ required just for marking translatable strings"""
    return x


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



        # TODO : need to check the following options (may be they are not internal):

        OptionInternal('BLACKHOLE', 'General', False, typeconv=boolext),
        # OptionBool('BLACKHOLE', 'General', False,
        #     label=_('Black Hole DON KNOW WHERE!!'),
        #     tooltip=_('Method for downloading usenet files.')
        # ),
	)
