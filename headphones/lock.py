"""
Locking-related classes
"""

import time
import threading
import Queue


class TimedLock(object):
    """
    Enfore request rate limit if applicable. This uses the lock so there
    is synchronized access to the API. When N threads enter this method, the
    first will pass trough, since there there was no last request recorded.
    The last request time will be set. Then, the second thread will unlock,
    and see that the last request was X seconds ago. It will sleep
    (request_limit - X) seconds, and then continue. Then the third one will
    unblock, and so on. After all threads finish, the total time will at
    least be (N * request_limit) seconds. If some request takes longer than
    request_limit seconds, the next unblocked thread will wait less.
    """

    def __init__(self, minimum_delta=0):
        """
        Set up the lock
        """
        self.lock = threading.Lock()
        self.last_used = 0
        self.minimum_delta = minimum_delta
        self.queue = Queue.Queue()

    def __enter__(self):
        """
        Called when with lock: is invoked
        """
        self.lock.acquire()
        delta = time.time() - self.last_used
        sleep_amount = self.minimum_delta - delta
        if sleep_amount >= 0:
            # zero sleeps give the cpu a chance to task-switch
            time.sleep(sleep_amount)
        while not self.queue.empty():
            try:
                seconds = self.queue.get(False)
                time.sleep(seconds)
            except Queue.Empty:
                continue
            self.queue.task_done()

    def __exit__(self, type, value, traceback):
        """
        Called when exiting the with block.
        """
        self.last_used = time.time()
        self.lock.release()

    def snooze(self, seconds):
        """
        Asynchronously add time to the next request.
        Can be called outside
        of the lock context, but it is possible for the next lock holder
        to not check the queue until after something adds time to it.
        """
        # we use a queue so that we don't have to synchronize
        # across threads and with or without locks
        self.queue.add(seconds)


class FakeLock(object):
    """
    If no locking or request throttling is needed, use this
    """

    def __enter__(self):
        """
        Do nothing on enter
        """
        pass

    def __exit__(self, type, value, traceback):
        """
        Do nothing on exit
        """
        pass
