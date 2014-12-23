""" Module to manage logging. """
import logging
import logging.handlers

_LOG = logging.getLogger(__name__.split('.')[0])


class LogManager:

    def __init__(self, log_file):
        _LOG_file = log_file
        _LOG.setLevel(logging.DEBUG)
        _LOG.propagate = False
        formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t'
                                      '%(name)s:\t%(message)s')

        file_handler = logging.handlers.RotatingFileHandler(
            _LOG_file, maxBytes=1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        _LOG.addHandler(file_handler)

        self._stream_handler = logging.StreamHandler()
        self._stream_handler.setLevel(logging.INFO)
        self._stream_handler.setFormatter(formatter)
        _LOG.addHandler(self._stream_handler)

    def set_level(self, log_level):
        self._stream_handler.setLevel(log_level)

    def get_log_text(self):
        return open(_LOG_file).read()
