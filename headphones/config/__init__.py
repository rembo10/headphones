import itertools

import os
import re
from configobj import ConfigObj

from _viewmodel import Tab, Tabs, OptionBase

from _viewmodel import PostDataParser

import headphones.config.definitions.webui
import headphones.config.definitions.download
import headphones.config.definitions.search
import headphones.config.definitions.internal
import headphones.config.definitions.advanced

from _meta import MetaConfig

from headphones.exceptions import ConfigError
from headphones import logger

def _(x):
    """ required just for marking translatable strings"""
    return x

# pylint:disable=R0902
# it might be nice to refactor for fewer instance variables
class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file):

        """ Initialize the config with values from a file """
        self._config_file = config_file
        self._config = ConfigObj(self._config_file, encoding='utf-8')

        # meta config preparation
        (_basename, _ext) = os.path.splitext(self._config_file)
        meta_config_name = _basename + '.meta' + _ext
        logger.debug('Read meta config from: [{0}]'.format(meta_config_name))
        self._meta_config = MetaConfig(meta_config_name)

        self._initTabs()

        # used in opt-register , it helps to make the names of sections correct
        self._section_name_spell_check_dic = {}

        self._vault = {}
        self._uiresolver = PostDataParser()

        # register options from definition's files:
        definitions.internal.reg(None, self._registerBlock, self._registerOptions)
        definitions.webui.reg('webui', self._registerBlock, self._registerOptions)
        definitions.download.reg('download', self._registerBlock, self._registerOptions)
        definitions.search.reg('search', self._registerBlock, self._registerOptions)
        definitions.advanced.reg('advanced', self._registerBlock, self._registerOptions)

        logger.debug('All options registered. Total options: {0}'.format(len(self._vault)))

        self._upgrade()

    # def _define(self, name):
    #     key = name.upper()
    #     ini_key = name.lower()
    #     definition = _CONFIG_DEFINITIONS[key]
    #     if len(definition) == 3:
    #         definition_type, section, default = definition
    #     elif len(definition) == 4:
    #         definition_type, section, _, default = definition
    #     return key, definition_type, section, ini_key, default

    # def _check_section(self, section):
    #     """ Check if INI section exists, if not create it """
    #     if section not in self._config:
    #         self._config[section] = {}
    #         return True
    #     else:
    #         return False

    # def check_setting(self, key):
    #     """ Cast any value in the config to the right type or use the default """
    #     key, definition_type, section, ini_key, default = self._define(key)
    #     self.check_section(section)
    #     try:
    #         my_val = definition_type(self._config[section][ini_key])
    #     except Exception:
    #         my_val = definition_type(default)
    #         self._config[section][ini_key] = my_val
    #     return my_val


    def getViewModel(self):
        return self._tabs

    def _initTabs(self):
        self._tabs = Tabs((
                Tab('webui', _("Web Interface"), savecaption=_("Save Changes"),
                    message=_( ('<i class="fa fa-info-circle"></i> Web Interface changes require a restart to take effect.'
                                'Saving settings will restart intervals if changed.'))
                ),
                Tab('download', _("Download settings"), savecaption=_("Save Changes")),
                Tab('search', _("Search providers"), savecaption=_("Save Changes")),
                Tab('quality_processing', _("Quality &amp; Post Processing"), savecaption=_("Save Changes")),
                Tab('notifications', _("Notifications"), savecaption=_("Save Changes")),
                Tab('advanced', _("Advanced Settings"), savecaption=_("Save Changes")),
            ))

    # TODO : refactor
    def _registerBlock(self, tabid, *blocks):
        tab = None
        for t in self._tabs:
            if t.id == tabid:
                tab = t
        if not tab:
            raise Exception('no such tab: ' + str(tabid))

        for block in blocks:
            tab.add(block)
            logger.debug('config:Block registered: {0} > {1}'.format(tabid, block.id))

    def _checkSectionName(self, section_name):
        """ Unnecessary method, it does not make any serious job, just make an additional
        check of names of sections in the config-definition
        """
        if section_name:
            lc_section = section_name.lower()
            if lc_section in self._section_name_spell_check_dic:
                sec = self._section_name_spell_check_dic[lc_section]
                if sec != section_name:
                    # different section names!
                    logger.info('Misspelling in section name [{0}] for option [{0}][{1}], expected [{2}]'
                        .format(section_name, o.appkey, sec))
            else:
                self._section_name_spell_check_dic[lc_section] = section_name

    # TODO : refactor
    def _registerOptions(self, *options):
        """ Register option to use as config value

        This is the main part of setting up the routes for config values.
        We will link together:
            1. names of options from INI file
            2. names of options in the web UI
            3. datamodels (they store actual values of each option)
            4. viewmodels (they know, how to render option, and how to handle value from UI)

        Each option will be registered in the _vault - which is a map {OPTKEY -> datamodel}, and in
        the _uiresolver, storing mapping {UINAME -> Option}.
        """

        for o in options:
            if isinstance(o, OptionBase):
                #logger.debug('config:Option registered: {0}'.format(str(o)))

                if o.appkey in self._vault:
                    raise ConfigError('Duplicate option:', o.appkey)

                self._checkSectionName(o.model.section)

                # register INI
                o.model.bindToConfig(lambda:self._config)
                self._vault[o.appkey] = o.model

                # register UI
                self._uiresolver.register(o)

                # set meta options:
                self._meta_config.apply(o)

                logger.debug('config:option registered: {0}'.format(o.appkey))
            else:
                logger.debug('config:non-option skip register: {0}'.format(str(o)))
        return options

    def accept(self, uidata):
        """ Not the best name for the method, which accepts data from UI, and apply them to running config """
        self._uiresolver.accept(uidata)

    def write(self):
        """ Make a copy of the stored config and write it to the configured file """

        # new_config = ConfigObj(encoding="UTF-8")
        # new_config.filename = self._config_file

        # # first copy over everything from the old config, even if it is not
        # # correctly defined to keep from losing data
        # for key, subkeys in self._config.items():
        #     if key not in new_config:
        #         new_config[key] = {}
        #     for subkey, value in subkeys.items():
        #         new_config[key][subkey] = value

        # """
        # # next make sure that everything we expect to have defined is so
        # for key in _CONFIG_DEFINITIONS.keys():
        #     key, definition_type, section, ini_key, default = self._define(key)
        #     self.check_setting(key)
        #     if section not in new_config:
        #         new_config[section] = {}
        #     new_config[section][ini_key] = self._config[section][ini_key]
        # """
        # Write it to file
        headphones.logger.info("Writing configuration to file")

        try:
            # TODO : do not forget to write file!!!!
            # new_config.write()

            # TODO : try to use self._config.write
            self._config.write()
            headphones.logger.info("Writing configuration to file: DONE")
        except IOError as e:
            headphones.logger.error("Error writing configuration file: %s", e)

    def get_extra_newznabs(self):
        """ Return the extra newznab tuples """
        headphones.logger.debug("DEPRECATED: config.get_extra_newznabs")

        extra_newznabs = list(
            itertools.izip(*[itertools.islice(self.EXTRA_NEWZNABS, i, None, 3)
                             for i in range(3)])
        )
        return extra_newznabs

    # def clear_extra_newznabs(self):
    #     """ Forget about the configured extra newznabs """
    #     self.EXTRA_NEWZNABS = []

    # def add_extra_newznab(self, newznab):
    #     """ Add a new extra newznab """
    #     extra_newznabs = self.EXTRA_NEWZNABS
    #     for item in newznab:
    #         extra_newznabs.append(item)
    #     self.EXTRA_NEWZNABS = extra_newznabs

    def get_extra_torznabs(self):
        """ Return the extra torznab tuples """
        headphones.logger.debug("DEPRECATED: config.get_extra_torznabs")

        extra_torznabs = list(
            itertools.izip(*[itertools.islice(self.EXTRA_TORZNABS, i, None, 3)
                             for i in range(3)])
        )
        return extra_torznabs

    # def clear_extra_torznabs(self):
    #     """ Forget about the configured extra torznabs """
    #     self.EXTRA_TORZNABS = []

    # def add_extra_torznab(self, torznab):
    #     """ Add a new extra torznab """
    #     extra_torznabs = self.EXTRA_TORZNABS
    #     for item in torznab:
    #         extra_torznabs.append(item)
    #     self.EXTRA_TORZNABS = extra_torznabs

    def __getattr__(self, name):
        """
        Returns something from the ini unless it is a real property
        of the configuration object or is not all caps.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__getattr__(name)
        else:
            #return self.check_setting(name)
            return self._vault[name].get()

    def __setattr__(self, name, value):
        """
        Maps all-caps properties to ini values unless they exist on the
        configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            super(Config, self).__setattr__(name, value)
            return value
        else:
            m = self._vault[name]
            m.set(value)
            return m.get()
