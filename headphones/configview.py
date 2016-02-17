import re
from itertools import ifilter
#from headphones import logger

""" Structures and classes for UI-related part of configuration """

# translation


def _(x):
    return x

class Tabs(object):
    """ This class required just to separate UI logic out of headphones.config """

    def __init__(self, *args):
        self.tabs = list(*args)
        pass

    def __iter__(self):
        """ Default iterator is comfortable for UI tasks """

        return self.iterate_ui()

    def iterate_ui(self):
        """ Iterates over non-empty tabs """
        return ifilter(lambda t: True, self.tabs)    

    def __repr__(self):
        return "<%s with %d tabs>" % (
            self.__class__.__name__,
            len(self.tabs)
        )
    pass

class Tab(object):
    """ UI-tab for grouping option on a page """

    def __init__(self, id, caption=None, cssclass=None):

        self._map = {}
        self._index = []

        self.id = re.sub(r'[^\w\d_]', '_', id)
        self.caption = caption
        self.cssclass = cssclass
        self.__setitem__ = None

    # itertools:
    def __getitem__(self, *args, **qw):
        return self._map.__getitem__(*args, **qw)

    def __repr__(self):
        return "<%s id='%s', caption='%s', with %d blocks>" % (
            self.__class__.__name__,
            self.id,
            self.caption,
            len(self._map)
        )

    def iblocks(self):
        return self.iterate_ui()

    def iterate_ui(self):
        """ Iterates over non-empty tabs """
        return ifilter(lambda t: True, self._index)       

    def add(self, blocks_list):
        """ add settings block to current tab """
        if blocks_list:
            for block in blocks_list:
                if not isinstance(block, Block):
                    continue

            bid = block.id
            if bid in self._map:
                # extend
                pass
            else:
                # append
                self._map[bid] = block
                self._index.append(block)

        self._index.sort(key=lambda a: a.order)
    pass

class Block(object):
    """ UI-block for grouping options within `Tab` """

    def __init__(self, id, order=100, caption=None, cssclass=None, options=[]):
        self.id = re.sub(r'[^\w\d_]', '_', id)
        self.caption = caption
        self._options = options or []  # should not be None
        self.cssclass = cssclass
        self.order = order

    def __repr__(self):
        return "<%s id=%s, caption=%s, with %d options>" % (
            self.__class__.__name__,
            self.id,
            self.caption,
            len(self._options)
        )
    
    def ioptions(self):
        return self.iterate_ui()

    def iterate_ui(self):
        """ Iterates over non-empty tabs """
        return ifilter(lambda t: True, self._options)     

    pass
