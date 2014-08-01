from nab.show import ShowSource
from nab.files import File
from nab.show_tree import Show

import appdirs
import os


watchlist_file = os.path.join(appdirs.user_config_dir('nab'), 'watchlist.txt')


class Watchlist(ShowSource):

    def __init__(self, *shows):
        ShowSource.__init__(self)
        self.config_entries = list(shows)

    def entries(self):
        entries = []
        with file(watchlist_file, 'a+') as f:
            for line in list(f) + self.config_entries:
                entry = File(line.rstrip())
                entries.append(entry)
        return entries

    def get_shows(self):
        shows = []
        for entry in self.entries():
            shows.append(Show(entry.title))
        return shows

    def is_owned(self, ep):
        return False

    def filter_episode(self, ep):
        for entry in self.entries():
            if (ep.match(entry) or
               ep.season.match(entry) or
               ep.show.match(entry)):
                return True
        return False
Watchlist.register("watchlist")
