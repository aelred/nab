from nab.show_manager import ShowSource
from nab.files import File
from nab.show import Show

import appdirs
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


watchlist_file = os.path.join(appdirs.user_config_dir('nab'), 'watchlist.txt')


class Watchlist(ShowSource):

    def __init__(self, *shows):
        ShowSource.__init__(self)
        self.config_entries = list(shows)

        # create a handler that watches the watchlist file
        WatchlistFileHandler(self)

    def entries(self):
        entries = []
        with file(watchlist_file, 'a+', 0o664) as f:
            for line in list(f) + self.config_entries:
                entry = File(line.rstrip(), False)
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


class WatchlistFileHandler(FileSystemEventHandler):
    def __init__(self, watchlist):
        observer = Observer()
        observer.schedule(self, os.path.dirname(watchlist_file))
        observer.start()
        self.watchlist = watchlist

    def on_modified(self, event):
        # refresh shows when file is changed
        self.watchlist.trigger_refresh()

Watchlist.register("watchlist")
