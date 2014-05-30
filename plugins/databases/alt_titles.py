from database import Database


class AltTitles(Database):
    """
    Adds additional titles for shows and seasons.
    """

    def __init__(self, **shows):
        """
        Args:
            shows: A structure of titles.
        """
        self.shows = dict((s.lower(), v) for s, v in shows.iteritems())

    def add_data(self, sh):
        for t in map(lambda t: t.lower(), sh.titles):
            try:
                sh.titles.update(self.shows[t]["titles"])
            except KeyError:
                pass

            for se in sh:
                try:
                    sh[se].titles.update(self.shows[t][se]["titles"])
                    sh[se].title = self.shows[t][se]["titles"][0]
                except KeyError:
                    pass

AltTitles.register("alt_titles")
