import pprint
import sys
import threading
import traceback

from headphones import logger


def cry():
    """
    Logs thread traces.
    """
    tmap = {}
    main_thread = None
    # get a map of threads by their ID so we can print their names
    # during the traceback dump
    for t in threading.enumerate():
        if t.ident:
            tmap[t.ident] = t
        else:
            main_thread = t

    # Loop over each thread's current frame, writing info about it
    for tid, frame in sys._current_frames().iteritems():
        thread = tmap.get(tid, main_thread)

        lines = []
        lines.append('%s\n' % thread.getName())
        lines.append('========================================\n')
        lines += traceback.format_stack(frame)
        lines.append('========================================\n')
        lines.append('LOCAL VARIABLES:\n')
        lines.append('========================================\n')
        lines.append(pprint.pformat(frame.f_locals))
        lines.append('\n\n')
        logger.info("".join(lines))
