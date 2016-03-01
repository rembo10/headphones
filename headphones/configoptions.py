import re
import os
import headphones
from mako.template import Template
from mako.lookup import TemplateLookup

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




class OptionBase(object):

    def __init__(self, appkey, section, default=None):
        """Initialization

        Args:
            appkey - unique identifier for an option
            section - name of section in CONFIG FILE
            default - default value
        """
        self.appkey = appkey
        self.default = default
        self.section = section

        self.writable = True
        self.readable = True

        self.value = None

    def render(self):
        """ Used in the config UI, should return result of rendering MAKO template - string """

        # TEMPLATING PRECOMPUTED STUFF
        # TODO : think twice about using option in options!!!!
        opt_INTERFACE = headphones.CONFIG.INTERFACE
        # TODO : compute this in static method
        prog_dir = str(headphones.PROG_DIR)
        _interface_dir = os.path.join(prog_dir, 'data/interfaces/')
        _template_dir = os.path.join(str(_interface_dir), opt_INTERFACE)

        _template_tmp_dir = os.path.join(prog_dir, 'auto')
        self._hplookup = TemplateLookup(directories=[_template_dir], module_directory=_template_tmp_dir)

        # TODO : add TRY-EXCEPT

        # this block searches for a template of an option (by name)
        # and render appropriate MAKO-def
        template = self._hplookup.get_template(self.getTemplateFileName())
        defs = template.get_def(self.getTemplateName())
        return defs.render(o=self)

    def getTemplateName(self):
        return self.__class__.__name__

    def getTemplateFileName(self):
        return "config-templates.html"

class OptionString(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, maxlength=None):
        super(OptionString, self).__init__(appkey, section, default)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

class OptionPath(OptionString):

    def getTemplateName(self):
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

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None):
        super(OptionBool, self).__init__(appkey, section, default)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

class OptionSwitch(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None):
        super(OptionSwitch, self).__init__(appkey, section, default)


# class Option_SCAFFOLD_(OptionBase):

#     def __init__(self, appkey, section='General', default=None):
#         super(Option_SCAFFOLD_, self).__init__(appkey, section, default)
