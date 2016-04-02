import re
import os
import random
from itertools import ifilter, imap
from mako.lookup import TemplateLookup

import headphones
from headphones import logger
from headphones.exceptions import ConfigError

from headphones.config.typeconv import path, boolext, intnullable, floatnullable
from _datamodel import OptionModel

""" ViewModel-classes of configuration

Some of classes still just ViewModels, without its own template (for example : Tabs)
But the most classes have its own template (they are inherited from Renderable)
"""

# ===============================================
# Internal helpers
# ===============================================

# TODO : convert to base/abstract class


def _get_iterator_over_visible(items):
    return ifilter(lambda t: not hasattr(t, 'visible') or t.visible, items)

# ===============================================
# Abstract, base class
# ===============================================


class CssClassable(object):

    def __init__(self):
        self._cssclasses = []

    @property
    def cssclasses(self):
        return self._cssclasses

    @cssclasses.setter
    def cssclasses(self, value):
        if not value:
            self._cssclasses = []
        elif isinstance(value, (tuple, list)):
            self._cssclasses = map(str, value)
        elif isinstance(value, basestring):
            self._cssclasses = [value]
        else:
            raise TypeError('Unexpected type of "cssclasses": {0}'.format(type(value)))
        return

    def uiCssClasses(self):
        if self.cssclasses:
            return ' '.join(self.cssclasses)
        return ''


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
# Tabs, Tab classes are defined here.
# Their templates are used just once, and, as
# a consequence, are embed to the main template -
# - config.html
# ===============================================


class Tabs(object):
    """ ViewModel for entire TABS element. Contains all the tabs """

    def __init__(self, tabs=None):
        self.tabs = list(tabs)

    def __repr__(self):
        return "<%s with %d tabs>" % (
            self.__class__.__name__,
            len(self.tabs)
        )

    def __iter__(self):
        """ Default iterator is sharpened for UI tasks """

        return _get_iterator_over_visible(self.tabs)


class Tab(Renderable, CssClassable):
    """ UI-tab for grouping option on a UI-page """

    def __init__(self, id, caption=None, cssclasses=None, message=None, savecaption=None, options=None):
        super(Tab, self).__init__()

        self._map = {}
        self._index = []
        self._sorted = True
        self.__setitem__ = None
        self._id = re.sub(r'[^\w\d_]', '_', id)

        self.caption = caption
        self.message = message
        self.savecaption = savecaption
        self.cssclasses = cssclasses

        if options:
            for i in options:
                self.add(i)

    def __repr__(self):
        return "<%s id='%s', with %d blocks>" % (
            self.__class__.__name__,
            self.id,
            len(self._map)
        )

    # itertools:
    def __getitem__(self, *args, **qw):
        return self._map.__getitem__(*args, **qw)

    def __iter__(self):
        """ Iterates over non-empty tabs """

        self._sort()

        # TODO : omit empty blocks
        return imap(lambda x: x[1], _get_iterator_over_visible(self._index))

    def _print_content(self):
        self._sort()
        for i in self._items:
            logger.debug('tab [{2}] item, order:[{0}], item: [{1}]'.format(i[0], type(i[1]), self.id))

    def _sort(self):
        if not self._sorted:
            self._index.sort(key=lambda a: a[0])
            self._sorted = True

    @property
    def id(self):
        return self._id

    def add(self, item, order=None):
        """ add one item to current tab """

        if not isinstance(item, Renderable):
            raise TypeError('Tab: item [{0}] is not Renderable child'.format(type(item)))

        if hasattr(item, 'id'):
            bid = item.id
        elif hasattr(item, 'appkey'):
            bid = item.appkey
        else:
            ll = len(self._index)
            bid = 'item' + str(ll)

        if bid in self._map:
            # extend
            raise ConfigError('Duplicate item')
        else:
            # append
            self._sorted = False
            self._map[bid] = item
            self._index.append(tuple([order, item]))

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

        self._uinames = ['hp_ui_' + self.model.appkey.lower()]

        self.visible = True
        self.readonly = False

    def __repr__(self):
        return "<{0} appkey={1}>".format(
            self.__class__.__name__,
            self.model.appkey
        )

    def __iter__(self):
        """ Iterates over visible suboptions """
        return _get_iterator_over_visible(self._options)

    def __len__(self):
        return len(self._options)

    def render(self, parent=None):
        return super(OptionBase, self).render(me=self, parent=parent)

    @property
    def appkey(self):
        return self.model.appkey

    @property
    def value(self):
        """ raw, runtime value of the option """
        return self.model.get()

    def uiValue(self):
        """ UI-friendly value of the option """
        v = self.model.get()
        if v is None:
            v = ''
        return v

    def uiValue2DataValue(self, valuedict):
        """
        Parses the value of an options, received from UI.
        Returned value MUST BE compatible with datamodel's value

        Args:

            @valuedict
                dict. Keys are from self.uiNamesList(), values - from submitted form (from UI).

        """
        value = valuedict[self.uiName()]
        return self._initype(value)

    def uiName(self):
        """This is a main identifier of the option in the UI.

        This identifier will be used:
        1. for generating identifiers (and names) for UI-input-elements
        2. for handling results, received from UI (on submit form)

        Also, extended options, with more than one input box (like `OptionExtra`), uses this
        method during generating names for child-options.
        """
        return self._uinames[0]

    def uiNamesList(self):
        """ MUST return list with all NAMEs, used in UI """
        return self._uinames

