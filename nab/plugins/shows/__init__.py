""" Show plugins for finding shows that the user owns, watches or follows. """

import time

from nab.plugins import register


class ShowFilter(register.Entry):

    """ Plugin that filters unwanted shows, seasons and episodes. """

    _register = register.Register()
    _type = "show filter"

    def filter_show(self, show):
        """
        Return true if this show should be filtered (unwanted).

        Implementation optional, default returns true.
        """
        return True

    def filter_season(self, season):
        """
        Return true if this season should be filtered (unwanted).

        Implementation optional, default returns true.
        """
        return True

    def filter_episode(self, episode):
        """
        Return true if this episode should be filtered (unwanted).

        Implementation optional, default returns true.
        """
        return True


class ShowSource(register.Entry):

    """
    Plugin for finding TV shows.

    Not to be confused with database, which finds data for TV shows.

    A ShowSource also acts as a ShowFilter and can be used to filter
    out unwanted shows, seasons or episodes. The default behaviour is to
    filter out anything that does not appear in the list returned by
    get_shows().
    """

    _register = register.Register()
    _type = "show source"

    def __init__(self, cache_timeout=60*60):
        """
        Create a new ShowSource.

        Args:
            cache_timeout (int):
                Time before data should be re-fetched in seconds.
        """
        self._cached_shows = None
        self._cached_time = 0
        self.cache_timeout = 60 * 60

    def get_shows(self):
        """
        Return a list of show titles ([str]).

        This function is cached, so don't re-cache results in implementations.
        """
        raise NotImplementedError()

    def get_cached_shows(self):
        """ Return a list of show titles using the cache. """
        elapsed = time.time() - self._cached_time
        if self._cached_shows is None or elapsed > self.cache_timeout:
            self._cached_time = time.time()
            self._cached_shows = self.get_shows()

        return self._cached_shows

    def is_watched(self, episode):
        """
        Return whether the given episode has been watched.

        Implementation optional, default returns false.
        """
        return False

    def is_owned(self, episode):
        """
        Return whether the given episode is owned.

        This could mean on the filesystem, or on some web service such as
        trakt.tv.

        Implementation optional, default returns false.
        """
        return NotImplementedError()

    def filter_show(self, show):
        """
        Return true if this show should be filtered (unwanted).

        Implementation optional, default returns False.
        """
        return False

    def filter_season(self, season):
        """
        Return true if this season should be filtered (unwanted).

        Implementation optional, default delegates to filter_show.
        """
        return self.filter_show(season.show)

    def filter_episode(self, episode):
        """
        Return true if this episode should be filtered (unwanted).

        Implementation optional, default delegates to filter_season.
        """
        return self.filter_season(episode.season)

    def trigger_refresh(self):
        """
        Force cache for get_shows() to refresh and tell nab to refresh shows.

        Can be called in plugins when data is known to need refreshing.
        """
        self._cached_shows = None

        # tell nab to refresh and look up data again
        self.log.info("Refresh triggered")
        # TODO Reimplement scheduling refresh
        self.log.warning("REFRESH NOT IMPLEMENTED")
        # scheduler.scheduler.add_lazy("refresh")
