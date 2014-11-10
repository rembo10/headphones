# Stub file. Not affiliated with the original 'pkg_resource.py' included in the
# 'setuptools' package.

def iter_entry_points(group, name=None):
    """
    Stub method to make APScheduler happy. This method is only imported in
    'lib/apscheduler/schedulers/base.py' to autodetect triggers, executors and
    job stores. Headphones does not use this functionality, so it just returns
    an iterator of an empty dict.
    """
    return iter(dict())