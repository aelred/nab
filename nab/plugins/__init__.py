""" Plugin package for plugins that extend nab. """
import os
import sys
import importlib
import logging

_loaded = False

_LOG = logging.getLogger(__name__)


def _load():
    """ Import all plugins in folder. Will only run once.  """
    global _loaded
    if _loaded:
        return

    _LOG.debug("Loading plugins")
    _loaded = True

    for folder, sub, files in os.walk("nab/plugins/"):
        sys.path.insert(0, folder)
        for f in files:
            fname, ext = os.path.splitext(f)
            if ext == '.py' and fname != "__init__":
                _LOG.debug(fname)
                importlib.import_module(fname)
_load()
