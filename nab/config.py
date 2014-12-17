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

_log = log.log.getChild("config")

_config_plugin_paths = {
    shows.ShowSource: [['shows', 'library'], ['shows', 'following']],
    shows.ShowFilter: [['shows', 'filters']],
    databases.Database: [['databases']],
    filesources.FileSource: [['files', 'sources']],
    filesources.FileFilter: [['files', 'filters']],
    downloaders.Downloader: [['downloader']]
}

_CONFIG_DIR = appdirs.user_config_dir('nab')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.yaml')
_ACCOUNTS_FILE = os.path.join(_CONFIG_DIR, 'accounts.yaml')


def _load_config():
    """ Return contents of config files, creating them if they don't exist. """
    if not os.path.exists(_CONFIG_FILE):
        _log.info("Creating default config file")
        copyfile("config_default.yaml", _CONFIG_FILE)

    _log.info("Loading config and accounts files")
    c = yaml.load(open(_CONFIG_FILE, "r"))
    a = yaml.load(open(_ACCOUNTS_FILE, "a+"))
    s = c["settings"]

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
            dir_map = dict((d.lower(), d) for d in dirs)

            # convert case to case of existing file, if it exists
            if basedir in dir_map:
                basedir = dir_map[basedir]

        return os.path.join(basepath, basedir)

    def format_path(path):
        """ Format user directory in path. """
        path = path.format(user=os.getenv('USERPROFILE') or os.getenv('HOME'))
        return case_insensitive(path)

    s["downloads"] = format_path(s["downloads"])
    s["videos"] = map(format_path, s["videos"])

    dirs = [s["downloads"]] + s["videos"]
    for d in dirs:
        if not os.path.exists(d):
            _log.info("Creating directory %s" % d)
            os.makedirs(d)

    # load any plugins on paths in config
    for entry_type, paths in _config_plugin_paths.items():
        for path in paths:
            subtree = c
            for node in path[:-1]:
                subtree = c[node]
            # replace parts of config data with loaded plugin
            subtree[path[-1]] = entry_type.get_all(subtree[path[-1]], s, a)

    return c, a
config, accounts = _load_config()


def reload_config():
    """ Reload config files into global variables. """
    _log.info('Reloading config and accounts files')
    global config, accounts
    config, accounts = _load_config()
tasks["load_config"] = reload_config


def change_config(new_config):
    """ Replace config file with new config file. """
    _log.info('Changing config file')
    yaml.safe_dump(new_config, open(_CONFIG_FILE, 'w'))

_observer = None


def init():
    """ Initialize config file watcher. """
    handler = ConfigWatcher()
    global _observer
    _observer = Observer()
    _observer.schedule(handler, _CONFIG_DIR)
    _observer.start()


def stop():
    """ Stop config file watcher. """
    try:
        _observer.stop()
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
            _log.info('Change detected in config.yaml, scheduling reload')
            scheduler.add_asap('load_config')
        if event.src_path == _ACCOUNTS_FILE or dest == _ACCOUNTS_FILE:
            _log.info('Change detected in accounts.yaml, scheduling reload')
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
