""" Database plugin for providing alternative titles for certain shows. """
from nab.plugins.databases import Database
from nab.season import Season


class AltTitles(Database):

    """ Adds additional titles for shows and seasons.  """

    def __init__(self, **shows):
        """
        Create an AltTitles database plugin.

        Args:
            shows: A structure of titles.
        """
        self.shows = dict((s.lower(), v) for s, v in shows.iteritems())

    def get_show_titles(self, show):
        """ Return alternative titles to the given show. """
        titles = []
        for t in map(lambda t: t.lower(), show.titles):
            titles += self.shows.get(t, {}).get('titles', [])

            for se in show:
                try:
                    show[se].titles.update(self.shows[t][se]["titles"])
                    show[se].title = self.shows[t][se]["titles"][0]
                except KeyError:
                    pass

    def get_seasons(self, show):
        """ Return seasons with alternative titles for the given show. """
        seasons = []

        for t in map(lambda t: t.lower(), show.titles):
            if t in self.shows:
                for (num, titles) in self.shows[t].iteritems():
                    seasons.append(Season(show, num, titles=titles))

        return seasons

AltTitles.register("alt_titles")
