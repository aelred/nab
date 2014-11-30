""" Handles show databases used to retrieve show data. """
from nab import config
from nab import register
from nab import log

_log = log.log.getChild("database")


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


def _databases():
    """ Return all databases in config file. """
    return Database.get_all(config.config["databases"])


def get_data(show):
    """ Retrieve and add data for a show from database plugins. """
    _log.debug("Searching for %s" % show)

    # get all titles for show
    _log.debug("Getting titles")
    for db in _databases():
        show.titles.update(db.get_show_titles(show))

    # get if should use absolute numbering
    _log.debug("Getting absolute numbering")
    for db in _databases():
        if db.get_show_absolute_numbering(show):
            show.absolute = True
            break

    # get ids of show
    _log.debug("Getting ids")
    for db in _databases():
        show.ids = dict(show.ids.items() + db.get_show_ids(show).items())

    # get banner for show
    _log.debug("Getting banner")
    for db in _databases():
        show.banner = db.get_banner(show)
        if show.banner:
            break

    # get seasons for show
    _log.debug("Getting seasons and episodes")
    for db in _databases():
        for season in db.get_seasons(show):
            # get episodes for season
            for episode in db.get_episodes(season):
                if episode.num in season:
                    season[episode.num].merge(episode)
                else:
                    season[episode.num] = episode

            if season.num in show:
                show[season.num].merge(season)
            else:
                show[season.num] = season

    show.format()
