""" Plugin package for plugins that extend nab. """
import os
import sys
import importlib

from nab.plugins import databases, filesources, shows, downloaders

_loaded = False


def load(plugin_log):
    """ Import all plugins in folder. Will only run once.  """
    global _loaded
    if _loaded:
        return

    for base in [databases.Database, filesources.FileSource,
                 filesources.FileFilter, shows.ShowSource, shows.ShowFilter,
                 downloaders.Downloader]:
        base.init(plugin_log)

    plugin_log.debug("Loading plugins")
    _loaded = True

    for folder, sub, files in os.walk("nab/plugins/"):
        sys.path.insert(0, folder)
        for f in files:
            fname, ext = os.path.splitext(f)
            if ext == '.py' and fname != "__init__":
                plugin_log.debug(fname)
                importlib.import_module(fname)
