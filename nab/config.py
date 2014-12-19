""" Handles config files and command line arguments. """
import yaml
import os
import os.path
from optparse import OptionParser
from shutil import copyfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import appdirs

from nab.scheduler import scheduler, tasks
from nab import log
from nab.plugins import shows
from nab.plugins import databases
from nab.plugins import filesources
from nab.plugins import downloaders

_LOG = log.log.getChild("config")

_CONFIG_PLUGIN_PATHS = {
    shows.ShowSource: (('shows', 'library'), ('shows', 'following')),
    shows.ShowFilter: (('shows', 'filters')),
    databases.Database: (('databases')),
    filesources.FileSource: (('files', 'sources')),
    filesources.FileFilter: (('files', 'filters')),
    downloaders.Downloader: (('downloader'))
}

_CONFIG_DIR = appdirs.user_config_dir('nab')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.yaml')
_ACCOUNTS_FILE = os.path.join(_CONFIG_DIR, 'accounts.yaml')


def _load_config():
    """ Return contents of config files, creating them if they don't exist. """
    if not os.path.exists(_CONFIG_FILE):
        _LOG.info("Creating default config file")
        copyfile("config_default.yaml", _CONFIG_FILE)

    _LOG.info("Loading config and accounts files")
    conf = yaml.load(file(_CONFIG_FILE, "r"))
    acc = yaml.load(file(_ACCOUNTS_FILE, "a+"))
    settings = conf["settings"]

    # find and create directories in settings
    def case_insensitive(path):
        """ look up path in a case insensitive way. """
        basepath, basedir = os.path.split(path)

        if basepath == path:
            # base case, return path as-is
            return path

        # recursive call to lower elements of path
        basepath = case_insensitive(basepath)

        dirs = os.listdir(basepath)

        # if this directory exists in the given casing, return it
        if basedir not in dirs:
            # lookup directory in lower case only
            basedir = basedir.lower()
            dir_map = dict((dir_.lower(), dir_) for dir_ in dirs)

            # convert case to case of existing file, if it exists
            if basedir in dir_map:
                basedir = dir_map[basedir]

        return os.path.join(basepath, basedir)

    def format_path(path):
        """ Format user directory in path. """
        path = path.format(user=os.getenv('USERPROFILE') or os.getenv('HOME'))
        return case_insensitive(path)

    settings["downloads"] = format_path(settings["downloads"])
    settings["videos"] = map(format_path, settings["videos"])

    dirs = [settings["downloads"]] + settings["videos"]
    for dir_ in dirs:
        if not os.path.exists(dir_):
            _LOG.info("Creating directory %s" % dir_)
            os.makedirs(dir_)

    # load any plugins on paths in config
    for entry_type, paths in _CONFIG_PLUGIN_PATHS.items():
        for path in paths:
            subtree = conf
            for node in path[:-1]:
                subtree = conf[node]
            # replace parts of config data with loaded plugin
            subtree[path[-1]] = entry_type.get_all(subtree[path[-1]], settings, acc)

    return conf, acc
config, accounts = _load_config()


def reload_config():
    """ Reload config files into global variables. """
    _LOG.info('Reloading config and accounts files')
    global config, accounts
    config, accounts = _load_config()
tasks["load_config"] = reload_config


def change_config(new_config):
    """ Replace config file with new config file. """
    _LOG.info('Changing config file')
    yaml.safe_dump(new_config, file(_CONFIG_FILE, 'w'))

OBSERVER = Observer()


def init():
    """ Initialize config file watcher. """
    handler = ConfigWatcher()
    _OBSERVER.schedule(handler, _CONFIG_DIR)
    _OBSERVER.start()


def stop():
    """ Stop config file watcher. """
    try:
        _OBSERVER.stop()
    except:
        pass


class ConfigWatcher(FileSystemEventHandler):

    """ Watcher that reloads config files whenever they change. """

    def on_any_event(self, event):
        """ Reload a config file if it has changed. """
        try:
            dest = event.dest_path
        except AttributeError:
            dest = None

        if event.src_path == _CONFIG_FILE or dest == _CONFIG_FILE:
            _LOG.info('Change detected in config.yaml, scheduling reload')
            scheduler.add_asap('load_config')
        if event.src_path == _ACCOUNTS_FILE or dest == _ACCOUNTS_FILE:
            _LOG.info('Change detected in accounts.yaml, scheduling reload')
            scheduler.add_asap('load_config')


def _load_options():
    """ Return option parser options. """
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", default=False)
    parser.add_option("-p", "--plugin", action="store_true", default=False)
    parser.add_option("-c", "--clean", action="store_true", default=False)
    parser.add_option("-d", "--debug", action="store_true", default=False)
    return parser.parse_args()
options, args = _load_options()
