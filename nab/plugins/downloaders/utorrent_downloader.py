""" Downloader that interfaces with uTorrent Web UI. """
from utorrent import client
import os.path

from nab.plugins.downloaders import Downloader


_status = {
    'started': 1,
    'checking': 2,
    'start after check': 4,
    'checked': 8,
    'error': 16,
    'paused': 32,
    'queued': 64,
    'loaded': 128
}


class uTorrent(client.UTorrentClient, Downloader):

    """ Downloader plugin to interface with uTorrent Web UI. """

    def __init__(self, account, ip="localhost", port=8080):
        """
        Create the uTorrent plugin.

        Args:
            ip (str): IP to utorrent client, defaults to 'localhost'.
            port (int): Port to access uTorrent client, defaults to 8080.
        """
        client.UTorrentClient.__init__(self, 'http://%s:%d/gui/' % (ip, port),
                                       account['utorrent']['username'],
                                       account['utorrent']['password'])

    def download(self, torrent):
        """ Tell uTorrent Web UI to download torrent. """
        url = torrent.url or torrent.magnet
        return self._action([('action', 'add-url'), ('s', url)])

    def get_size(self, torrent):
        """ Get size of torrent from Web UI. """
        return self._lookup(torrent).get('size', 0)

    def get_progress(self, torrent):
        """ Get progress of torrent from Web UI. """
        return float(self._lookup(torrent).get('percent progress', 0)) / 1000.0

    def get_downspeed(self, torrent):
        """ Get download speed of torrent from Web UI. """
        return self._lookup(torrent).get('download speed', 0)

    def get_upspeed(self, torrent):
        """ Get upload speed of torrent from Web UI. """
        return self._lookup(torrent).get('upload speed', 0)

    def get_num_seeds(self, torrent):
        """ Get number of seeds from Web UI. """
        return self._lookup(torrent).get('seeds connected', 0)

    def get_num_peers(self, torrent):
        """ Get number of peers from Web UI. """
        return self._lookup(torrent).get('peers connected', 0)

    def is_completed(self, torrent):
        """ Return if the torrent is completed from Web UI. """
        return (self._lookup(torrent).get('percent progress', 0) == 1000)

    def get_files(self, torrent):
        """ Return a list of files in the torrent from Web UI. """
        d = self._lookup(torrent)
        files = self.getfiles(d['hash'])[1]['files'][1]
        return [os.path.join(d['path'], self._format_file_data(f)['name'])
                for f in files]

    def _lookup(self, torrent):
        downloads = self.list()[1]['torrents']
        for d in map(self._format_torrent_data, downloads):
            if torrent.url == d['url']:
                return d
        return {}

    def _format_file_data(self, data):
        # label fields, some are unknown
        fields = ['name', 'size', 'downloaded', 'priority',
                  '', '', '', '', '', '', '', '']
        return dict(zip(fields, data))

    def _format_torrent_data(self, data):
        # label fields, some are unknown
        fields = ['hash', 'status', 'name', 'size', 'percent progress',
                  'downloaded', 'uploaded', 'ratio', 'upload speed',
                  'download speed', 'eta', 'label', 'peers connected',
                  'peers in swarm', 'seeds connected', 'seeds in swarm',
                  'availability', 'torrent queue order', 'remaining', 'url',
                  '', 'error', '', '', '', '', 'path', '']
        return dict(zip(fields, data))


uTorrent.register("utorrent", has_account=True)
