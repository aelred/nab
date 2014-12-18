""" Downloader plugins for downloading torrents. """

from nab import register


class Downloader(register.Entry):

    """
    A downloader is used to download torrents.

    Most downloader methods take a nab.file.Torrent object.
    """

    _register = register.Register()
    _type = "downloader"

    def download(self, torrent):
        """ Start downloading the given torrent. """
        raise NotImplementedError()

    def get_size(self, torrent):
        """ Return the total size in bytes of this torrent. """
        raise NotImplementedError()

    def get_progress(self, torrent):
        """ Return download progress of this torrent as a float from 0 to 1. """
        raise NotImplementedError()

    def get_downspeed(self, torrent):
        """ Return download speed in bytes per second of this torrent. """
        raise NotImplementedError()

    def get_upspeed(self, torrent):
        """ Return upload speed in bytes per second of this torrent. """
        raise NotImplementedError()

    def get_num_seeds(self, torrent):
        """ Return the number of seeds for this torrent. """
        raise NotImplementedError()

    def get_num_peers(self, torrent):
        """ Return the number of peers for this torrent. """
        raise NotImplementedError()

    def is_completed(self, torrent):
        """ Return whether this torrent has completed downloading. """
        raise NotImplementedError()

    def get_files(self, torrent):
        """ Return a list of absolute paths to files in this torrent. """
        raise NotImplementedError()


