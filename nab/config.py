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


config_dir = appdirs.user_config_dir('nab')
config_file = os.path.join(config_dir, 'config.yaml')
accounts_file = os.path.join(config_dir, 'accounts.yaml')


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
        return path.format(user=os.getenv('USERPROFILE') or os.getenv('HOME'))
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

_observer = None


def init():
    handler = ConfigWatcher()
    global _observer
    _observer = Observer()
    _observer.schedule(handler, config_dir)
    _observer.start()


def stop():
    try:
        _observer.stop()
    except:
        pass


class ConfigWatcher(FileSystemEventHandler):
    def on_any_event(self, event):
        try:
            dest = event.dest_path
        except AttributeError:
            dest = None

        if event.src_path == config_file or dest == config_file:
            _log.info('Change detected in config.yaml, scheduling reload')
            scheduler.add_asap('load_config')
        if event.src_path == accounts_file or dest == accounts_file:
            _log.info('Change detected in accounts.yaml, scheduling reload')
            scheduler.add_asap('load_config')


def _load_options():
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", default=False)
    parser.add_option("-p", "--plugin", action="store_true", default=False)
    parser.add_option("-c", "--clean", action="store_true", default=False)
    return parser.parse_args()
options, args = _load_options()