# ===============================================
# API-usable options
# ===============================================


class OptionInternal(OptionBase):
    """ This option will not appear in the UI. It is internal stuff"""

    def __init__(self, appkey, section, default=None, initype=str):
        super(OptionInternal, self).__init__(appkey, section, default, initype=initype)

        self.readonly = False
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


class OptionString(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None, maxlength=None):
        super(OptionString, self).__init__(appkey, section, default, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength

        self.cssclasses = cssclasses


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


class OptionPath(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None, maxlength=None):
        super(OptionPath, self).__init__(appkey, section, default, initype=path, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.maxlength = maxlength
        self.cssclasses = cssclasses

    @property
    def templateName(self):
        # currently, path uses the same template as string
        return "OptionString"

    def uiValue(self):
        # override
        v = self.model.get()

        # TODO : this is not the best way to implement SoftChroot
        # reimplement please WITHOUT IMPORT
        import headphones
        v = headphones.SOFT_CHROOT.apply(v)

        return v

    def uiValue2DataValue(self, valuedict):
        # override
        value = valuedict[self.uiName()]

        v = self._initype(value)

        # TODO : this is not the best way to implement SoftChroot
        # reimplement please WITHOUT IMPORT
        import headphones
        v = headphones.SOFT_CHROOT.revoke(v)

        return v


class OptionPassword(OptionString):
    pass


class OptionUrl(OptionString):

    @property
    def templateName(self):
        # currently, url uses the same template as string
        return "OptionString"


class OptionEmail(OptionString):

    @property
    def templateName(self):
        # currently, url uses the same template as string
        return "OptionString"


class OptionNumber(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None, minvalue=None, maxvalue=None):
        super(OptionNumber, self).__init__(appkey, section, default, initype=intnullable, options=None)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.cssclasses = cssclasses

        self.minvalue = minvalue
        self.maxvalue = maxvalue


class OptionPercent(OptionNumber):
    pass


class OptionFloat(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None, minvalue=None, maxvalue=None):
        super(OptionFloat, self).__init__(appkey, section, default, initype=floatnullable, options=None)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        self.cssclasses = cssclasses

        self.minvalue = minvalue
        self.maxvalue = maxvalue

    @property
    def templateName(self):
        # float uses the same template as number
        return "OptionNumber"


class OptionBool(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None, alignleft=False):
        super(OptionBool, self).__init__(appkey, section, default, initype=boolext, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip

        # DONE : implement in template
        self.alignleft = alignleft
        self.cssclasses = cssclasses

    def uiValue2DataValue(self, valuedict):
        # override
        value = valuedict[self.uiName()]

        if value:
            value = str(value).strip()

        if value == '1':
            return True
        if value == '0':
            return False
        raise ValueError('Unexpected value accepted: {0}. Expected "1" or "0"'.format(value))

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

        def __init__(self, value, label="", csssuffix=None):
            self.value = value
            self.label = label

            self.csssuffix = csssuffix
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

        # DONE : implement in template
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
                if ii.csssuffix is None:
                    ii.csssuffix = str(counter - 1 * 100000 + random.randint(1000, 9999))

                ii.checked_callback = self._checked_cb
                self.items.append(ii)

    def _checked_cb(self, value):
        if value in set(self.model.get()):
            return True
        return False

    def uiValue2DataValue(self, valuedict):
        # override
        value = valuedict[self.uiName()]

        # logger.debug('VALUE accepted: ({1}) {0}'.format(value, type(value)))
        ret = None

        # what is going on:
        # there is input-hidden on the template. And it is posted always with ''-value.
        # so, when we receive just ONE item - it is our fictive input-hidden, and when
        # we got the list - then we should parse all values, excepting the first (hidden)
        if isinstance(value, list):
            ret = map(self._itemtype, value[1:])
        else:
            ret = []
        # logger.debug('VALUE converted: ({1}) {0}'.format(ret, type(ret)))
        return ret


class OptionCheckboxListExtrasCrutch(OptionCheckboxList):
    """ The same as parent, but uses STRING-type for internal value

    TODO : remove this class... It is a crutch
    """

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

    def uiValue2DataValue(self, valuedict):
        # override

        # logger.debug('VALUE accepted: ({1}) {0}'.format(value, type(value)))

        ret = super(OptionCheckboxListExtrasCrutch, self).uiValue2DataValue(valuedict)

        if ret:
            ret = ",".join(ret)
        else:
            ret = ""

        # logger.debug('VALUE converted: ({1}) {0}'.format(ret, type(ret)))
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

    def uiValue2DataValue(self, valuedict):
        # override
        value = valuedict[self.uiName()]
        return self._uitype(value)


class OptionDropdownSelector(OptionDropdown):
    """ Dropbox-selector. On change selected item - appears appropriate block of sub-options

    Used as root selector for compound options."""

    class Item(object):
        """ INTERNAL class, represents one option in options list """

        def __init__(self, value, label, options=None, csssuffix=None):
            self.value = value
            self.label = label
            self.csssuffix = csssuffix
            self._options = options or []
            self.csssuffix = csssuffix
            self._section_visible_cb = None

        def __iter__(self):
            return _get_iterator_over_visible(self._options)

        def __len__(self):
            return len(self._options)

        def isSelectorSectionVisible(self):
            if not self._section_visible_cb:
                logger.warn('Misconfigured option. You could\'t fix it, a hand of'
                            ' a developer is required. Label of option [{0}]'.format(self.label))
                return False
            return self._section_visible_cb(self.csssuffix)

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
            items=None  # we will handle items in custom manner
        )

        # just one difference (from parent) - items handling
        self.items = []
        self.value2csssuffix = {}

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

                if ii.csssuffix is None:
                    ii.csssuffix = str(counter)

                self.value2csssuffix[ii.value] = ii.csssuffix
                ii._section_visible_cb = self._item_section_visible

                self.items.append(ii)

    def _item_section_visible(self, csssuffix):
        val = self.model.get()
        if val not in self.value2csssuffix:
            return False
        css = self.value2csssuffix[val]
        return css == csssuffix


class OptionExtra(OptionBase, CssClassable):

    def __init__(self, appkey, section, default=None, label="", caption=None, tooltip=None, options=None, cssclasses=None,
        labelhost=None,
        labelapikey=None,
        labelenabled=None,

        captionadd=None,
        captionremove=None,
    ):
        super(OptionExtra, self).__init__(appkey, section, default, initype=list, options=options)

        self.label = label
        self.caption = caption
        self.tooltip = tooltip
        self.cssclasses = cssclasses

        self.labelHost = labelhost
        self.labelApiKey = labelapikey
        self.labelEnabled = labelenabled

        self.captionHost = None
        self.captionApiKey = None
        self.captionEnabled = None

        self.captionAddButton = captionadd
        self.captionDelButton = captionremove

        uinm = self.uiName();
        self._uinames = [uinm,
            uinm + '_host[]',
            uinm + '_apikey[]',
            uinm + '_enabled[]',
        ]

    def uiValue(self):
        # override

        v = super(OptionExtra, self).uiValue()

        i = 0
        d = []
        if v:
            ll = len(v)
            while i+2<ll:
                h = str(v[i])
                a = str(v[i+1])
                e = boolext(v[i+2])

                d.append({"host":h, "apikey":a, "enabled": e})
                i += 3

        # d:
        # [{"host": "http://snab.ru", "apikey": "yyyy", "enabled": true}, {"host": "http://ya.ru", "apikey": "xxx", "enabled": true}]
        return d

    def uiValue2DataValue(self, valuedict):
        # override
        uinm = self.uiName();
        keyhost = uinm + '_host[]'
        keyapi = uinm + '_apikey[]'
        keyenabled = uinm + '_enabled[]'

        res = []
        ll = len(valuedict[keyhost])
        for i in xrange(ll):
            hst = str(valuedict[keyhost][i])
            api = str(valuedict[keyapi][i])
            enb = boolext(valuedict[keyenabled][i])

            res.append(hst)
            res.append(api)
            res.append(enb)

        return res

# ===============================================
# PLACEHOLDERS and STATIC templates
# ===============================================


class BlockExtension(Renderable, CssClassable):
    """ UI-block for grouping options within `Tab` """

    def __init__(self, id, caption=None, cssclasses=None, options=None):
        super(BlockExtension, self).__init__()

        self._id = id
        self.caption = caption
        self._options = options or []  # should not be None
        self.cssclasses = cssclasses

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return "<%s id=%s, with %d options>" % (
            self.__class__.__name__,
            self.id,
            len(self._options)
        )

    def __iter__(self):
        """ Iterates over non-empty tabs """
        # TODO : omit invisible options blocks
        return _get_iterator_over_visible(self._options)

    def render(self, parent=None):
        return super(BlockExtension, self).render(me=self, parent=parent)


class MessageExtension(Renderable, CssClassable):
    """ Render message on the same level, as other options """

    def __init__(self, message=None, icon=None, cssclasses=None, fullwidth=False):
        super(MessageExtension, self).__init__()
        self.message = message
        self.icon = icon
        self.fullwidth = fullwidth
        self.cssclasses = cssclasses

    def render(self, parent=None):
        return super(MessageExtension, self).render(me=self, parent=parent)

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
