""" Database plugins for finding extra show data. """

from nab.plugins import register


class Database(register.Entry):

    """
    A show database is used to get data about TV shows.

    Show databases methods typically take a list of titles and a dictionary of
    IDs and return some information about the show.
    """

    _register = register.Register()
    _type = "database"

    def get_show_titles(self, show_titles, show_ids):
        """
        Return a list of strings describing titles of the given show.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }

        Returns ([str]):
            List of titles for this show. Return an empty list by default.
        """
        return []

    def get_show_absolute_numbering(self, show_titles, show_ids):
        """
        Return if this show might use absolute numbering.

        Absolute numbering means the show uses a single number to identify
        episodes rather than a season and episode number.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }

        Returns (boolean):
            If this show might use absolute numbering. False if unsure.
            Return False by default.
        """
        return False

    def get_show_ids(self, show_titles, show_ids):
        """
        Return a dictionary of IDs for this show.

        This list of IDs is later available to other plugins to use.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }

        Returns ({str: str}):
            Dictionary of IDs for this show on various services.
            The key identifies the service and the value the ID.
            e.g. { 'tvdb': '1242' }
            Return an empty dictionary by default.
        """
        return {}

    def get_show_banner(self, show_titles, show_ids):
        """
        Return a URL to an image banner for this show.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }

        Returns (str):
            URL to an image banner for this show. Return None by default.
        """
        return None

    def get_num_seasons(self, show_titles, show_ids):
        """
        Return the number of seasons in this show (excluding specials).

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }

        Args:
            show (Show)
        Returns (int):
            The number of seasons. Return None by default.
        """
        return None

    def get_season_titles(self, show_titles, show_ids, season_num):
        """
        Return known titles for the given season.

        This is for unique season titles such as 'Scrubs: Interns' or
        'Blackadder Goes Forth'. Typically, shows do not have unique season
        titles. In that case, return the empty list.

        Do not return titles that ONLY identify the show, such as 'Friends' or
        'Firefly', even if the show has only one season. However, if a title
        identifies a show AND season, such as 'Bakemonogatari', include it.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }
            season_num (int):
                The season number. 0 indicates specials season.

        Returns ([str]):
            List of titles. Return an empty list by default.
        """
        return []

    def get_num_episodes(self, show_titles, show_ids, season_num):
        """
        Return the number of episodes in this season.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }
            season_num (int):
                The season number. 0 indicates specials season.

        Returns (int):
            The number of episodes in this season. Return None by default.
        """
        return None

    def get_episode_titles(self, show_titles, show_ids, season_num, ep_num):
        """
        Return known titles for the given episode.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }
            season_num (int):
                The season number. 0 indicates specials season.
            ep_num (int):
                The episode number within the season.

        Returns ([str]):
            List of titles. Return an emtpy list by default.
        """
        return []

    def get_episode_aired(self, show_titles, show_ids, season_num, ep_num):
        """
        Return when the given episode aired.

        Args:
            show_titles ([str]):
                List of titles of this show.
            show_ids ({str: str}):
                Dictionary of IDs for this show on various services.
                The key identifies the service and the value the ID.
                e.g. { 'tvdb': '1242' }
            season_num (int):
                The season number. 0 indicates specials season.
            ep_num (int):
                The episode number within the season.

        Returns (int):
            When the given episode aired in UNIX time. Return None by default.
        """
        return None
