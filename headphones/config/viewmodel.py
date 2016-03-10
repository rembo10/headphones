import re
import os
from itertools import ifilter, imap
from mako.template import Template
from mako.lookup import TemplateLookup

import headphones
from headphones import logger

# ===============================================
""" ViewModel-classes of configuration 

Some of classes still just ViewModels, without its own template (for example : Tabs)
But the most classes have its own template (they are inherited from Renderable)
"""
# ===============================================

# will be useful for translation
def _(x):
    return x

# ===============================================
# Abstract, base class
# ===============================================

class Renderable(object):
    """ Basic class for all things, which could be rendered in runtime from python code """

    def __init__(self):
        # internal templating stuff:
        self._hplookup = None

    def _getTemplateLookup(self):
        # TDO : make this static, to optimize the search for a template
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
        return self.__class__.__name__

    @property
    def templateFileName(self):
        return "config-templates.html"

    def render(self, **qwargs):
        """ Used in the config UI, should return result of rendering MAKO template - string """

        try:
            # this block searches for a template of an option (by name)
            # and render appropriate MAKO-def
            template = self._getTemplateLookup().get_template(self.templateFileName)
            defs = template.get_def(self.templateName)
        except Exception, e:
            logger.error('Error on render template: {0}'.format(e.message))
            raise

        return defs.render(**qwargs)

# ===============================================
# Section "One-time used templates"
#
# Tabs, Tab and Block classes are defined here.
# Their templates are used just once, and, as
# a consequence, are embed to the main template -
# - config.html
# ===============================================

class Tabs(object):
    """ ViewModel for entire TABS element. Contains all the tabs """

    def __init__(self, *args):
        self.tabs = list(*args)
        pass

    def __repr__(self):
        return "<%s with %d tabs>" % (
            self.__class__.__name__,
            len(self.tabs)
        )

    def __iter__(self):
        """ Default iterator is sharpened for UI tasks """

        return ifilter(lambda t: True, self.tabs)
    pass

class Tab(Renderable):
    """ UI-tab for grouping option on a UI-page """

    def __init__(self, id, caption=None, cssclass=None, message=None):
        super(Tab, self).__init__()

        self._map = {}
        self._index = []
        self._sorted = True

        self.id = re.sub(r'[^\w\d_]', '_', id)
        self.caption = caption
        self.cssclass = cssclass
        self.message = message
        self.__setitem__ = None

    def __repr__(self):
        return "<%s id='%s', caption='%s', with %d blocks>" % (
            self.__class__.__name__,
            self.id,
            self.caption,
            len(self._map)
        )

    # itertools:
    def __getitem__(self, *args, **qw):
        return self._map.__getitem__(*args, **qw)

    def __iter__(self):
        """ Iterates over non-empty tabs """

        if not self._sorted:
            self._index.sort(key=lambda a: a[0])

        # TODO : omit empty blocks
        return imap(lambda x: x[1], ifilter(lambda t: True, self._index))

    def add(self, block, order=None):
        """ add one block to current tab """

        if not isinstance(block, Block):
            raise Exception('Not a Block')

        self._sorted = False

        bid = block.id
        if bid in self._map:
            # extend
            raise Exception('Duplicate block')
        else:
            # append
            self._map[bid] = block
            self._index.append(tuple([order, block]))

    pass

class Block(object):
    """ UI-block for grouping options within `Tab` """

    def __init__(self, id, caption=None, cssclass=None, options=None):
        self.id = re.sub(r'[^\w\d_]', '_', id)
        self.caption = caption
        self._options = options or []  # should not be None
        self.cssclass = cssclass

    def __repr__(self):
        return "<%s id=%s, caption=%s, with %d options>" % (
            self.__class__.__name__,
            self.id,
            self.caption,
            len(self._options)
        )

    def __iter__(self):
        """ Iterates over non-empty tabs """
        # TODO : omit invisible options blocks
        return ifilter(lambda t: True, self._options)

    pass


# ===============================================
# base class for options
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

    def render(self, parent=None):
        return super(OptionBase, self).render(me=self, parent=parent)

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


# ===============================================
# Option extensions
# ===============================================


class TemplaterExtension(Renderable):
    """ Allow render any template, extending HTML for options with non-standart layout """

    def __init__(self, template_name=None, strings=None):
        super(TemplaterExtension, self).__init__()
        self._template_name = template_name

        self.strings = strings

    @property
    def templateName(self):
        return self._template_name

    def render(self, parent=None):
        return super(TemplaterExtension, self).render(me=self, parent=parent)

    def __repr__(self):
        return "<%s template_name=%s>" % (
            self.__class__.__name__,
            self._template_name
        )
