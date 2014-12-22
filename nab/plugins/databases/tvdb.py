""" Database plugin using thetvdb to get up-to-date TV show info. """
from filecache import filecache
import tvdb_api
import time

from nab.plugins.databases import Database

_t = tvdb_api.Tvdb()


@filecache(7 * 24 * 60 * 60)
def _show_search(term):
    return _t.search(term)


def _show_get(show_titles, show_ids):
    try:
        if "tvdb" in show_ids:
            return _t[int(show_ids["tvdb"])]

        # search for longest names first (avoid searching for initials)
        for title in reversed(sorted(show_titles, key=len)):
            result = _show_search(title)
            if len(result):
                return _t[int(result[0]["id"])]
    except (tvdb_api.tvdb_error, KeyError):
        # deal with errors where no match found
        # also deals with KeyError bug in tvdb API
        pass

    TVDB.log.debug("Couldn't find %s" % show_titles)
    return None


class TVDB(Database):

    """ Uses thetvdb to get up-to-date TV show info. """

    def get_show_titles(self, show_titles, show_ids):
        """ Return titles for the specified show. """
        data = _show_get(show_titles, show_ids)
        if data is None:
            return []

        titles = [data["seriesname"]]
        try:
            titles += _show_search(data["seriesname"])[0]["aliasnames"]
        except KeyError:
            pass

        return titles

    def get_show_ids(self, show_titles, show_ids):
        """ Return thetvdb id for the specified show. """
        data = _show_get(show_titles, show_ids)
        if data is None:
            return {}
        else:
            return {"tvdb": str(data["id"])}

    def get_banner(self, show_titles, show_ids):
        """ Return thetvdb show banner url. """
        return _show_get(show_titles, show_ids)['banner']

    def get_num_seasons(self, show_titles, show_ids):
        data = _show_get(show_titles, show_ids)
        if data is None:
            return None
        else:
            return max(data.keys())

    def get_num_episodes(self, show_titles, show_ids, season_num):
        data = _show_get(show_titles, show_ids)
        if data is None or season_num not in data:
            return None
        else:
            return max(data[season_num].keys())

    def get_episode_titles(self, show_titles, show_ids, season_num, ep_num):
        data = _show_get(show_titles, show_ids)
        try:
            ep = data[season_num][ep_num]
        except (TypeError, tvdb_api.tvdb_episodenotfound):
            return []  # no such episode found

        return [ep['episodename']]

    def get_episode_aired(self, show_titles, show_ids, season_num, ep_num):
        data = _show_get(show_titles, show_ids)
        try:
            ep = data[season_num][ep_num]
        except (TypeError, tvdb_api.tvdb_episodenotfound):
            return None  # no such episode found

        airstr = ep['firstaired']

        if airstr is not None:
            try:
                return time.mktime(time.strptime(airstr, '%Y-%m-%d'))
            except OverflowError:
                return 0  # Doctor Who is REALLY old
        else:
            return None

TVDB.register("tvdb")
