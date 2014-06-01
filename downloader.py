import config
import register
import log

_log = log.log.getChild("download")


class Downloader(register.Entry):
    _register = register.Register(config.config["downloaders"])
    _type = "downloader"

    def download(self, file_):
        raise NotImplemented()


class DownloadException(Exception):

    def __init__(self, msg):
        Exception.__init__(self, msg)


def download(entry, f):
    if not f:
        return
    _log.info('For "%s" downloading %s' % (entry, f))
    _log.debug(f.url)
    if config.options.test:
        raise DownloadException("Nab is in test mode, no downloading allowed")

    for downloader in Downloader.get_all():
        downloader.download(f)
