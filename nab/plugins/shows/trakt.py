import requests
from filecache import filecache
from itertools import groupby

from nab.show_manager import ShowSource
from nab.database import Database
from nab.show import Show
from nab.season import Season
from nab.episode import Episode
from nab import config
from nab.exception import PluginError


@filecache(60 * 60)
def _cget(*args, **kwargs):
    return requests.get(*args, **kwargs)

show_data = {}


class Trakt:

    _url = "http://api.trakt.tv"

    def _get(self, url, *args, **kwargs):
        try:
            return requests.get(Trakt._url + url,
                                auth=(config.accounts['trakt']['username'],
                                      config.accounts['trakt']['password']),
                                *args, **kwargs)
        except requests.exceptions.ConnectionError:
            raise PluginError(self, 'Error connecting to trakt')

    def _cget(self, url, *args, **kwargs):
        try:
            return _cget(Trakt._url + url,
                         auth=(config.accounts['trakt']['username'],
                               config.accounts['trakt']['password']),
                         *args, **kwargs)
        except requests.exceptions.ConnectionError:
            raise PluginError(self, 'Error connecting to trakt')

    def get_data(self, show):
        if "tvdb" in show.ids:
            # use tvdb id to look up
            tvdb_id = show.ids["tvdb"]
            if tvdb_id in show_data:
                return show_data[tvdb_id]

        else:
            # search for longest names first (avoid searching for initials)
            for title in reversed(sorted(show.titles, key=len)):
                r = self._cget("/search/shows.json/%s" %
                               config.accounts['trakt']['api'],
                               params={"query": title, "limit": 1})

                try:
                    results = r.json()
                except ValueError:
                    raise PluginError(self, 'Error decoding trakt data')

                if results:
                    tvdb_id = results[0]["tvdb_id"]
                    break
            else:
                return None  # no result found

        # get show from trakt
        r = self._cget("/show/summary.json/%s/%s/true"
                       % (config.accounts['trakt']['api'], tvdb_id))
        try:
            j = r.json()
        except ValueError:
            raise PluginError(self, 'Error decoding trakt data')
        show_data[tvdb_id] = j
        return j


class TraktSource(ShowSource, Trakt):

    def get_shows(self):
        TraktSource.log.debug("Getting library")
        r1 = self._cget("/user/library/shows/all.json/%s/%s/min" %
                        (config.accounts['trakt']['api'],
                         config.accounts['trakt']['username']))
        # watchlist requests are never cached for fast response time
        TraktSource.log.debug("Getting watchlist")
        r2 = self._get("/user/watchlist/shows.json/%s/%s" %
                       (config.accounts['trakt']['api'],
                        config.accounts['trakt']['username']))
        sort = lambda s: s["title"].lower()

        try:
            shows_data = sorted(r1.json() + r2.json(), key=sort)
        except ValueError:
            raise PluginError(self, 'Error decoding trakt data')

        # remove duplicate shows
        shows_data = [next(v) for k, v in groupby(shows_data, key=sort)]
        shows_data = sorted(shows_data, key=sort)

        shows = []

        # get episode info
        for shd in shows_data:
            shows.append(Show(shd["title"], ids={"tvdb": shd["tvdb_id"]}))

        return shows

    def is_watched(self, episode):
        shd = self.get_data(episode.show)
        if not shd:
            return False

        try:
            sed = next(se for se in shd["seasons"]
                       if se["season"] == episode.season.num)
            epd = next(ep for ep in sed["episodes"]
                       if ep["episode"] == episode.num)
            return epd["watched"]
        except (KeyError, StopIteration):
            return False

    def is_owned(self, episode):
        shd = self.get_data(episode.show)
        if not shd:
            return False

        try:
            sed = next(se for se in shd["seasons"]
                       if se["season"] == episode.season.num)
            epd = next(ep for ep in sed["episodes"]
                       if ep["episode"] == episode.num)
            return epd["in_collection"]
        except (KeyError, StopIteration):
            return False

TraktSource.register("trakt")


class TraktDB(Database, Trakt):

    def get_show_titles(self, show):
        return [self.get_data(show)["title"]]

    def get_show_ids(self, show):
        return {"tvdb": self.get_data(show)["tvdb_id"]}

    def get_seasons(self, show):
        return [Season(show, sed["season"])
                for sed in self.get_data(show)["seasons"]]

    def get_episodes(self, season):
        data = self.get_data(season.show)["seasons"]
        sed = next(se for se in data if se["season"] == season.num)

        episodes = []

        for epd in sed["episodes"]:
            ep = Episode(season, epd["episode"],
                         epd["title"], epd["first_aired_utc"])
            if ep.aired == 0:
                ep.aired = None
            episodes.append(ep)

        return episodes

TraktDB.register("trakt")
