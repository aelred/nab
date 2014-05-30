from collections import namedtuple, defaultdict
import requests
import xml.etree.ElementTree as ET
import urllib
import gzip
import time
from filecache import filecache
from pprint import pprint
from lxml import html
from itertools import chain, product
from database import Database
from munkres import Munkres

from show_tree import Show, Season, Episode
from match import format_title, comp

url = "http://api.anidb.net:9001/httpapi"
defparams = {
    "client": "shanaproject",
    "clientver": "1",
    "protover": "1"
}
langs = ["en", "x-jat"]
ns = "{http://www.w3.org/XML/1998/namespace}"


# fetch names database only once every two days max
@filecache(7 * 24 * 60 * 60)
def get_db():
    urllib.urlretrieve("http://anidb.net/api/anime-titles.xml.gz",
                       "anime-titles.xml.gz")
get_db()

# populate database of titles
dbt = defaultdict(list)
dbi = {}
dbe = namedtuple("dbe", ["id", "title", "titles"])


def load_db():
    def main_title(show):
        for t in show:
            if t.get("type") == "official" and t.get("%slang" % ns) == "en":
                return t.text
        for t in show:
            if t.get("type") == "main":
                return t.text

    def get_titles(show):
        titles = [t.text for t in show
                  if t.get("%slang" % ns) in langs]
        return list(set(titles))

    with gzip.open("anime-titles.xml.gz") as f:
        root = ET.fromstring(f.read())
        for show in root:
            e = dbe(show.get("aid"), main_title(show), get_titles(show))
            for t in e.titles:
                dbt[format_title(t)].append(e)
            dbi[e.id] = e
load_db()

# only request one page every three seconds
_last_get = time.clock()
_get_interval = 3.0


# only request anidb data once a week max
@filecache(7 * 24 * 60 * 60)
def get(*args, **kwargs):
    global _last_get
    while time.clock() < _last_get + _get_interval:
        time.sleep(_last_get + _get_interval - time.clock())
    _last_get = time.clock()
    return requests.get(*args, **kwargs)


def entries(title):
    return dbt[format_title(title)]


def info(entry):
    params = dict(defparams, **{"request": "anime", "aid": entry.id})
    r = get(url, params=params)
    return html.fromstring(r.text.encode("ascii", "ignore"))


def type(entry):
    return info(entry).xpath('//type/text()')[0]


def get_time(time_str):
    try:
        return time.mktime(time.strptime(time_str, "%Y-%m-%d"))
    except ValueError:
        pass
    try:
        return time.mktime(time.strptime(time_str, "%Y-%m"))
    except ValueError:
        pass
    try:
        return time.mktime(time.strptime(time_str, "%Y"))
    except ValueError:
        return 0


def startdate(entry):
    date = info(entry).xpath(".//startdate/text()")[0]
    return get_time(date)


def airdate(episode):
    try:
        date = episode.xpath(".//airdate/text()")[0]
    except IndexError:
        return None
    return get_time(date)


def related(entry, types=None, incl_type=False):
    if types:
        type_str = "[" + " or ".join(['@type="%s"' % t for t in types]) + "]"
    else:
        type_str = ""
    rel = info(entry).xpath("//relatedanime/anime%s" % type_str)
    result = []
    for r in rel:
        entry = dbi[r.xpath("@id")[0]]
        if incl_type:
            result.append((entry, r.xpath("@type")[0]))
        else:
            result.append(entry)
    return result


def family(entries, criteria=lambda e: True, types=None):
    relations = []
    rids = set()
    queue = list(reversed([(e, None) for e in entries]))
    while queue:
        (entry, rel_type) = queue.pop()
        if entry.id not in rids and criteria(entry, rel_type):
            relations.append(entry)
            rids.add(entry.id)
            queue += related(entry, types, True)
    return relations


def episodes(entry):
    eps = info(entry).xpath('.//episodes/episode/epno[@type="1"]/text()')
    return sorted(map(int, eps))


@filecache(7 * 24 * 60 * 60)
def find_seasons(entry):
    def is_season(e, rel_type):
        if e == entry:
            return True
        is_series = info(e).xpath("//type/text()")[0] == "TV Series"
        is_movie = info(e).xpath("//type/text()")[0] == "Movie"
        is_special = info(e).xpath("//type/text()")[0] == "TV Special"
        is_sequel = not rel_type or rel_type == "Sequel"
        return (is_series or is_sequel) and not (is_movie or is_special)
    seasons = family([entry], is_season)

    # sort series by start date for correct season numbers
    seasons = sorted(seasons, key=startdate)

    # eliminate entries earlier than requested season
    entry_index = seasons.index(entry)
    return seasons[entry_index:]


