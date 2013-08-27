#
# OSX Mountain Lion Notifications
#
# Lifted from https://github.com/dbader/pytest-osxnotify - thanks!
#
# needs pyobjc-core
#

objc = None

def swizzle(cls, SEL, func):
    old_IMP = cls.instanceMethodForSelector_(SEL)
    def wrapper(self, *args, **kwargs):
        return func(self, old_IMP, *args, **kwargs)
    new_IMP = objc.selector(wrapper, selector=old_IMP.selector,
        signature=old_IMP.signature)
    objc.classAddMethod(cls, SEL, new_IMP)

def notify(title, subtitle=None, text=None, sound=True):
    """Display a NSUserNotification on Mac OS X >= 10.8"""

    global objc

    try:
        objc = __import__("objc")

        swizzle(objc.lookUpClass('NSBundle'),
               b'bundleIdentifier',
                swizzled_bundleIdentifier)

        NSUserNotification = objc.lookUpClass('NSUserNotification')
        NSUserNotificationCenter = objc.lookUpClass('NSUserNotificationCenter')
        NSAutoreleasePool = objc.lookUpClass('NSAutoreleasePool')
        if not NSUserNotification or not NSUserNotificationCenter:
            return

        pool = NSAutoreleasePool.alloc().init()

        notification = NSUserNotification.alloc().init()
        notification.setTitle_(str(title))
        if subtitle:
            notification.setSubtitle_(str(subtitle))
        if text:
            notification.setInformativeText_(str(text))
        if sound:
            notification.setSoundName_("NSUserNotificationDefaultSoundName")

        notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
        notification_center.deliverNotification_(notification)

        del pool

    except:
        pass

def swizzled_bundleIdentifier(self, original):
    """Swizzle [NSBundle bundleIdentifier] to make NSUserNotifications
    work.

    To post NSUserNotifications OS X requires the binary to be packaged
    as an application bundle. To circumvent this restriction, we modify
    `bundleIdentifier` to return a fake bundle identifier.

    Original idea for this approach by Norio Numura:
        https://github.com/norio-nomura/usernotification
    """
    #return 'com.apple.itunes'
    return 'org.headphones.notify'

if __name__ == '__main__':
    notify('Test Title', 'Test Subtitle', 'Test Text')

