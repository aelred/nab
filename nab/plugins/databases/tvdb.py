from filecache import filecache
import tvdb_api
import time

from nab.database import Database
from nab.show_tree import Season, Episode

_t = tvdb_api.Tvdb()


@filecache(7 * 24 * 60 * 60)
def show_search(term):
    return _t.search(term)


def show_get(show):
    try:
        if "tvdb" in show.ids:
            return _t[int(show.ids["tvdb"])]

        # search for longest names first (avoid searching for initials)
        for title in reversed(sorted(show.titles, key=len)):
            result = show_search(title)
            if len(result):
                return _t[int(result[0]["id"])]
    except (tvdb_api.tvdb_error, KeyError):
        # deal with errors where no match found
        # also deals with KeyError bug in tvdb API
        pass

    TVDB.log.debug("Couldn't find %s" % show)
    return None


class TVDB(Database):

    def get_show_titles(self, show):
        data = show_get(show)
        if data is None:
            return []

        titles = [data["seriesname"]]
        try:
            titles += show_search(data["seriesname"])[0]["aliasnames"]
        except KeyError:
            pass

        return titles

    def get_show_ids(self, show):
        data = show_get(show)
        if data is None:
            return {}
        return {"tvdb": data["id"]}

    def get_seasons(self, show):
        data = show_get(show)
        if data is None:
            return []

        return [Season(show, senum) for senum in data]

    def get_episodes(self, season):
        data = show_get(season.show)[season.num]
        if data is None:
            return []

        episodes = []
        for epnum in data:
            airstr = data[epnum]["firstaired"]
            if airstr is not None:
                try:
                    aired = time.mktime(time.strptime(airstr, "%Y-%m-%d"))
                except OverflowError:
                    aired = 0  # Doctor Who is REALLY old
            else:
                aired = None

            title = data[epnum]["episodename"]

            if title:
                # only add titled episodes
                episodes.append(Episode(season, epnum, title, aired))

        return episodes
TVDB.register("tvdb")
