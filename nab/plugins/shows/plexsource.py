from plex.server import Server
from itertools import chain

from nab.show_manager import ShowSource
from nab.show_tree import Show


class Plex(ShowSource):

    def __init__(self, ip="localhost", port=32400):
        ShowSource.__init__(self)

        self.server = Server(ip, port)

        shows = [sec.getContent() for sec in self.server.library.shows]
        shows = list(chain(*shows))
        self.shows = dict([(sh.title, sh) for sh in shows])

    def get_show_data(self, show):
        for title in show.titles:
            if title in self.shows:
                return self.shows[title]
        return None

    def get_ep_data(self, episode):
        show = self.get_show_data(episode.show)
        if show is None:
            return None
        try:
            season = show.seasons[episode.season.num]
        except IndexError:
            return None
        try:
            return season.episodes[episode.num]
        except IndexError:
            return None

    def get_shows(self):
        shows = []
        for title in self.shows:
            shows.append(Show(title))

        return shows

    def is_watched(self, episode):
        epd = self.get_ep_data(episode)
        if epd is None:
            return False
        return self.get_ep_data(episode).viewed

    def is_owned(self, episode):
        epd = self.get_ep_data(episode)
        if epd is None:
            return False
        else:
            return True
Plex.register("plex")
