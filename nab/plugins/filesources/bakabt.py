import string
from filecache import filecache
import requests
import urllib
from lxml import html

from nab.files import Searcher, Torrent
from nab import config, exception

session = requests.session()


@filecache(60 * 60)
def _cget(*args, **kwargs):
    return session.get(*args, **kwargs)


class Bakabt(Searcher):
    """
    Searches the website bakabt.me for seasons.
    """

    _url = "http://bakabt.me"
    _surl = string.Template("%s/browse.php?only=0&incomplete=1&lossless=1&hd=1"
                            "&multiaudio=1&bonus=1&c1=1&c2=1&reorder=1"
                            "&q=${s}" % _url)

    def __init__(self):
        Searcher.__init__(self, ["season"], ["season"])
        session.post("%s/login.php" % Bakabt._url,
                     data=config.accounts['bakabt'])

    def _cget(self, *args, **kwargs):
        try:
            return _cget(*args, **kwargs)
        except requests.ConnectionError:
            raise exception.PluginError(self, "Error connecting to bakabt")

    def search(self, term):
        r = self._cget(Bakabt._surl.substitute({"s": urllib.quote(term)}),
                       auth=(config.accounts['bakabt']['username'],
                             config.accounts['bakabt']['password']))
        tree = html.fromstring(r.text)
        results = tree.xpath('//table[@class="torrents"]/tbody/'
                             'tr/td[@class="name"]/div/a/@href')
        files = []
        for result in results:
            tree = html.fromstring(self._cget(Bakabt._url + result).text)
            title = tree.xpath('//div[@id="description_title"]/h1/text()')[0]
            url = tree.xpath('//div[@class="download_link"]/a/@href')[0]
            tags = tree.xpath('//div[@class="tags"]/a/text()')
            files.append(Torrent(title, url))

        return files

Bakabt.register("bakabt")
