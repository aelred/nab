from filecache import filecache
import feedparser
from unidecode import unidecode
import urllib
import re

from nab.files import Searcher, Torrent


@filecache(60 * 60)
def _get_feed(url):
    feed = feedparser.parse(url)
    if feed["entries"]:
        return feed["entries"]
    else:
        return []


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


class Feed(Searcher):
    def __init__(self, url, name=None,
                 search_by=None, match_by=None):
        Searcher.__init__(self, search_by, match_by)
        self.url = url
        self.name = name or url

        self.multipage = "{p}" in self.url

    def search(self, term):
        files = []

        if isinstance(term, unicode):
            term = unidecode(term)
        term = urllib.quote(term)

        p1_results = _get_feed(self.url.format(s=term, p=1))
        p1_links = set([f["link"] for f in p1_results])

        files = []
        # only search first 3 pages for files
        for page in range(1, 3):
            results = _get_feed(self.url.format(s=term, p=page))

            # break when no results or results are the same as page 1
            links = set([f["link"] for f in results])
            if not results or (page != 1 and p1_links == links):
                break

            for f in results:
                if "torrent_magneturi" in f:
                    url = f["torrent_magneturi"]
                else:
                    url = f["link"]

                files.append(Torrent(f["title"], url, get_seeds(f)))

            if not self.multipage:
                break

        return files

    def __str__(self):
        return "%s: %s" % (Searcher.__str__(self), self.name)

Feed.register("feed")
