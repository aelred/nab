""" Handles downloader plugins and downloads. """
from nab import config
from nab import log
from nab import exception
from nab import scheduler

_log = log.log.getChild("download")
_downloads = {}


class DownloadException(Exception):

    """
    Exception raised within nab when a download cannot be completed.

    Plugins should not raise this, but instead raise nab.exception.PluginError.
    """

    def __init__(self, msg):
        """ Set message on this exception. """
        Exception.__init__(self, msg)


def _downloader():
    return config.config["downloader"][0]


def download(entry, torrent):
    """ Download the given torrent for the given entry.

    An entry is a nab.show.Show, nab.season.Season or nab.episode.Episode and
    a torrent is a nab.file.Torrent.
    """
    if not torrent:
        return
    if torrent in _downloads:
        return

    _log.info('For "%s" downloading %s' % (entry, torrent))
    _log.debug(torrent.url)
    if config.options.test:
        raise DownloadException("Nab is in test mode, no downloading allowed")

    downloader = _downloader()
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
    """ Check downloads to see if any have completed. """
    scheduler.scheduler.add(15, "check_downloads")
    downloader = _downloader()
    for d in list(_downloads):
        if downloader.is_completed(d):
            for path in sorted(downloader.get_files(d)):
                scheduler.scheduler.add_asap("rename_file", path)
            del _downloads[d]
scheduler.tasks["check_downloads"] = check_downloads


def get_size(torrent):
    """ Return the total size in bytes of this torrent. """
    return _downloader().get_size(torrent)


def get_progress(torrent):
    """ Return download progress of this torrent as a float from 0 to 1. """
    return _downloader().get_progress(torrent)


def get_downspeed(torrent):
    """ Return download speed in bytes per second of this torrent. """
    return _downloader().get_downspeed(torrent)


def get_upspeed(torrent):
    """ Return upload speed in bytes per second of this torrent. """
    return _downloader().get_upspeed(torrent)


def get_num_seeds(torrent):
    """ Return the number of seeds for this torrent. """
    return _downloader().get_num_seeds(torrent)


def get_num_peers(torrent):
    """ Return the number of peers for this torrent. """
    return _downloader().get_num_peers(torrent)


def get_downloads():
    """
    Return a dictionary of downloads to show entries.

    A download is a nab.file.Torrent and an entry is a nab.show.Show,
    nab.season.Season or nab.episode.Episode.
    """
    return dict(_downloads)
