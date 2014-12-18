""" Database plugins for finding extra show data. """

from nab import register


class Database(register.Entry):

    """
    A show database is used to get data about TV shows.

    Show databases methods typically take a nab.show.Show object as a parameter
    and return some information about that show. They should not attempt to
    add data to the given object themselves!
    """

    _register = register.Register()
    _type = "database"

    def get_show_titles(self, show):
        """
        Return a list of strings describing titles of the given show.

        Implementation optional.
        The default implementation will return an empty list.
        """
        return []

    def get_show_absolute_numbering(self, show):
        """
        Return a boolean indicating if this show uses absolute numbering.

        Absolute numbering means the show uses a single number to identify
        episodes rather than a season and episode number.

        Implementation optional: if unsure, don't override this function.
        Return false by default.
        """
        return False

    def get_show_ids(self, show):
        """
        Return a dictionary of IDs for this show, where each key-value pair is
        a string, identifying a service and a string or an integer ID value.
        For example, a plugin for thetvdb might return { 'tvdb': 1242 }.

        This list of IDs is available to other plugins to use.

        Implementation optional.
        The default implementation will return an empty dictionary.
        """
        return {}

    def get_banner(self, show):
        """
        Return a URL to an image banner for this show.

        Implementation optional. The default implementation will return None.
        """
        return None

    def get_seasons(self, show):
        """
        Return a list of nab.season.Season objects for this show. Consult
        the documentation for that object for more details.

        Implementation optional.
        The default implementation will return an empty list.
        """
        return []

    def get_episodes(self, season):
        """
        Return a list of nab.episode.Episode objects for the given
        nab.season.Season object. Consult the documentation for that object
        for more details.

        Implementation optional.
        The default implementation will return an empty list.
        """
        return []

