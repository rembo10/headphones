from headphones import logger
from headphones.exceptions import ConfigError

from _viewmodel import OptionBase

""" Parser for ViewModel data

This module is closely related with `_viewmodel`, and helps to parse submited data,
from UI
"""


class ViewParser(object):
    """
    Knows how to parse options, POSTed from UI. Closely related with `OptionBase`
    """

    def __init__(self):
        self._vault = {}

    def register(self, option):
        if not isinstance(option, OptionBase):
            raise TypeError('Could not register this option, because it '
                            'should be child of {0}.{1}'.format(OptionBase.__module__, OptionBase.__name__))

        for k in option.uiNamesList():
            if k in self._vault:
                raise ConfigError('Duplicate ui-key [{0}] for option [{1}]'.format(k, option.appkey))

            self._vault[k] = option

    def accept(self, values_as_dict):
        """ Accepts data from UI, and apply it to the options """
        if not isinstance(values_as_dict, dict):
            raise TypeError('dict expected')

        aggregated = {}
        optmap = {}

        # First loop. Aggregate POST data by options:
        # one bunch of posted values per option
        for (k, v) in values_as_dict.items():
            if k not in self._vault:
                logger.debug('This form-key [{0}] is unknown for config, skip'.format(k))
                continue

            opt = self._vault[k]
            ak = opt.appkey

            if opt.readonly:
                logger.info('This option [{0}][{1}] is readonly, but it was submited. Contact the'
                            ' maintainers of `config` package! SKIP'
                            .format(opt.model.section, ak)
                            )
                continue

            if ak not in aggregated:
                aggregated[ak] = {}

            aggregated[ak][k] = v
            optmap[ak] = opt

        # Second loop. Apply aggregated options
        diffcount = 0
        for (ak, opt) in optmap.items():

            v = aggregated[ak]

            # new value
            nv = opt.uiValue2DataValue(v)
            # old value
            ov = opt.model.get()

            if ov != nv:
                opt.model.set(nv)
                logger.info('The value of [{0}][{1}] changed [{2}] => [{3}]'.format(opt.model.section, opt.appkey, ov, nv))
                diffcount += 1

        # DONE
        return diffcount
