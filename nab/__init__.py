""" Handles directories and exceptions for nab package. """
import os
import appdirs
import errno
import sys
import traceback

import nab.log


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


# set up logging for uncaught exceptions
def _handle_exception(*exception):
    """ Pass exception to nab log. """
    log = nab.log.log.getChild("exception")
    log.exception("".join(traceback.format_exception(*exception)))

sys.excepthook = _handle_exception
