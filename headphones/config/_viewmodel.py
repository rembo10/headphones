import re
import os
import random
from itertools import ifilter, imap
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

    def __repr__(self):
        return "<%s>" % (
            self.__class__.__name__
        )

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

    def __init__(self, id, caption=None, cssclass=None, message=None, savecaption=None):
        super(Tab, self).__init__()

        self._map = {}
        self._index = []
        self._sorted = True

        self.id = re.sub(r'[^\w\d_]', '_', id)
        self.caption = caption
        self.cssclass = cssclass
        self.message = message
        self.savecaption = savecaption
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

    def __init__(self, appkey, section, default=None, options=None, initype=str):
        """Initialization

        Args:
            appkey - unique identifier for an option
            section - name of section in CONFIG FILE
            default - default value
            initype - function to convert data from internal form to config
            options - list of suboptions
        """
        super(OptionBase, self).__init__()

        self.model = OptionModel(appkey=appkey, section=section, default=default, initype=initype)

        self._options = options or []  # should not be None
        self._initype = initype

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
        Parses the value of an options, received from UI.
        Returned value MUST BE compatible with datamodel's value
        """
        return self._initype(value)

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
    def __init__(self, appkey, section, default=None, initype=str):
        super(OptionInternal, self).__init__(appkey, section, default, initype=initype)

        self.readonly = True
        self.visible = False

    def render(self, *args, **qwargs):
        """ Overridden. This kind of options are not renderable, so `render` always returns an empty string """
        return ""

class OptionDeprecated(OptionBase):
    """ This option will not appear in the UI. It is internal stuff"""
    def __init__(self, appkey, section, default=None, initype=str):
        super(OptionDeprecated, self).__init__(appkey, section, default, initype=initype)

        self.readonly = True
        self.visible = False

    def render(self, *args, **qwargs):
        """ Overridden. This kind of options are not renderable, so `render` always returns an empty string """
        return ""

class OptionString(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, maxlength=None):
        super(OptionString, self).__init__(appkey, section, default, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

class OptionCombobox(OptionString):
    """ Textbox with list of available variants """
    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, maxlength=None, items=None):
        super(OptionCombobox, self).__init__(
            appkey,
            section,
            default,
            options=options,
            label=label,
            caption=caption,
            tooltip=tooltip,
            maxlength=maxlength)

        self.items = []
        if items:
            for i in items:
                if isinstance(i, basestring):
                    self.items.append(i)
                else:
                    self.items.append(str(i))

class OptionPath(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, maxlength=None):
        super(OptionPath, self).__init__(appkey, section, default, initype=path, options=options)

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

class OptionUrl(OptionString):
    @property
    def templateName(self):
        # currently, url uses the same template as string
        return "OptionString"

class OptionNumber(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, minvalue=None, maxvalue=None):
        super(OptionNumber, self).__init__(appkey, section, default, initype=int, options=None)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.minvalue = minvalue
        self.maxvalue = maxvalue

class OptionPercent(OptionNumber):
    pass

class OptionBool(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, alignleft=False):
        super(OptionBool, self).__init__(appkey, section, default, initype=boolext, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        # TODO : implement in template
        self.alignleft = alignleft

    def uiValue2DataValue(self, value):
        # override
        if value == '1':
            return True
        if value == '0':
            return False
        raise ValueError('Unexpected bool value accepted: {0}'.format(value))

# TODO : think about inheritance from Block
class OptionSwitch(OptionBool):
    """ Option, which includes switcher and suboptions

    This is **enabler**, or **switch** option. Its own value is `bool`, and when it is checked -
    the set of suboptions is visible for editing. When its own value is `False` - nothing happens,
    no additional settings are visible
    """
    pass

class OptionCheckboxList(OptionBase):
    class Item:
        """ Internal class, defining one item of CheckBoxList """
        def __init__(self, value, label=""):
            self.value = value
            self.label = label

            self.uniq = None
            self.checked_callback = None

        @property
        def checked(self):
            return self.checked_callback(self.value)

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, alignleft=False, itemtype=str, items=None):
        super(OptionCheckboxList, self).__init__(appkey, section, default, initype=list, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip
        self._itemtype = itemtype

        # TODO : implement in template
        self.alignleft = alignleft

        self.items = []
        counter = 0
        if items:
            for i in items:
                counter += 1
                if isinstance(i, OptionCheckboxList.Item):
                    ii = i
                elif isinstance(i, (tuple, list)):
                    ii = OptionCheckboxList.Item(*i)
                elif isinstance(i, dict):
                    ii = OptionCheckboxList.Item(**i)
                else:
                    raise TypeError('Unexpected type of item {0} in items: {1}'.format(counter, type(i)))

                # COMMON stuff:
                ii.unique = counter - 1 * 100000 + random.randint(1000, 9999)
                ii.checked_callback = self._checked_cb
                self.items.append(ii)

    def _checked_cb(self, value):
        if value in set(self.model.get()):
            return True
        return False

    def uiValue2DataValue(self, value):
        # override

        #logger.debug('VALUE accepted: ({1}) {0}'.format(value, type(value)))
        ret = None

        # what is going on:
        # there is input-hidden on the template. And it is posted always with ''-value.
        # so, when we receive just ONE item - it is our fictive input-hidden, and when
        # we got the list - then we should parse all values, excepting the first (hidden)
        if isinstance(value, list):
            print 'list'
            ret = map(self._itemtype, value[1:])
        else:
            print 'not list'
            ret = []
        #logger.debug('VALUE converted: ({1}) {0}'.format(ret, type(ret)))
        return ret

# TODO : remove this class... It is a crutch
class OptionCheckboxListExtrasCrutch(OptionCheckboxList):
    """ The same as parent, but uses STRING-type for internal value """
    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, alignleft=False, items=None):
        super(OptionCheckboxListExtrasCrutch, self).__init__(appkey, section, default,
            label=label,
            caption=caption,
            tooltip=tooltip,
            options=options,
            alignleft=alignleft,
            items=items
        )
        super(OptionCheckboxList, self).__init__(appkey, section, default, initype=str, options=options)

    def _checked_cb(self, value):
        asstr = self.model.get()
        aslist = asstr.split(',') if asstr else []
        if value in set(aslist):
            return True
        return False

    def uiValue2DataValue(self, value):
        # override

        #logger.debug('VALUE accepted: ({1}) {0}'.format(value, type(value)))

        ret = super(OptionCheckboxListExtrasCrutch, self).uiValue2DataValue(value)

        if ret:
            ret = ",".join(ret)
        else:
            ret = ""

        #logger.debug('VALUE converted: ({1}) {0}'.format(ret, type(ret)))
        return ret

    @property
    def templateName(self):
        # override
        return "OptionCheckboxList"

class OptionDropdown(OptionBase):
    class Item:
        def __init__(self, value, label=""):
            self.value = value
            self.label = label

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, initype=str, items=None):
        super(OptionDropdown, self).__init__(appkey, section, default, initype=initype, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self._uitype = initype

        self.items = []
        counter = 0
        if items:
            for i in items:
                counter += 1
                if isinstance(i, OptionDropdown.Item):
                    ii = i
                elif isinstance(i, (tuple, list)):
                    ii = OptionDropdown.Item(*i)
                elif isinstance(i, dict):
                    ii = OptionDropdown.Item(**i)
                else:
                    raise TypeError('Unexpected type of item {0} in items: {1}'.format(counter, type(i)))

                self.items.append(ii)

    def uiValue2DataValue(self, value):
        # override
        return self._uitype(value)

class OptionDropdownSelector(OptionDropdown):
    """ Dropbox-selector. On change selected item - appears appropriate block of sub-options

    Used as root selector for compound options."""

    class Item:
        """ INTERNAL class, represents one option in options list """

        def __init__(self, value, label, options=None):
            self.value = value
            self.label = label
            self.options = options or []
            self.uniq = None

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, initype=str, items=None):
        super(OptionDropdownSelector, self).__init__(
                appkey,
                section,
                default,

                label=label,
                caption=caption,
                tooltip=tooltip,

                initype=initype,
                options=options,
                items=None # we will handle items in custom manner
        )

        # just one difference (from parent) - items handling
        self.items = []
        counter = 0
        if items:
            for i in items:
                counter += 1

                if isinstance(i, OptionDropdownSelector.Item):
                    ii = i
                elif isinstance(i, (tuple, list)):
                    ii = OptionDropdownSelector.Item(*i)
                elif isinstance(i, dict):
                    ii = OptionDropdownSelector.Item(**i)
                else:
                    raise TypeError('Unexpected type of item {0} in items: {1}'.format(counter, type(i)))

                ii.uniq = counter
                self.items.append(ii)

class OptionList(OptionBase):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None):
        super(OptionList, self).__init__(appkey, section, default, initype=list, options=None)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = None

    @property
    def templateName(self):
        return "OptionString"

    def uiValue2DataValue(self, value):
        # override
        return [value]


# ===============================================
# PLACEHOLDERS and STATIC templates
# ===============================================

class LabelExtension(Renderable):
    """ Render simple text on the same level, as other options """

    def __init__(self, label=None, cssclasses=None, fullwidth=False):
        super(LabelExtension, self).__init__()
        self.label = label
        self.fullwidth = fullwidth
        if cssclasses:
            if not isinstance(cssclasses, (tuple, list)):
                logger.error('LabelExtension argument "cssclasses" should be an array. Will str() it.')
                cssclasses = [str(cssclasses)]
        self.cssclasses = cssclasses or []

    def render(self, parent=None):
        return super(LabelExtension, self).render(me=self, parent=parent)

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
        for (k, v) in d.items():
            if k not in self._vault:
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
