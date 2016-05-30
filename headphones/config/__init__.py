import itertools

import os
import re
from configobj import ConfigObj
from loc import _

from _viewmodel import Tab, Tabs, OptionBase

from _viewparser import ViewParser

from headphones.config.definitions.internal import reg as reg_internal
from headphones.config.definitions.webui import reg as reg_webui
from headphones.config.definitions.download import reg as reg_download
from headphones.config.definitions.search import reg as reg_search
from headphones.config.definitions.quality import reg as reg_quality
from headphones.config.definitions.notifications import reg as reg_notifications
from headphones.config.definitions.advanced import reg as reg_advanced

from _meta import MetaConfig

from headphones.exceptions import ConfigError
from headphones import logger

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

        # used in opt-register , it helps to make the names of sections correct
        self._section_name_spell_check_dic = {}

        self._options = {}
        self._uiparser = ViewParser()

        # -------------------------------------------------------------
        # register options from definition's files:
        # -------------------------------------------------------------
        self._initOptions()

        logger.info('All options registered. Total options: {0}'.format(len(self._options)))

        self._upgrade()

    def getViewModel(self):
        return self._tabs

    def _initOptions(self):

        # Internal options will exist out of the tabs:
        self._extend(*reg_internal(self._extend))

        self._tabs = Tabs(tabs=[
            Tab('webui', _("Web Interface"), savecaption=_("Save Changes"),
                message=_('<i class="fa fa-info-circle"></i> Web Interface changes require a'
                          ' restart to take effect. Saving settings will restart intervals'
                          ' if changed.'),
                options=self._extend(*reg_webui(self._extend))
                ),
            Tab('download', _("Download settings"), savecaption=_("Save Changes"),
                options=self._extend(*reg_download(self._extend))
                ),
            Tab('search', _("Search Providers"), savecaption=_("Save Changes"),
                options=self._extend(*reg_search(self._extend))
                ),
            Tab('quality_processing', _("Quality &amp; Post Processing"),
                savecaption=_("Save Changes"),
                options=self._extend(*reg_quality(self._extend))
                ),
            Tab('notifications', _("Notifications"), savecaption=_("Save Changes"),
                options=self._extend(*reg_notifications(self._extend))
                ),
            Tab('advanced', _("Advanced Settings"), savecaption=_("Save Changes"),
                options=self._extend(*reg_advanced(self._extend))
                ),
        ])

    def _checkSectionName(self, section_name, appkey):
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
                                .format(section_name, appkey, sec))
            else:
                self._section_name_spell_check_dic[lc_section] = section_name

    # TODO : refactor
    def _extend(self, *options):
        """ Extends configuration with new options

        This is the cornerstone of tuning routes for saving and loading config values between app-core,
        UI and INI-file.
        We will link together:
            1. names of options from INI file
            2. names of options in the web UI
            3. datamodels (they store runtime values of each option)
            4. viewmodels (they know, how to render option, and how to handle value from UI)

        Each option will be registered:
            1. in `self._options` - it is a map {OPTKEY -> datamodel},
            2. and in the `self._uiparser`, which stores mapping {UINAME -> viewmodel}.
        """

        for o in options:
            if isinstance(o, OptionBase):
                #logger.debug('config:Option registered: {0}'.format(str(o)))

                if o.appkey in self._options:
                    raise ConfigError('Duplicate option:', o.appkey)

                self._checkSectionName(o.model.section, o.model.appkey)

                # register INI
                o.model.bindToConfig(lambda: self._config)
                self._options[o.appkey] = o.model

                # register UI
                self._uiparser.register(o)

                # set meta options:
                self._meta_config.apply(o)

                logger.debug('config:option registered: {0}'.format(o.appkey))
            else:
                logger.debug('config:non-option skip register: {0}'.format(str(o)))
        return options

    def accept(self, uidata):
        """ Not the best name for the method, which accepts data from UI, and apply them to running config """
        self._uiparser.accept(uidata)

    def write(self):
        """ Make a copy of the stored config and write it to the configured file """

        logger.debug("Writing configuration to file")
        try:
            self._config.write()
            logger.info("Writing configuration to file: DONE")
        except IOError as e:
            logger.error("Error writing configuration file: %s", e)

    def get_extra_newznabs(self):
        """ Return the extra newznab tuples """
        logger.debug("DEPRECATED: config.get_extra_newznabs")

        extra_newznabs = list(
            itertools.izip(*[itertools.islice(self.EXTRA_NEWZNABS, i, None, 3)
                             for i in range(3)])
        )
        return extra_newznabs


    # OBSOLETE
    # TODO: remove this method and all references!
    def get_extra_torznabs(self):
        """ Return the extra torznab tuples """
        logger.debug("DEPRECATED: config.get_extra_torznabs")

        extra_torznabs = list(
            itertools.izip(*[itertools.islice(self.EXTRA_TORZNABS, i, None, 3)
                             for i in range(3)])
        )
        return extra_torznabs

    def __getattr__(self, name):
        """
        Returns something from the ini unless it is a real property
        of the configuration object or is not all caps.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__getattr__(name)
        else:
            # return self.check_setting(name)
            return self._options[name].get()

    def __setattr__(self, name, value):
        """
        Maps all-caps properties to ini values unless they exist on the
        configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            super(Config, self).__setattr__(name, value)
            return value
        else:
            m = self._options[name]
            m.set(value)
            return m.get()

    def _upgrade(self):
        """ Update folder formats in the config & bump up config version """
        if str(self.CONFIG_VERSION) == '0':
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

            self.CONFIG_VERSION = 1

        if str(self.CONFIG_VERSION) == '1':
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
            self.CONFIG_VERSION = 2

        if str(self.CONFIG_VERSION) == '2':
            # Update the config to use direct path to the encoder rather than the encoder folder
            if self.ENCODERFOLDER:
                self.ENCODER_PATH = os.path.join(self.ENCODERFOLDER, self.ENCODER)
            self.CONFIG_VERSION = 3

        if str(self.CONFIG_VERSION) == '3':
            # Update the BLACKHOLE option to the NZB_DOWNLOADER format
            if self.BLACKHOLE:
                self.NZB_DOWNLOADER = 2
            self.CONFIG_VERSION = 4

        # Enable Headphones Indexer if they have a VIP account
        if str(self.CONFIG_VERSION) == '4':
            if self.HPUSER and self.HPPASS:
                self.HEADPHONES_INDEXER = True
            self.CONFIG_VERSION = 5

        if str(self.CONFIG_VERSION) == '5':
            if self.OPEN_MAGNET_LINKS:
                self.MAGNET_LINKS = 2
            self.CONFIG_VERSION = 6

        # HERE and further use INT values to determine version
        # of the config file, no more strings here!
        if self.CONFIG_VERSION == 6:
            self.CONFIG_VERSION = 7
