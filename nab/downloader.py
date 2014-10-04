from nab import config
from nab import register
from nab import log
from nab import exception
from nab import scheduler

_log = log.log.getChild("download")
_downloads = {}


class Downloader(register.Entry):
    _register = register.Register()
    _type = "downloader"

    def download(self, torrent):
        raise NotImplemented()

    def is_completed(self, torrent):
        raise NotImplemented()

    def get_files(self, torrent):
        raise NotImplemented()


class DownloadException(Exception):

    def __init__(self, msg):
        Exception.__init__(self, msg)


def download(entry, torrent):
    if not torrent:
        return
    if torrent in _downloads:
        return

    _log.info('For "%s" downloading %s' % (entry, torrent))
    _log.debug(torrent.url)
    if config.options.test:
        raise DownloadException("Nab is in test mode, no downloading allowed")

    downloader = Downloader.get_all(config.config["downloader"])[0]
    try:
        downloader.download(torrent)
    except exception.PluginError:
        # unsuccessful, silently continue
        pass
    else:
        # successful, record downloaded file
        _downloads[torrent] = entry
        # mark this entry's episodes as no longer wanted
        for episode in entry.epwanted:
            episode.wanted = False


def check_downloads():
    scheduler.scheduler.add(15, "check_downloads")
    downloader = Downloader.get_all(config.config["downloader"])[0]
    for d in list(_downloads):
        if downloader.is_completed(d):
            for path in downloader.get_files(d):
                scheduler.scheduler.add_asap("rename_file", path)
            del _downloads[d]
scheduler.tasks["check_downloads"] = check_downloads
