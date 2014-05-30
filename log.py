import logging
import logging.handlers


def _init():
    log = logging.getLogger("nab")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t'
                                  '%(name)s:\t%(message)s')

    file_handler = logging.handlers.RotatingFileHandler(
        "log.txt", maxBytes=1024*1024)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    return log
log = _init()
