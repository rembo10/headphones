
from headphones import logger, notifiers
from lib.osxnotify import osxnotify

import headphones

def notify(artist, album, provider='', info='', xbmc_album_art_path=None, synoindex_album_paths=None):

    title = artist + ' - ' + album

    if provider:
        snatched = True
        event = 'Snatched from ' + provider
    else:
        snatched = False
        event = 'Download and Postprocessing completed'

    if info:
        event = event + '. ' + info

    if headphones.PROWL_ENABLED and (not snatched or headphones.PROWL_ONSNATCH and snatched):
        prowl = notifiers.PROWL()
        prowl.notify(title, event)

    if headphones.XBMC_ENABLED and not snatched:
        xbmc = notifiers.XBMC()
        if headphones.XBMC_UPDATE:
            xbmc.update()
        if headphones.XBMC_NOTIFY:
            xbmc.notify(artist, album, xbmc_album_art_path)

    if headphones.NMA_ENABLED and (not snatched or headphones.NMA_ONSNATCH and snatched):
        nma = notifiers.NMA()
        nma.notify(title, event)

    if headphones.SYNOINDEX_ENABLED and not snatched and synoindex_album_paths:
        syno = notifiers.Synoindex()
        for albumpath in synoindex_album_paths:
            syno.notify(albumpath)

    if headphones.PUSHOVER_ENABLED and (not snatched or headphones.PUSHOVER_ONSNATCH and snatched):
        pushover = notifiers.PUSHOVER()
        pushover.notify(title, event)

    #Mountain Lion Notification
    if headphones.OSX_NOTIFY_ENABLED and (not snatched or headphones.OSX_NOTIFY_ONSNATCH and snatched):
        osxnotify.notify(artist, album, event, True)

    if headphones.EMAIL_ENABLED and (not snatched or headphones.EMAIL_ONSNATCH and snatched):
        email = notifiers.EMAIL()
        email.notify(title, event)

