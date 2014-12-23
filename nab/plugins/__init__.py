""" Plugin package for plugins that extend nab. """
import os
import sys
import importlib
import logging

from .shows import ShowSource
from .shows import ShowFilter
from .databases import Database
from .filesources import FileSource
from .filesources import FileFilter
from .downloaders import Downloader

PLUGIN_TYPES = (
    ShowSource, ShowFilter, Database, FileSource, FileFilter, Downloader
)

_LOG = logging.getLogger(__name__)


def _load():
    """ Import all plugins in folder. """
    _LOG.debug("Loading plugins")

    for folder, sub, files in os.walk("nab/plugins/"):
        sys.path.insert(0, folder)
        for f in files:
            fname, ext = os.path.splitext(f)
            if ext == '.py' and fname != "__init__":
                _LOG.debug(fname)
                importlib.import_module(fname)
_load()
