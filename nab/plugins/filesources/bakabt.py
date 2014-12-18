import string
from filecache import filecache
import requests
import urllib.request, urllib.parse, urllib.error
from lxml import html

from nab.files import Torrent
from nab.plugins.filesources import Searcher
from nab import exception

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

    def __init__(self, account):
        Searcher.__init__(self, ["season"], ["season"])
        self._account = account
        session.post("%s/login.php" % Bakabt._url, data=self._account)

    def _cget(self, *args, **kwargs):
        try:
            return _cget(*args, **kwargs)
        except requests.ConnectionError:
            raise exception.PluginError(self, "Error connecting to bakabt")

    def search(self, term):
        r = self._cget(Bakabt._surl.substitute({"s": urllib.parse.quote(term)}),
                       auth=(self._account['username'],
                             self._account['password']))
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

Bakabt.register("bakabt", req_account=True)
