# =======================================================================================
# Special internal option, which will never be visible in UI
# =======================================================================================

from headphones.config.typeconv import path, boolext
from headphones.config.viewmodel import OptionInternal

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
        OptionInternal('GIT_PATH', 'General', '', typeconv=str),
        OptionInternal('GIT_USER', 'General', 'rembo10', typeconv=str),
        OptionInternal('DO_NOT_OVERRIDE_GIT_BRANCH', 'General', False, typeconv=boolext),

        OptionInternal('HTTP_PROXY', 'General', False, typeconv=boolext),
        OptionInternal('HTTP_ROOT', 'General', '/', typeconv=str),
	)
