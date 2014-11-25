from utorrent import client
import os.path

from nab.downloader import Downloader
from nab import config


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

    def __init__(self, ip="localhost", port=8080):
        client.UTorrentClient.__init__(self, 'http://%s:%d/gui/' % (ip, port),
                                       config.accounts['utorrent']['username'],
                                       config.accounts['utorrent']['password'])

    def download(self, torrent):
        self.addurl(torrent.url)

    def get_size(self, torrent):
        return self.lookup(torrent).get('size', 0)

    def get_progress(self, torrent):
        return float(self.lookup(torrent).get('percent progress', 0)) / 1000.0

    def get_downspeed(self, torrent):
        return self.lookup(torrent).get('download speed', 0)

    def get_upspeed(self, torrent):
        return self.lookup(torrent).get('upload speed', 0)

    def get_num_seeds(self, torrent):
        return self.lookup(torrent).get('seeds connected', 0)

    def get_num_peers(self, torrent):
        return self.lookup(torrent).get('peers connected', 0)

    def is_completed(self, torrent):
        return (self.lookup(torrent).get('percent progress', 0) == 1000)

    def get_files(self, torrent):
        d = self.lookup(torrent)
        files = self.getfiles(d['hash'])[1]['files'][1]
        return [os.path.join(d['path'], self._format_file_data(f)['name'])
                for f in files]

    def lookup(self, torrent):
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

    def addurl(self, url):
        params = [('action', 'add-url'), ('s', url)]
        return self._action(params)

uTorrent.register("utorrent")
