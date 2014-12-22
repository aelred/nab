""" Downloader plugins for downloading torrents. """

from nab.plugins import register


class Downloader(register.Entry):

    """
    A downloader is used to download torrents.

    Most downloader methods take a nab.file.Torrent object.
    """

    _register = register.Register()
    _type = "downloader"

    def download_url(self, tid, url):
        """
        Start downloading using the given torrent url.

        Args:
            tid (str):
                A unique ID identifying this torrent.
            url (str)
        """
        raise NotImplementedError()

    def download_magnet(self, magnet):
        """
        Start downloading using the given magnet link.

        Args:
            tid (str):
                A unique ID identifying this torrent.
            magnet (str)
        """

    def get_download_status(self, tid):
        """
        Return download data from the given torrent ID.

        Args:
            tid (str):
                A unique ID identifying this torrent.

        Returns (dict):
            Dictionary, including any of the following fields:
                - size (int): size of torrent in bytes
                - progress (float): progress of torrent, between 0.0 and 1.0
                - downspeed (int): download speed in bytes per second
                - upspeed (int): upload speed in bytes per second
                - num_seeds (int): number of seeds
                - num_peers (int): number of peers
                - completed (bool): if torrent is completed
        """

    def get_files(self, tid):
        """
        Return a list of absolute paths to files in this torrent.

        Args:
            tid (str):
                A unique ID identifying this torrent.

        Returns ([str]):
            List of absolute paths to files in this torrent.
        """
        raise NotImplementedError()
