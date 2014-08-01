import logging
import logging.handlers
import appdirs
import os

log_file = os.path.join(appdirs.user_log_dir('nab'), 'log.txt')


def _init():
    log = logging.getLogger("nab")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t'
                                  '%(name)s:\t%(message)s')

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)
    return log
log = _init()
