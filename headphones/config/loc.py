import locale
import gettext

""" This module performs just one action: it loads appropriate translation for config package """

current_locale, encoding = locale.getdefaultlocale()

# TODO : fix path
__t = gettext.translation('config', 'locale/', [current_locale], fallback=True)

_ = __t.ugettext
