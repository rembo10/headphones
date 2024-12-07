"""Lock acquisition helpers."""
import datetime


class NeverExpires(object):
    """A representation of a never expiring object."""

    def expired(self):
        """Communicate that the object hasn't expired."""
        return False


class Timer(object):
    """A simple timer that will indicate when an expiration time has passed."""

    def __init__(self, expiration):
        """Create a timer that expires at `expiration` (UTC datetime)."""
        self.expiration = expiration

    @classmethod
    def after(cls, elapsed):
        """Return a timer that will expire after `elapsed` passes."""
        return cls(
            datetime.datetime.now(datetime.timezone.utc) + elapsed,
        )

    def expired(self):
        """Check whether the timer has expired."""
        return datetime.datetime.now(
            datetime.timezone.utc,
        ) >= self.expiration


class LockTimeout(Exception):
    """Exception when a lock could not be acquired before a timeout period."""


class LockChecker(object):
    """Keep track of the time and detect if a timeout has expired."""

    def __init__(self, session_id, timeout):
        """Initialize a lock acquisition tracker."""
        self.session_id = session_id
        if timeout:
            self.timer = Timer.after(timeout)
        else:
            self.timer = NeverExpires()

    def expired(self):
        """Check whether the lock checker has expired."""
        if self.timer.expired():
            raise LockTimeout(
                'Timeout acquiring lock for %(session_id)s' % vars(self))
        return False
