import re
import os
from itertools import ifilter, imap
from mako.template import Template
from mako.lookup import TemplateLookup

import headphones
from headphones import logger
from headphones.exceptions import ConfigError

from headphones.config.typeconv import path, boolext
from _datamodel import OptionModel

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
        # TODO : make this static, to optimize the search for a template
        # TODO : it is important to optimize this, because this method called to often
        if not self._hplookup:
            # TODO : to ensure, that there is enough calls - put PRINT here
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
            raise TypeError('Not a Block')

        self._sorted = False

        bid = block.id
        if bid in self._map:
            # extend
            raise ConfigError('Duplicate block')
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

    def __init__(self, appkey, section, default=None, options=None, typeconv=str):
        """Initialization

        Args:
            appkey - unique identifier for an option
            section - name of section in CONFIG FILE
            default - default value
            typeconv - function to convert data from 
            options - list of suboptions
        """
        super(OptionBase, self).__init__()

        self.model = OptionModel(appkey=appkey, section=section, default=default, typeconv=typeconv)

        self._options = options or []  # should not be None

        self.visible = True
        self.readonly = False


    def __repr__(self):
        return "<{0} appkey={1}>".format(
            self.__class__.__name__,
            self.model.appkey
        )

    def __iter__(self):
        """ Iterates over visible suboptions """
        return ifilter(lambda t: t.visible if hasattr(t, 'visible') else True, self._options)

    def __len__(self):
        return len(self._options)

    def render(self, parent=None):
        return super(OptionBase, self).render(me=self, parent=parent)

    @property
    def appkey(self):
        return self.model.appkey

    #@property
    def uiValue(self):
        return self.model.get()

    def uiValue2DataValue(self, value):
        """
        Parses the value, which will be receiven on POSTing form with this options.
        Returned value MUST BE compatible with datamodel's value
        """
        return value

    def uiName(self):
        "This is an identifier of option, when data are sended/received to/from UI"
        return 'hp_ui_' + self.model.appkey.lower()

# ===============================================
# API-usable options
# ===============================================

# class Option_SCAFFOLD_(OptionBase):

#     def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None):
#         super(Option_SCAFFOLD_, self).__init__(appkey, section, default)

#         self.label = label
#         self.caption = caption
#         self.tooltip = tooltip

class OptionInternal(OptionBase):
    """ This option will not appear in the UI. It is internal stuff"""
    def __init__(self, appkey, section, default=None, typeconv=str):
        super(OptionInternal, self).__init__(appkey, section, default, typeconv=typeconv)

        self.readonly = True
        self.visible = False

class OptionString(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None, maxlength=None):
        super(OptionString, self).__init__(appkey, section, default, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

class OptionPath(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None, maxlength=None):
        super(OptionPath, self).__init__(appkey, section, default, typeconv=path, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

    @property
    def templateName(self):
        # currently, path uses the same template as string
        return "OptionString"

class OptionPassword(OptionString):
    pass

class OptionNumber(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, minvalue=None, maxvalue=None):
        super(OptionNumber, self).__init__(appkey, section, default, typeconv=int)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.minvalue = minvalue
        self.maxvalue = maxvalue

    def uiValue2DataValue(self, value):
        # override
        return int(value)

class OptionBool(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption = None, tooltip=None, options=None):
        super(OptionBool, self).__init__(appkey, section, default, typeconv=boolext, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

    def uiValue2DataValue(self, value):
        # override
        if value == '1':
            return True
        if value == '0':
            return False
        raise ValueError('Unexpected bool value accepted: {0}'.format(value))

class OptionList(OptionString):

    @property
    def templateName(self):
        return "OptionString"

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


# ===============================================
# ===============================================
# ViewModel Parser
# ===============================================
# ===============================================

class PostDataParser(object):
    """ Knows how to parse options, POSTed from UI """

    def __init__(self):
        self._vault = {}

    def register(self, option):
        if not isinstance(option, OptionBase):
            raise TypeError('Could not register this option, because it '
                    'should be child of {0}.{1}'.format(OptionBase.__module__, OptionBase.__name__))

        k = option.uiName()
        if k in self._vault:
            raise ConfigError('Duplicate ui-key [{0}] for option [{1}]'.format(k, option.appkey))

        self._vault[k] = option

    def accept(self, values_as_dict):
        if not isinstance(values_as_dict, dict):
            raise TypeError('dict expected')

        d = values_as_dict

        diffcount = 0
        for (k,v) in d.items():
            if not k in self._vault:
                print 'NOT IN VAULT', k
                continue

            opt = self._vault[k]

            # new value
            nv = opt.uiValue2DataValue(v)
            # old value
            ov = opt.model.get()

            if ov != nv:
                opt.model.set(nv)
                logger.debug('The value of [{0}][{1}] changed [{2}] => [{3}]'.format(opt.model.section, opt.model.appkey, ov, nv))
                diffcount += 1

        return diffcount

