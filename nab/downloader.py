""" Handles downloader plugins and downloads. """
from nab import exception


class DownloadException(Exception):

    """
    Exception raised within nab when a download cannot be completed.

    Plugins should not raise this, but instead raise nab.exception.PluginError.
    """

    def __init__(self, msg):
        """ Set message on this exception. """
        Exception.__init__(self, msg)


class DownloadManager:

    def __init__(self, download_log, scheduler, config):
        self._log = download_log
        self._downloads = {}
        self._scheduler = scheduler
        self._config = config

    def _downloader(self):
        return self._config.config['downloader'][0]

    def _test(self):
        return self._config.options.test

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

        self._log.info('For "%s" downloading %s' % (entry, torrent))
        self._log.debug(torrent.url)
        if self._test():
            raise DownloadException(
                "Nab is in test mode, no downloading allowed")

        try:
            self._downloader().download(torrent)
        except exception.PluginError:
            # unsuccessful, silently continue
            self._log.warning('Failed to download torrent')
        else:
            # successful, record downloaded file
            self._log.debug('Successfully started torrent download')
            self._downloads[torrent] = entry
            # mark this entry's episodes as no longer wanted
            for episode in entry.epwanted:
                episode.wanted = False

    def check_downloads(self):
        """ Check downloads to see if any have completed. """
        for d in list(self._downloads):
            if self._downloader().is_completed(d):
                for path in sorted(self._downloader().get_files(d)):
                    self._scheduler.add_asap("rename_file", path)
                    del self._downloads[d]

    def get_downloads(self):
        """
        Return a dictionary of downloads to show entries.

        A download is a nab.file.Torrent and an entry is a nab.show.Show,
        nab.season.Season or nab.episode.Episode.
        """
        return dict(self._downloads)
