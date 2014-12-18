""" Plugin for accessing information from anidb. """
from collections import namedtuple, defaultdict
import requests
import xml.etree.ElementTree as ET
import urllib
import gzip
import time
from filecache import filecache
from lxml import html
from itertools import chain, product
from munkres import Munkres
import appdirs
import os

from nab.plugins.databases import Database
from nab.season import Season
from nab.match import format_title, comp


titles_file = os.path.join(appdirs.user_data_dir('nab'), 'anime-titles.xml.gz')

url = "http://api.anidb.net:9001/httpapi"
defparams = {
    "client": "shanaproject",
    "clientver": "1",
    "protover": "1"
}
langs = ["en", "x-jat"]
ns = "{http://www.w3.org/XML/1998/namespace}"


@filecache(7 * 24 * 60 * 60)
def _get_db():
    # fetch names database only once every two days max
    urllib.urlretrieve("http://anidb.net/api/anime-titles.xml.gz",
                       titles_file)

# populate database of titles
dbt = defaultdict(list)
dbi = {}
dbe = namedtuple("dbe", ["id", "title", "titles"])


def _load_db():
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

    with gzip.open(titles_file) as f:
        root = ET.fromstring(f.read())
        for show in root:
            e = dbe(show.get("aid"), main_title(show), get_titles(show))
            for t in e.titles:
                dbt[format_title(t)].append(e)
            dbi[e.id] = e

_init_flag = False


def _init():
    _get_db()
    _load_db()
    global _init_flag
    _init_flag = True

# only request one page every two seconds
_last_get = time.clock()
_get_interval = 2.0


# only request anidb data once a week max
@filecache(7 * 24 * 60 * 60)
def _get(*args, **kwargs):
    global _last_get

    t = time.clock()
    if t < _last_get + _get_interval:
        Anidb.log.debug("Sleeping between anidb requests")
        time.sleep(_last_get + _get_interval - t)
        t = time.clock()
        Anidb.log.debug("Done sleeping")

    Anidb.log.debug("Getting anidb page")
    r = requests.get(*args, **kwargs)
    _last_get = time.clock()
    return r


def _entries(title):
    return dbt[format_title(title)]


def _info(entry):
    Anidb.log.debug("Getting info for %s" % entry.title)
    params = dict(defparams, **{"request": "anime", "aid": entry.id})
    r = _get(url, params=params)
    Anidb.log.debug("Found info for %s" % entry.title)
    return html.fromstring(r.text.encode("ascii", "ignore"))


def _type(entry):
    return _info(entry).xpath('//type/text()')[0]


def _get_time(time_str):
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


def _startdate(entry):
    date = _info(entry).xpath(".//startdate/text()")[0]
    return _get_time(date)


def _airdate(episode):
    try:
        date = episode.xpath(".//airdate/text()")[0]
    except IndexError:
        return None
    return _get_time(date)


def _related(entry, types=None, incl_type=False):
    Anidb.log.debug("Finding shows related to %s" % entry.title)

    if types:
        type_str = "[" + " or ".join(['@type="%s"' % t for t in types]) + "]"
    else:
        type_str = ""
    rel = _info(entry).xpath("//relatedanime/anime%s" % type_str)
    result = []
    for r in rel:
        try:
            entry = dbi[r.xpath("@id")[0]]
        except KeyError:
            # entry not in database, skip over it
            # (database is likely not up-to-date)
            continue
        if incl_type:
            result.append((entry, r.xpath("@type")[0]))
        else:
            result.append(entry)

    Anidb.log.debug("Found related shows %s" % [e.title for e, t in result])
    return result


def _family(entries, criteria=lambda e: True, types=None):
    Anidb.log.debug("Getting family of %s" % [e.title for e in entries])

    relations = []
    rids = set()
    queue = list(reversed([(e, None) for e in entries]))
    while queue:
        (entry, rel_type) = queue.pop()
        Anidb.log.debug("Checking %s" % entry.title)
        if entry.id not in rids:
            rids.add(entry.id)
            if criteria(entry, rel_type):
                Anidb.log.debug("Adding %s" % entry.title)
                relations.append(entry)
            # continue searching if a direct pr/sequel or meets criteria
            if rel_type in ['Sequel', 'Prequel'] or criteria(entry, rel_type):
                queue += _related(entry, types, True)

    Anidb.log.debug("Family found for %s" % [e.title for e in entries])
    return relations


def _episodes(entry):
    eps = _info(entry).xpath('.//episodes/episode/epno[@type="1"]/text()')
    return sorted(map(int, eps))


