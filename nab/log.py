""" Module to manage logging. """
import logging
import logging.handlers
import appdirs
import os

log_dir = appdirs.user_log_dir('nab')
log_file = os.path.join(log_dir, 'log.txt')

_stream_handler = logging.StreamHandler()


def _init():
    log = logging.getLogger("nab")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t'
                                  '%(name)s:\t%(message)s')

    # create log directory
    try:
        os.makedirs(log_dir)
    except OSError:
        pass

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    _stream_handler.setLevel(logging.INFO)
    _stream_handler.setFormatter(formatter)
    log.addHandler(_stream_handler)
    return log
log = _init()


def set_level(log_level):
    _stream_handler.setLevel(log_level)
