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

_log = log.log.getChild("config")


config_file = os.path.join(appdirs.user_config_dir('nab'), 'config.yaml')
accounts_file = os.path.join(appdirs.user_config_dir('nab'), 'accounts.yaml')


def _load_config():
    if not os.path.exists(config_file):
        _log.info("Creating default config file")
        copyfile("config_default.yaml", config_file)

    _log.info("Loading config and accounts files")
    c = yaml.load(file(config_file, "r"))
    a = yaml.load(file(accounts_file, "a+"))

    # find and create directories in settings
    s = c["settings"]

    def format_path(path):
        return path.format(user=os.getenv('USERPROFILE'),
                           home=os.getenv('HOME'))
    s["downloads"] = format_path(s["downloads"])
    s["videos"] = map(format_path, s["videos"])

    dirs = [s["downloads"]] + s["videos"]
    for d in dirs:
        if not os.path.exists(d):
            _log.info("Creating directory %s" % d)
            os.makedirs(d)

    return c, a
config, accounts = _load_config()


def reload_config():
    _log.info('Reloading config and accounts files')
    global config, accounts
    config, accounts = _load_config()
tasks["load_config"] = reload_config


def change_config(new_config):
    _log.info('Changing config file')
    yaml.safe_dump(new_config, file(config_file, 'w'))


def init():
    handler = ConfigWatcher()
    observer = Observer()
    observer.schedule(handler, ".")
    observer.start()


class ConfigWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == os.path.join(os.getcwd(), config_file):
            _log.info('Change detected in config.yaml, scheduling reload')
            scheduler.add_asap('load_config')
        if event.src_path == os.path.join(os.getcwd(), accounts_file):
            _log.info('Change detected in accounts.yaml, scheduling reload')
            scheduler.add_asap('load_config')


def _load_options():
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", default=False)
    parser.add_option("-p", "--plugin", action="store_true", default=False)
    parser.add_option("-c", "--clean", action="store_true", default=False)
    return parser.parse_args()
options, args = _load_options()