# TODO : remove on finish config-improvements
#            key, definition_type, section, ini_key, default = self._define(name)
#            self._config[section][ini_key] = definition_type(value)
#            return self._config[section][ini_key]

    def _upgrade(self):
        """ Update folder formats in the config & bump up config version """
        if self.CONFIG_VERSION == '0':
            from headphones.helpers import replace_all
            file_values = {
                'tracknumber': 'Track',
                'title': 'Title',
                'artist': 'Artist',
                'album': 'Album',
                'year': 'Year'
            }
            folder_values = {
                'artist': 'Artist',
                'album': 'Album',
                'year': 'Year',
                'releasetype': 'Type',
                'first': 'First',
                'lowerfirst': 'first'
            }
            self.FILE_FORMAT = replace_all(self.FILE_FORMAT, file_values)
            self.FOLDER_FORMAT = replace_all(self.FOLDER_FORMAT, folder_values)

            self.CONFIG_VERSION = '1'

        if self.CONFIG_VERSION == '1':
            from headphones.helpers import replace_all
            file_values = {
                'Track': '$Track',
                'Title': '$Title',
                'Artist': '$Artist',
                'Album': '$Album',
                'Year': '$Year',
                'track': '$track',
                'title': '$title',
                'artist': '$artist',
                'album': '$album',
                'year': '$year'
            }
            folder_values = {
                'Artist': '$Artist',
                'Album': '$Album',
                'Year': '$Year',
                'Type': '$Type',
                'First': '$First',
                'artist': '$artist',
                'album': '$album',
                'year': '$year',
                'type': '$type',
                'first': '$first'
            }
            self.FILE_FORMAT = replace_all(self.FILE_FORMAT, file_values)
            self.FOLDER_FORMAT = replace_all(self.FOLDER_FORMAT, folder_values)
            self.CONFIG_VERSION = '2'

        if self.CONFIG_VERSION == '2':
            # Update the config to use direct path to the encoder rather than the encoder folder
            if self.ENCODERFOLDER:
                self.ENCODER_PATH = os.path.join(self.ENCODERFOLDER, self.ENCODER)
            self.CONFIG_VERSION = '3'

        if self.CONFIG_VERSION == '3':
            # Update the BLACKHOLE option to the NZB_DOWNLOADER format
            if self.BLACKHOLE:
                self.NZB_DOWNLOADER = 2
            self.CONFIG_VERSION = '4'

        # Enable Headphones Indexer if they have a VIP account
        if self.CONFIG_VERSION == '4':
            if self.HPUSER and self.HPPASS:
                self.HEADPHONES_INDEXER = True
            self.CONFIG_VERSION = '5'

        if self.CONFIG_VERSION == '5':
            if self.OPEN_MAGNET_LINKS:
                self.MAGNET_LINKS = 2
            self.CONFIG_VERSION = '5'

