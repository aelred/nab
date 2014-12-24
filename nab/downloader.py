""" Handles downloader plugins and downloads. """
from nab import exception
from nab import renamer

import logging

_LOG = logging.getLogger(__name__)


class DownloadManager:

    def __init__(self, scheduler, config, options, shows):
        self._downloads = {}
        self._config = config
        self._options = options

        renamer_ = renamer.Renamer(config, shows)
        self._rename_file_sched = scheduler(renamer_.rename_file)

        # check downloads every 15 seconds
        self._check_downloads_sched = scheduler(self._check_downloads)
        self._check_downloads_sched('repeat', 15)

    def _downloader(self):
        return self._config.config['downloader']

    def download(self, entry, torrent):
        """
        Download the given torrent for the given entry.

        Args:
            entry (Show, Season or Episode)
            torrent (Torrent)
        """
        if not torrent:
            return
        if torrent in self._downloads:
            return

        _LOG.info('For "%s" downloading %s' % (entry, torrent))
        _LOG.debug(torrent.url)
        if self._options.test:
            raise exception.DownloadException(
                "Nab is in test mode, no downloading allowed")

        try:
            if torrent.url:
                self._downloader().download_url(torrent.id, torrent.url)
            else:
                self._downloader().download_magnet(torrent.id,
                                                   torrent.magnet)
        except exception.PluginError:
            # unsuccessful, raise exception
            raise exception.DownloadException('Failed to download torrent')
        else:
            # successful, record downloaded file
            _LOG.debug('Successfully started torrent download')
            self._downloads[torrent] = entry
            # mark this entry's episodes as no longer wanted
            for episode in entry.epwanted:
                episode.wanted = False

    def _check_downloads(self):
        """ Check downloads to see if any have completed. """
        paths = []
        for d in list(self._downloads):
            if self._downloader().get_download_status(d.id)['completed']:
                paths += sorted(self._downloader().get_files(d.id))
                del self._downloads[d]

        for path in paths:
            self._rename_file_sched('asap', path)

    def get_downloads(self):
        """
        Return a dictionary of downloads to show entries.

        A download is a nab.file.Torrent and an entry is a nab.show.Show,
        nab.season.Season or nab.episode.Episode.
        """
        return dict(self._downloads)
