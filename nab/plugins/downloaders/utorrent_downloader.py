""" Downloader that interfaces with uTorrent Web UI. """
from utorrent import client
import os.path

from nab.plugins.downloaders import Downloader


_STATUS = {
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
        self._tids = {}

    def download_url(self, tid, url):
        self._download(tid, url)

    def download_magnet(self, tid, magnet):
        self._download(tid, magnet)

    def get_download_status(self, tid):
        data = self._lookup(tid)

        return {
            'size': data['size'],
            'progress': float(data['percent progress']) / 1000.0,
            'downspeed': data['download speed'],
            'upspeed': data['upload speed'],
            'num_seeds': data['seeds connected'],
            'num_peers': data['peers connected'],
            'completed': (data['percent progress'] == 1000)
        }

    def get_files(self, tid):
        """ Return a list of files in the torrent from Web UI. """
        d = self._lookup(tid)
        files = self.getfiles(d['hash'])[1]['files'][1]
        return [os.path.join(d['path'], self._format_file_data(f)['name'])
                for f in files]

    def _download(self, tid, url_or_magnet):
        self._tids[tid] = url_or_magnet
        self._action([('action', 'add-url'), ('s', url_or_magnet)])

    def _lookup(self, tid):
        downloads = self.list()[1]['torrents']
        for d in map(self._format_torrent_data, downloads):
            if self._tids[tid] == d['url']:
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


uTorrent.register("utorrent", req_account=True)
