# =======================================================================================
# Special internal option, which will never be visible in UI
# =======================================================================================

from headphones.config.typeconv import path
from headphones.config.viewmodel import OptionInternal

def _(x):
    """ required just for marking translatable strings"""
    return x


def reg(register_block_cb, register_options_cb):

    register_options_cb(
        OptionInternal('CONFIG_VERSION', 'General', 0, typeconv=int),
        OptionInternal('INTERFACE', 'General', 'default', typeconv=str),
        OptionInternal('SOFT_CHROOT', 'General', '', typeconv=path),
    )
