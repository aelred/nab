from nab.plugins.shows import ShowSource

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

    def get_shows(self):
        with file(watchlist_file, 'a+', 0o664) as f:
            return [line.rstrip() for line in list(f) + self.config_entries]

    def is_owned(self, ep):
        return False

    def filter_episode(self, ep):
        for entry in self.get_shows():
            if (ep.match(entry, format_name=False) or
               ep.season.match(entry, format_name=False) or
               ep.show.match(entry, format_name=False)):
                return True
        return False


class WatchlistFileHandler(FileSystemEventHandler):
    def __init__(self, watchlist):
        self._observer = Observer()
        self._observer.schedule(self, os.path.dirname(watchlist_file))
        self._observer.start()
        self.watchlist = watchlist

    def __del__(self):
        try:
            self._observer.stop()
        except:
            pass

    def on_any_event(self, event):
        try:
            dest = event.dest_path
        except AttributeError:
            dest = None

        if event.src_path == watchlist_file or dest == watchlist_file:
            # refresh shows when file is changed
            self.watchlist.trigger_refresh()

Watchlist.register("watchlist")
