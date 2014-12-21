""" Module to manage logging. """
import logging
import logging.handlers


class Logger:

    def __init__(self, log_file):

        self._log_file = log_file
        self._log = logging.getLogger('nab')
        self._log.setLevel(logging.DEBUG)
        self._log.propagate = False
        formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t'
                                      '%(name)s:\t%(message)s')

        file_handler = logging.handlers.RotatingFileHandler(
            self._log_file, maxBytes=1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        self._log.addHandler(file_handler)

        self._stream_handler = logging.StreamHandler()
        self._stream_handler.setLevel(logging.INFO)
        self._stream_handler.setFormatter(formatter)
        self._log.addHandler(self._stream_handler)

    def set_level(self, log_level):
        self._stream_handler.setLevel(log_level)

    def get_child(self, name):
        return self._log.getChild(name)

    def get_log_text(self):
        return open(self._log_file).read()
