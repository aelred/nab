from downloader import Downloader
import requests
from lxml import html


class uTorrent(Downloader):

    def __init__(self, username, password, ip="localhost", port=8080):
        self._url = "http://%s:%d/gui/" % (ip, port)
        self.session = requests.session()
        self.session.auth = (username, password)

        # get authentication token
        r = self.session.get(self._url + "token.html")
        tree = html.fromstring(r.text)
        self.token = tree.xpath('//div[@id="token"]/text()')[0]

    def download(self, f):
        self.session.get(self._url,
                         params={"token": self.token,
                                 "action": "add-url", "s": f.url})

uTorrent.register("utorrent")
