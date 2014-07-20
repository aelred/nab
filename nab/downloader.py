from nab import config
from nab import register
from nab import log
from nab import exception

_log = log.log.getChild("download")


class Downloader(register.Entry):
    _register = register.Register()
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

    for downloader in Downloader.get_all(config.config["downloaders"]):
        try:
            downloader.download(f)
        except exception.PluginError:
            # unsuccessful, try the next downloader
            pass
        else:
            # succesful download, return
            return
