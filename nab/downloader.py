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

    def __init__(self, download_log, config, options):
        self._log = download_log
        self._downloads = {}
        self._config = config
        self._options = options

    def _downloader(self):
        return self._config.config['downloader'][0]

    def _test(self):
        return self._options.test

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
            if torrent.url:
                self._downloader().download_url(torrent.id, torrent.url)
            else:
                self._downloader().download_magnet(torrent.id,
                                                   torrent.magnet)
        except exception.PluginError:
            # unsuccessful, raise exception
            raise DownloadException('Failed to download torrent')
        else:
            # successful, record downloaded file
            self._log.debug('Successfully started torrent download')
            self._downloads[torrent] = entry
            # mark this entry's episodes as no longer wanted
            for episode in entry.epwanted:
                episode.wanted = False

    def check_downloads(self):
        """
        Check downloads to see if any have completed.

        Returns ([str]):
            List of paths to completed files.
        """
        paths = []
        for d in list(self._downloads):
            if self._downloader().get_download_status()['completed']:
                paths += sorted(self._downloader().get_files(d))
                del self._downloads[d]
        return paths

    def get_downloads(self):
        """
        Return a dictionary of downloads to show entries.

        A download is a nab.file.Torrent and an entry is a nab.show.Show,
        nab.season.Season or nab.episode.Episode.
        """
        return dict(self._downloads)
