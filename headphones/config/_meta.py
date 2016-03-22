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

        # default meta settings
        option.visible = True
        option.readonly = False

        if (s in self._config) and (k in self._config[s]):
            mode = self._config[s][k]
            self._parseConfigValueAndApply(mode, option, s, k)

    def _parseConfigValueAndApply(self, value, option, s, k):

        if not value:
            return

        if isinstance(value, (list, tuple)):
            tokens = map(str, value)
        else:
            value = str(value)
            tokens = value.split(',')

        tokens = map(lambda x: x.strip(), tokens)
        tokens = map(lambda x: x.lower(), tokens)

        logger.debug('Set up meta for [{0}][{1}] = [{2}]'.format(s, k, ','.join(tokens)))

        for mo in tokens:

            if mo in ['ro', 'readonly']:
                option.readonly = True
            elif mo in ['rw']:
                option.readonly = False

            elif mo in ['visible', 'show']:
                option.visible = True
            elif mo in ['invisible', 'hide', 'hidden']:
                option.visible = False
            else:
                logger.warn('Unknown value of meta [{0}] for option [{1}][{2}]'.format(mo, s, k))
