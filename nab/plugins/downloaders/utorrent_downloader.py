from utorrent import client

from nab.downloader import Downloader
from nab import config


class uTorrent(client.UTorrentClient, Downloader):

    def __init__(self, ip="localhost", port=8080):
        client.UTorrentClient.__init__(self, 'http://%s:%d/gui/' % (ip, port),
                                       config.accounts['utorrent']['username'],
                                       config.accounts['utorrent']['password'])

    def download(self, f):
        self.addurl(f.url)

    def addurl(self, url):
        params = [('action', 'add-url'), ('s', url)]
        return self._action(params)

uTorrent.register("utorrent")
