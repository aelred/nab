import os
import appdirs
import errno


# make various user data directories
def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print "Couldn't create directory %s" % path

for path in [appdirs.user_data_dir('nab'), appdirs.user_config_dir('nab'),
             appdirs.user_cache_dir('nab'), appdirs.user_log_dir('nab')]:
    makedirs(path)
