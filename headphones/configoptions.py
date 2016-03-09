import re
import os
from itertools import ifilter
from mako.template import Template
from mako.lookup import TemplateLookup
import headphones

# will be helpful for translations
def _(x):
    return x


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, basestring):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))


class path(str):
    """Internal 'marker' type for paths in config."""

    @staticmethod
    def __call__(val):
        return path(val)

    def __new__(cls, *args, **kw):
        hstr = str.__new__(cls, *args, **kw)
        return hstr

    def __repr__(self):
        return 'headphones.config.path(%s)' % self


# ===============================================
# Abstract, base class
# ===============================================

class Renderable(object):
    """ Basic class for all things, which want be renderable on runtime """

    def __init__(self):
        self._templateName=None
        self._templateFileName = None

        # internal templating stuff:
        self._hplookup = None

    def _getTemplateLookup(self):
        if not self._hplookup:
            opt_INTERFACE = headphones.CONFIG.INTERFACE
            prog_dir = str(headphones.PROG_DIR)
            _interface_dir = os.path.join(prog_dir, 'data/interfaces/')
            _template_dir = os.path.join(str(_interface_dir), opt_INTERFACE)

            _template_tmp_dir = os.path.join(prog_dir, 'auto')
            self._hplookup = TemplateLookup(directories=[_template_dir], module_directory=_template_tmp_dir)

        return self._hplookup

    @property
    def templateName(self):
        return self._templateName

    @property
    def templateFileName(self):
        return self._templateFileName

    def render(self, **qwargs):
        """ Used in the config UI, should return result of rendering MAKO template - string """

        # TODO : add TRY-EXCEPT
        # this block searches for a template of an option (by name)
        # and render appropriate MAKO-def
        template = self._getTemplateLookup().get_template(self.templateFileName)
        defs = template.get_def(self.templateName)
        print ('root render', qwargs)

        return defs.render(**qwargs)

# ===============================================
# Abstract, base class
# ===============================================

class OptionBase(Renderable):
    """ Base, abstract parent for all other options """

    def __init__(self, appkey, section, default=None, options=None):
        """Initialization

        Args:
            appkey - unique identifier for an option
            section - name of section in CONFIG FILE
            default - default value
        """
        super(OptionBase, self).__init__()

        self.appkey = appkey
        self.default = default
        self.section = section
        self._options = options or []  # should not be None

        self.writable = True
        self.readable = True

        self.value = None

    def __iter__(self):
        """ Iterates over non-empty tabs """
        return ifilter(lambda t: t.readable if hasattr(t, 'readable') else True, self._options)

    def __len__(self):
        return len(self._options)

    def uiId(self):
        return self.appkey

    @property
    def templateName(self):
        return self.__class__.__name__

    @property
    def templateFileName(self):
        return "config-templates.html"

    def render(self, parent=None):
        return super(OptionBase, self).render(o=self, parent=parent)

# ===============================================
# API-usable options
# ===============================================

# class Option_SCAFFOLD_(OptionBase):

#     def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None):
#         super(Option_SCAFFOLD_, self).__init__(appkey, section, default)

#         self.label = label
#         self.caption = caption
#         self.tooltip = tooltip

class OptionString(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None, maxlength=None):
        super(OptionString, self).__init__(appkey, section, default, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

class OptionPath(OptionString):

    @property
    def templateName(self):
        return "OptionString"

class OptionPassword(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, maxlength=None):
        super(OptionPassword, self).__init__(appkey, section, default)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

class OptionNumber(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, minvalue=None, maxvalue=None):
        super(OptionNumber, self).__init__(appkey, section, default)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.minvalue = minvalue
        self.maxvalue = maxvalue

class OptionBool(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None):
        super(OptionBool, self).__init__(appkey, section, default, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

# ===============================================
# API-usable options with SUBSTRUCTURE
# ===============================================

# TODO : think about inheritance from Block
class OptionSwitch(OptionBool):
    """ Option, which includes switcher and suboptions

    This is **enabler**, or **switch** option. Its own value is `bool`, and when it is checked -
    the set of suboptions is visible for editing. When its own value is `False` - nothing happens,
    no additional settings are visible
    """
    pass

    # def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None):
    #     super(OptionSwitch, self).__init__(appkey, section, default, options=options)

    #     self.label = label
    #     self.caption = caption
    #     self.tooltip = tooltip




class ApiKeyOptionExtension(Renderable):
    def __init__(self):
        super(ApiKeyOptionExtension, self).__init__()

    @property
    def templateName(self):
        return "ApiKeyOptionExtension"