def find_specials(entry):
    # first search seasons for special episodes
    season_entries = find_seasons(entry)
    lang_str = " or ".join(['@*="%s"' % la for la in langs])
    titles_path = './title[%s]/text()' % lang_str
    specials = []
    for series in season_entries:
        # pick special episodes from regular seasons
        eps = info(series).xpath(
            './/episodes/episode/epno[@type="2"]/..')
        for ep in eps:
            if airdate(ep) is None or airdate(ep) <= time.time():
                specials.append((ep.xpath(titles_path), airdate(ep)))

    # next search special series for episodes (e.g. spinoffs)
    sp_series = chain(*[related(e) for e in season_entries])
    sp_series = filter(lambda s: s not in season_entries, sp_series)

    for series in sp_series:
        # pick regular and special episodes from special seasons
        eps = info(series).xpath(
            './/episodes/episode/epno[@type="1" or @type="2"]/..')
        for ep in eps:
            if airdate(ep) is None or airdate(ep) <= time.time():
                if len(eps) == 1:
                    # one episode means series title is real title
                    titles = series.titles
                else:
                    titles = [str(t) for t in ep.xpath(titles_path)]
                    # combine episode titles with season titles
                    combs = product(series.titles, titles)
                    titles.extend([t1 + " " + t2 for t1, t2 in combs])
                specials.append((titles, airdate(ep)))

    return specials


def similarity(show, ep, titles):
    text_comp = max([comp(ep.title, t, show.titles)
                     for t in titles[0]])**2
    month = 60 * 60 * 24 * 30
    if ep.aired is not None and titles[1] is not None:
        air_comp = min(((titles[1] - ep.aired) / month)**2, 1.0)
    else:
        air_comp = 1.0
    return (text_comp + (1.0 - air_comp)) / 2.0

m = Munkres()


def pair_episodes_to_titles(show, episodes, title_set):
    ep_nums = list(enumerate(episodes))
    title_nums = list(enumerate(title_set))

    # build matrix out of similarities
    cost_matrix = [[1.0 - similarity(show, ep, t) for tn, t in title_nums]
                   for epn, ep in ep_nums]

    # Hungarian algorithm
    indexes = m.compute(cost_matrix)

    assign = {}
    for epn, tn in indexes:
        assign[ep_nums[epn][1]] = title_nums[tn][1]
    return assign


class Anidb(Database):

    def show_get(self, show):
        # add data about other titles for this show
        try:
            return entries(show.title)[0]
        except IndexError:
            Anidb.log.debug("Couldn't find %s" % show)
            return None

    def get_show_titles(self, show):
        # add data about other titles for this show
        data = self.show_get(show)
        if data is None:
            return []
        return data.titles

    def get_show_absolute_numbering(self, show):
        # if on anidb, could use absolute episode numbering
        if self.show_get(show) is not None:
            return True
        else:
            return False

    def get_seasons(self, show):
        data = self.show_get(show)
        if data is None:
            return []

        seasons = find_seasons(data)
        return [Season(show, num, se.title, se.titles)
                for num, se in enumerate(seasons, 1)]

    # OBSOLETE
    def add_data(self, sh):
        # add data about other titles for this show
        try:
            match = entries(sh.title)[0]
        except IndexError:
            Anidb.log.debug("Couldn't find %s" % sh)
            return
        sh.titles.update(match.titles)

        # if on anidb, could use absolute episode numbering
        sh.absolute = True

        # find additional seasons
        season_entries = find_seasons(match)

        # add titles for seasons
        season_sp = None
        for se in sh:
            if se == 0:
                season_sp = sh[se]
                continue
            try:
                sh[se].titles.update(set(season_entries[se - 1].titles))
            except IndexError:
                pass

        if season_sp is None or len(season_sp) == 0:
            # no special season found, skipping looking for specials
            return

        # find specials relating to this show
        specials = find_specials(match)

        if len(specials) == 0:
            # no special episodes found
            return

        # match wanted specials to find special titles
        assign = pair_episodes_to_titles(sh, season_sp.itervalues(), specials)
        for ep in assign:
            titles, airdate = assign[ep]
            # root out any obvious non-matches
            if similarity(sh, ep, assign[ep]) < 0.10:
                continue
            ep.titles.update(titles)

Anidb.register("anidb")
