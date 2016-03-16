from configobj import ConfigObj

from headphones import logger

class MetaConfig(object):
    """ Handles metainformation about options """

    def __init__(self, filename):
        self._filename = filename
        self._config = ConfigObj(self._filename, encoding='utf-8')

    def apply(self, option):
        """ Sets up the appropriate meta-configuration for the option

        Args:
            - self - self
            - option - _viewmodel.BaseOption or its ancestor
        """
        s = option.model.section
        k = option.model.inikey

        if (s in self._config) and (k in self._config[s]):
            mo = self._config[s][k]
            logger.debug('Set up meta for [{0}][{1}] = [{2}]'.format(s, k, mo))
            option.visible = True
            option.readonly = False
        else:
            # default meta settings
            option.visible = True
            option.readonly = False
