import config
import register
import log

_log = log.log.getChild("download")


class Downloader(register.Entry):
    _register = register.Register(config.config["downloaders"])

    def download(self, file_):
        raise NotImplemented()


def download(entry, f):
    if not f:
        return
    _log.info('For "%s" downloading %s' % (entry, f))
    _log.debug(f.url)
    if config.options.test:
        return

    for downloader in Downloader.get_all():
        downloader.download(f)
