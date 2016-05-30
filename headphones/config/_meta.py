import re
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
            t = self._parseMetaTokenValue(mo)

            if not t:
                logger.warn('Syntax error in meta-option definition, [{0}][{1}] = [{2}]'.format(s, k, mo))
            elif t['name'] in ['ro', 'readonly']:
                option.readonly = True
            elif t['name'] in ['rw']:
                option.readonly = False

            elif t['name'] in ['visible', 'show']:
                option.visible = True
            elif t['name'] in ['invisible', 'hide', 'hidden']:
                option.visible = False
            elif t['name'] in ['items-allow']:
                if option._items:
                    for ii in option._items:
                        if hasattr(ii, 'value'):
                            if str(ii.value) in t['params']:
                                ii.visible = True
                            else:
                                ii.visible = False

            else:
                logger.warn('Unknown value of meta [{0}] for option [{1}][{2}]'.format(t['name'], s, k))

    def _parseMetaTokenValue(self, value):

        if not value:
            logger.warn('config.meta.parse.token: empty value')
            return None

        r = re.compile('(?P<name>[-\w]+)\s*(?:\((?P<params>[-;\w\d\s]+)\))?')
        m = r.match(value)

        if not m:
            logger.warn('config.meta.parse.token: raw-value has syntax error')
            return None

        t = {}
        t['name'] = m.groupdict()['name']
        params = m.groupdict()['params']
        if params:
            params = params.split(';')
            params = map(lambda x: x.strip(), params)
        else:
            params = []
        t['params'] = params

        logger.debug('config.meta.parse.token parsed token: {0}'.format(t))

        return t
