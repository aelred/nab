""" Handles directories and exceptions for nab package. """
import os
import appdirs
import errno


# make various user data directories
def _makedirs(path):
    """ Make the specified path.  """
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno != errno.EEXIST:
            print "Couldn't create directory %s" % path

for app_path in [appdirs.user_data_dir('nab'), appdirs.user_config_dir('nab'),
                 appdirs.user_cache_dir('nab'), appdirs.user_log_dir('nab')]:
    _makedirs(app_path)
