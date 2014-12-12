""" Plugin package for plugins that extend nab. """
import os
import sys
import importlib

from nab import log

_loaded = False


def load():
    """ Import all plugins in folder. Will only run once.  """
    global _loaded
    if _loaded:
        return
    log.log.debug("Loading plugins")
    _loaded = True

    for folder, sub, files in os.walk("nab/plugins/"):
        sys.path.insert(0, folder)
        for f in files:
            fname, ext = os.path.splitext(f)
            if ext == '.py' and fname != "__init__":
                log.log.debug(fname)
                importlib.import_module(fname)
