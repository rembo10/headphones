import os

from headphones.exceptions import SoftChrootError


class SoftChroot(object):
    """ SoftChroot provides SOFT chrooting for UI

    IMPORTANT: call methods of this class just in modules, which generates data for client UI. Try to avoid unnecessary usage.
    """

    enabled = False
    chroot = None

    def __init__(self, path):
        if not path:
            # disabled
            return

        path = path.strip()
        if not path:
            return

        if (not os.path.exists(path) or
                not os.path.isdir(path)):
            raise SoftChrootError('No such directory: %s' % path)

        path = path.rstrip(os.path.sep) + os.path.sep

        self.enabled = True
        self.chroot = path

    def isEnabled(self):
        return self.enabled

    def getRoot(self):
        return self.chroot

    def apply(self, path):
        if not self.enabled:
            return path

        if not path:
            return path

        p = path.strip()
        if not p:
            return path

        if path.startswith(self.chroot):
            p = os.path.sep + path[len(self.chroot):]
        else:
            p = os.path.sep

        return p

    def revoke(self, path):
        if not self.enabled:
            return path

        if not path:
            return path

        p = path.strip()
        if not p:
            return path

        if os.path.sep == p[0]:
            p = p[1:]

        p = self.chroot + p
        return p
