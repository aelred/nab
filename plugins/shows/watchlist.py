from show import ShowSource, ShowFilter
from files import File
from show_tree import Show


class Watchlist:

    def __init__(self, filename='watchlist.txt'):
        self.filename = filename

    def entries(self):
        entries = []
        with file(self.filename, 'a+') as f:
            for line in f:
                entry = File(line.rstrip())
                entries.append(entry)
        return entries


class WatchlistSource(Watchlist, ShowSource):

    def __init__(self, *args, **kwargs):
        Watchlist.__init__(self, *args, **kwargs)

    def get_shows(self):
        shows = []
        for entry in self.entries():
            shows.append(Show(entry.title))
        return shows

    def is_owned(self, ep):
        return False
WatchlistSource.register("watchlist")


class WatchlistFilter(Watchlist, ShowFilter):

    def __init__(self, *args, **kwargs):
        Watchlist.__init__(self, *args, **kwargs)

    def filter_episode(self, ep):
        for entry in self.entries():
            if (ep.match(entry) or
               ep.season.match(entry) or
               ep.show.match(entry)):
                return True
        return False
WatchlistFilter.register("watchlist")
