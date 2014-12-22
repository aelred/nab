""" Database plugin for providing alternative titles for certain shows. """
from nab.plugins.databases import Database


class AltTitles(Database):

    """ Adds additional titles for shows and seasons.  """

    def __init__(self, **shows):
        """
        Create an AltTitles database plugin.

        Args:
            shows: A structure of titles.
        """
        self.shows = dict((s.lower(), v) for s, v in shows.iteritems())

    def get_show_titles(self, show_titles, show_ids):
        """ Return alternative titles to the given show. """
        titles = []
        for t in [t.lower() for t in show_titles]:
            titles += self.shows.get(t, {}).get('titles', [])
        return titles

    def get_season_titles(self, show_titles, show_ids, season_num):
        titles = []
        for t in [t.lower() for t in show_titles]:
            if t in self.shows and season_num in self.shows[t]:
                titles.append(self.shows[t][season_num])
        return titles

AltTitles.register("alt_titles")
