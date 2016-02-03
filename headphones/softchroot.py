import os
from headphones.exceptions import SoftChrootError

class SoftChroot(object):
    def __init__(self, path):
        path = path.strip()

        if (not os.path.exists(path) or
                not os.path.isdir(path)):
            raise SoftChrootError('No such directory: %s' % path)

        path = path.strip(os.path.sep) + os.path.sep

        self.chroot = path
