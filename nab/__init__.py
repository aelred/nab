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
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Couldn't create directory {}".format(path))

for app_path in [appdirs.user_data_dir('nab'), appdirs.user_config_dir('nab'),
                 appdirs.user_cache_dir('nab'), appdirs.user_log_dir('nab')]:
    _makedirs(app_path)


# set up logging for uncaught exceptions
_log = nab.log.log.getChild("exception")


def _handle_exception(ex_cls, ex, tb):
    """ Pass exception to nab log. """
    _log.critical(''.join(traceback.format_tb(tb)))
    _log.critical('{}: {}'.format(ex_cls, ex))

sys.excepthook = _handle_exception
