from filecache import filecache
import feedparser
from unidecode import unidecode
import urllib
import urlparse
import re

from nab.files import Torrent
from nab.plugins.filesources import Searcher


@filecache(60 * 60)
def _get_feed(url):
    feed = feedparser.parse(url)
    if feed['entries']:
        return feed['entries']
    else:
        raise IOError("No results found")


def get_seeds(f):
    if "description" in f:
        match = re.search(r"(\d+) seed", f["description"])
        if match:
            return int(match.group(1))
        match = re.search(r"seed(?:er(?:\(s?\))?)?:? (\d+)", f["description"])
        if match:
            return int(match.group(1))
    if "torrent_seeds" in f:
        return int(f["torrent_seeds"])
    return None


def get_torrent_url(f):
    links = f.get('links', [])
    for link in links:
        if link['type'] == 'application/x-bittorrent':
            return link['href']
    # no link found, just return first link
    if links:
        return links[0]['href']
    return None


class Feed(Searcher):
    def __init__(self, url, name=None,
                 search_by=None, match_by=None, num_pages=1):
        Searcher.__init__(self, search_by, match_by)
        self.url = url
        self.name = name or url
        self.num_pages = num_pages

        self.multipage = "{p}" in self.url

    def _get_feed(self, url):
        Feed.log.debug("Parsing feed at %s" % url)

        # retry three times
        feed = []
        for retry in range(1):
            try:
                feed = _get_feed(url)
            except IOError:
                continue
            else:
                break

        if feed:
            Feed.log.debug("Feed parsed")
        else:
            Feed.log.debug("No results found")

        return feed

    def search(self, term):
        files = []

        if isinstance(term, unicode):
            term = unidecode(term)
        term = urllib.quote(term)

        files = []
        # only search first few pages for files
        for page in range(1, self.num_pages + 1):
            results = self._get_feed(self.url.format(s=term, p=page))

            # remember page 1 links so we can tell if the
            # site is giving us the same page again
            links = set([(get_torrent_url(f), f.get("torrent_magneturi"))
                         for f in results])
            if page == 1:
                p1_links = set(links)

            # break when no results or results are the same as page 1
            if not results or (page != 1 and p1_links == links):
                break

            for f in results:
                url = get_torrent_url(f)
                magnet = f.get("torrent_magneturi")
                files.append(Torrent(f["title"], url, magnet, get_seeds(f)))

            if not self.multipage:
                break

        return files

    def __str__(self):
        return "%s: %s" % (Searcher.__str__(self), self.name)

Feed.register("feed")