@filecache(7 * 24 * 60 * 60)
def _find_seasons(entry):
    Anidb.log.debug("Getting seasons for %s" % entry.title)

    def is_season(e, rel_type):
        if e == entry:
            return True
        e_type = _info(e).xpath("//type/text()")[0]
        is_series = e_type == "TV Series"
        is_movie = e_type == "Movie"
        is_special = e_type == "TV Special"
        is_sequel = not rel_type or rel_type == "Sequel"
        return (is_series or is_sequel) and not (is_movie or is_special)
    seasons = _family([entry], is_season)

    # sort series by start date for correct season numbers
    seasons = sorted(seasons, key=_startdate)

    # eliminate entries earlier than requested season
    entry_index = seasons.index(entry)

    Anidb.log.debug("Seasons found for %s" % entry.title)

    return seasons[entry_index:]


def _find_specials(entry):
    # first search seasons for special episodes
    season_entries = _find_seasons(entry)
    lang_str = " or ".join(['@*="%s"' % la for la in langs])
    titles_path = './title[%s]/text()' % lang_str
    specials = []
    for series in season_entries:
        # pick special episodes from regular seasons
        eps = _info(series).xpath(
            './/episodes/episode/epno[@type="2"]/..')
        for ep in eps:
            if _airdate(ep) is None or _airdate(ep) <= time.time():
                specials.append((ep.xpath(titles_path), _airdate(ep)))

    # next search special series for episodes (e.g. spinoffs)
    sp_series = chain(*[_related(e) for e in season_entries])
    sp_series = filter(lambda s: s not in season_entries, sp_series)

    for series in sp_series:
        # pick regular and special episodes from special seasons
        eps = _info(series).xpath(
            './/episodes/episode/epno[@type="1" or @type="2"]/..')
        for ep in eps:
            if _airdate(ep) is None or _airdate(ep) <= time.time():
                if len(eps) == 1:
                    # one episode means series title is real title
                    titles = series.titles
                else:
                    titles = [str(t) for t in ep.xpath(titles_path)]
                    # combine episode titles with season titles
                    combs = product(series.titles, titles)
                    titles.extend([t1 + " " + t2 for t1, t2 in combs])
                specials.append((titles, _airdate(ep)))

    return specials


def _similarity(show, ep, titles):
    text_comp = max([comp(ep.title, t, show.titles)
                     for t in titles[0]])**2
    month = 60 * 60 * 24 * 30
    if ep.aired is not None and titles[1] is not None:
        air_comp = min(((titles[1] - ep.aired) / month)**2, 1.0)
    else:
        air_comp = 1.0
    return (text_comp + (1.0 - air_comp)) / 2.0

m = Munkres()


def _pair_episodes_to_titles(show, episodes, title_set):
    ep_nums = list(enumerate(episodes))
    title_nums = list(enumerate(title_set))

    # build matrix out of similarities
    cost_matrix = [[1.0 - _similarity(show, ep, t) for tn, t in title_nums]
                   for epn, ep in ep_nums]

    # Hungarian algorithm
    indexes = m.compute(cost_matrix)

    assign = {}
    for epn, tn in indexes:
        assign[ep_nums[epn][1]] = title_nums[tn][1]
    return assign


class Anidb(Database):

    """ Plugin that accesses show data from anidb. """

    def __init__(self):
        """ Create anidb plugin. """
        if not _init_flag:
            _init()

    def _show_get(self, show):
        # add data about other titles for this show
        Anidb.log.debug("Getting data for %s" % show)
        try:
            return _entries(show.title)[0]
        except IndexError:
            Anidb.log.debug("Couldn't find %s" % show)
            return None

    def get_show_titles(self, show):
        """ Add data about other titles for this show. """
        data = self._show_get(show)
        if data is None:
            return []
        return data.titles

    def get_show_absolute_numbering(self, show):
        """ If this show is on anidb, return true. """
        if self._show_get(show) is not None:
            return True
        else:
            return False

    def get_seasons(self, show):
        """ Get additional titles for show seasons. """
        data = self._show_get(show)
        if data is None:
            return []

        seasons = _find_seasons(data)
        return [Season(show, num, se.title, se.titles)
                for num, se in enumerate(seasons, 1)]

    # OBSOLETE
    def _add_data(self, sh):
        # add data about other titles for this show
        try:
            match = _entries(sh.title)[0]
        except IndexError:
            Anidb.log.debug("Couldn't find %s" % sh)
            return
        sh.titles.update(match.titles)

        # if on anidb, could use absolute episode numbering
        sh.absolute = True

        # find additional seasons
        season_entries = _find_seasons(match)

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
        specials = _find_specials(match)

        if len(specials) == 0:
            # no special episodes found
            return

        # match wanted specials to find special titles
        assign = _pair_episodes_to_titles(sh, season_sp.itervalues(), specials)
        for ep in assign:
            titles, airdate = assign[ep]
            # root out any obvious non-matches
            if _similarity(sh, ep, assign[ep]) < 0.10:
                continue
            ep.titles.update(titles)

Anidb.register("anidb")
