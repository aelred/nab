""" Handles config files and command line arguments. """
import yaml
import os
import os.path
from optparse import OptionParser
from shutil import copyfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import appdirs

from nab import log
from nab import scheduler
from nab.plugins import shows
from nab.plugins import databases
from nab.plugins import filesources
from nab.plugins import downloaders

_LOG = log.log.getChild("config")

_CONFIG_PLUGIN_PATHS = {
    shows.ShowSource: (('shows', 'library'), ('shows', 'following')),
    shows.ShowFilter: (('shows', 'filters'),),
    databases.Database: (('databases',),),
    filesources.FileSource: (('files', 'sources'),),
    filesources.FileFilter: (('files', 'filters'),),
    downloaders.Downloader: (('downloader',),)
}


class _Config(FileSystemEventHandler):

    """
    Encapsulates config file and accounts file.

    Should never be directly modified except through specific scheduler calls.
    If the base files are modified, a reload is automatically scheduled.
    """

    def __init__(self, path, sched):
        # read config files
        self._accounts_file = os.path.join(path, 'accounts.yaml')
        self._config_file = os.path.join(path, 'config.yaml')
        self.load()

        # parse command line options
        self.options, self.args = _load_options()

        # watch config directory
        self._observer = Observer()
        self._observer.schedule(self, path)

        # set scheduler task to point to this object
        scheduler.tasks["load_config"] = self.load
        scheduler.tasks["set_config"] = self.set_config

        self._scheduler = sched

    def load(self):
        """ Reload config files. """
        _LOG.info('Reloading config and accounts files')
        self.accounts = _load_accounts(self._accounts_file)
        self.config = _load_config(self._config_file, self.accounts)

    def set_config(self, new_config):
        """ Replace config file with new config file. """
        _LOG.info('Changing config file')
        yaml.safe_dump(new_config, open(self._config_file, 'w'))

    def on_any_event(self, event):
        """ Reload a config file if it has changed. """
        try:
            dest = event.dest_path
        except AttributeError:
            dest = None

        if event.src_path == self._config_file or dest == self._config_file:
            _LOG.info('Change detected in config.yaml, scheduling reload')
            self._scheduler.add_asap('load_config')
        if (event.src_path == self._accounts_file
           or dest == self._accounts_file):
            _LOG.info('Change detected in accounts.yaml, scheduling reload')
            self._scheduler.add_asap('load_config')


def _load_config(path, accounts):
    """ Return contents of config file, creating it if it don't exist. """
    if not os.path.exists(path):
        _LOG.info("Creating default config file")
        copyfile("config_default.yaml", path)

    _LOG.info("Loading config file")
    conf = yaml.load(open(path, "r"))
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
            subtree[path[-1]] = entry_type.get_all(
                subtree[path[-1]], settings, accounts)

    return conf


def _load_accounts(path):
    """ Return contents of accounts file, creating it if it doesn't exist. """
    _LOG.info("Loading accounts file")
    acc = yaml.load(open(path, "a+"))
    return acc


def _load_options():
    """ Return option parser options. """
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", default=False)
    parser.add_option("-p", "--plugin", action="store_true", default=False)
    parser.add_option("-c", "--clean", action="store_true", default=False)
    parser.add_option("-d", "--debug", action="store_true", default=False)
    return parser.parse_args()


def create(scheduler):
    return _Config(appdirs.user_config_dir('nab'), scheduler)
