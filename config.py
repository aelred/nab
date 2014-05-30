import yaml
import os.path
from optparse import OptionParser
from shutil import copyfile


def _load_config():
    if not os.path.exists("config.yaml"):
        copyfile("config_default.yaml", "config.yaml")

    c = yaml.load(file("config.yaml", "r"))

    # create directories in settings
    s = c["settings"]
    dirs = [s["downloads"], s["completed"]] + s["videos"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

    return c
config = _load_config()


def _load_options():
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", default=False)
    parser.add_option("-p", "--plugin", action="store_true", default=False)
    return parser.parse_args()
options, args = _load_options()
