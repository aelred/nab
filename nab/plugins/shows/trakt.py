import requests
from filecache import filecache
from itertools import groupby

from nab.plugins.shows import ShowSource
from nab.plugins.databases import Database
from nab.exception import PluginError


@filecache(60 * 60)
def _cget(*args, **kwargs):
    return requests.get(*args, **kwargs)

show_data = {}


class Trakt:

    _url = "https://api.trakt.tv"

    def __init__(self, account):
        self._account = account

    def _get(self, url, get_func=requests.get, *args, **kwargs):
        try:
            return get_func(Trakt._url + url,
                            auth=(self._account['username'],
                                  self._account['password']),
                            headers={
                                'content-type': 'application/json',
                                'trakt-api-key': self._account['api'],
                                'trakt-api-version': 1
                            },
                            *args, **kwargs).json()
        except requests.exceptions.ConnectionError:
            raise PluginError(self, 'Error connecting to trakt')

    def _cget(self, url, *args, **kwargs):
        return self._get(url, get_func=_cget, *args, **kwargs)

    def get_data(self, show_titles, show_ids):
        if "tvdb" in show_ids:
            # use tvdb id to look up
            tvdb_id = int(show_ids["tvdb"])
            if tvdb_id in show_data:
                return show_data[tvdb_id]

        else:
            # search for longest names first (avoid searching for initials)
            for title in reversed(sorted(show_titles, key=len)):
                try:
                    results = self._cget(
                        "/search", params={"query": title, "limit": 1,
                                           "type": "show"})
                except ValueError:
                    raise PluginError(
                        self, 'Error decoding trakt search data for %s' %
                        show_titles)

                if results:
                    tvdb_id = results[0]["ids"]["tvdb"]
                    break
            else:
                return None  # no result found

        # get show from trakt
        try:
            j = self._cget("/show/summary.json/%s/%s/true"
                           % (self._account['api'], tvdb_id))
        except ValueError:
            raise PluginError(self, 'Error decoding trakt show data for %s'
                                    % show_titles)

        show_data[tvdb_id] = j
        return j


class TraktSource(Trakt, ShowSource):

    def __init__(self, account):
        Trakt.__init__(self, account)
        ShowSource.__init__(self)

    def get_shows(self):
        try:
            TraktSource.log.debug("Getting library")
            r1 = self._cget("/user/library/shows/all.json/%s/%s/min" %
                            (self._account['api'],
                             self._account['username']))
            # watchlist requests are never cached for fast response time
            TraktSource.log.debug("Getting watchlist")
            r2 = self._get("/user/watchlist/shows.json/%s/%s" %
                           (self._account['api'],
                            self._account['username']))
            sort = lambda s: s["title"].lower()
        except ValueError:
            raise PluginError(
                self, 'Error decoding trakt library and watchlist data')

        sort = lambda s: s["title"].lower()
        shows_data = sorted(r1 + r2, key=sort)

        # remove duplicate shows
        shows_data = [next(v) for k, v in groupby(shows_data, key=sort)]
        shows_data = sorted(shows_data, key=sort)

        return [shd["title"] for shd in shows_data]

    def is_watched(self, episode):
        shd = self.get_data(episode.show.titles, episode.show.ids)
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
        shd = self.get_data(episode.show.titles, episode.show.ids)
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

TraktSource.register("trakt", req_account=True)


class TraktDB(Trakt, Database):

    def get_show_titles(self, show_titles, show_ids):
        return [self.get_data(show_titles, show_ids)["title"]]

    def get_show_ids(self, show_titles, show_ids):
        return {"tvdb": str(self.get_data(show_titles, show_ids)["tvdb_id"])}

    def get_num_seasons(self, show_titles, show_ids):
        seasons = self.get_data(show_titles, show_ids)['seasons']
        return max(se['season'] for se in seasons)

    def get_num_episodes(self, show_titles, show_ids, season_num):
        seasons = self.get_data(show_titles, show_ids)['seasons']
        season = next(se for se in seasons if se['season'] == season_num)
        return max(ep['episode'] for ep in season['episodes'])

    def get_episode_titles(self, show_titles, show_ids, season_num, ep_num):
        seasons = self.get_data(show_titles, show_ids)['seasons']
        season = next(se for se in seasons if se['season'] == season_num)
        episode = next(ep for ep in season['episodes']
                       if ep['episode'] == ep_num)
        return [episode['title']]

    def get_episode_aired(self, show_titles, show_ids, season_num, ep_num):
        seasons = self.get_data(show_titles, show_ids)['seasons']
        season = next(se for se in seasons if se['season'] == season_num)
        episode = next(ep for ep in season['episodes']
                       if ep['episode'] == ep_num)
        return episode['first_aired_utc']

TraktDB.register("trakt", req_account=True)
