""" Handles downloader plugins and downloads. """
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


def download(downloader, entry, torrent, test):
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
    if test:
        raise DownloadException("Nab is in test mode, no downloading allowed")

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


def check_downloads(downloader, shows, rename_pattern, videos_path,
                    rename_copy):
    """ Check downloads to see if any have completed. """
    for d in list(_downloads):
        if downloader.is_completed(d):
            for path in sorted(downloader.get_files(d)):
                scheduler.scheduler.add_asap("rename_file", path, shows,
                                             rename_pattern, videos_path,
                                             rename_copy)
                del _downloads[d]


def get_downloads():
    """
    Return a dictionary of downloads to show entries.

    A download is a nab.file.Torrent and an entry is a nab.show.Show,
    nab.season.Season or nab.episode.Episode.
    """
    return dict(_downloads)
