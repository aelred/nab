import time

from nab import config
from nab import register
from nab import log
from nab import exception

_log = log.log.getChild("show")


class ShowFilter(register.Entry):
    _register = register.Register()
    _type = "show filter"

    def filter_show(self, show):
        return True

    def filter_season(self, season):
        return True

    def filter_episode(self, episode):
        return True


class ShowSource(register.Entry):
    _register = register.Register()
    _type = "show source"

    def __init__(self, cache_timeout=60*60):
        self._cached_shows = None
        self._cached_time = 0
        self.cache_timeout = 60 * 60

    def get_shows(self):
        raise NotImplemented()

    def get_cached_shows(self):
        elapsed = time.time() - self._cached_time
        if self._cached_shows is None or elapsed > self.cache_timeout:
            self._cached_time = time.time()
            self._cached_shows = self.get_shows()

        return self._cached_shows

    def is_watched(self, episode):
        return False

    def is_owned(self, episode):
        return NotImplemented()

    def filter_show(self, show):
        return show in self.get_cached_shows()

    def filter_season(self, season):
        return season.show in self.get_cached_shows()

    def filter_episode(self, episode):
        return episode.show in self.get_cached_shows()


def get_shows():
    _log.info("Getting shows")

    # get wanted shows from 'watching' list
    shows = []
    for source in ShowSource.get_all(config.config["shows"]["watching"]):
        source.__class__.log.info("Searching show source %s" % source)
        try:
            shows += source.get_cached_shows()
        except exception.PluginError:
            # errors are printed, but keep running
            # shows will be looked up again in an hour
            pass

    return shows


def filter_shows(shows):
    _log.info("Filtering shows")

    # get owned/watched info for all episodes
    sources = (ShowSource.get_all(config.config["shows"]["watching"]) +
               ShowSource.get_all(config.config["shows"]["library"]))
    try:
        for ep in shows.episodes:
            for source in sources:
                try:
                    if source.is_owned(ep):
                        ep.owned = True
                        break
                except exception.PluginError:
                    _log.info("Unknown ")
            for source in sources:
                if source.is_watched(ep):
                    ep.watched = True
                    break
    except exception.PluginError:
        # if shouw source fails, abandon all hope! (try again later)
        for ep in shows.episodes:
            # mark all episodes as unwanted
            # don't accidentally download unwanted things
            ep.wanted = False
        return

    _log.info("Found %s show(s)" % len(shows))

    _log.info("Applying filters")

    def filter_entry(entry, filter_funcs, permissive):
        # permissive = False means must be accepted by ALL filters

        wanted = not permissive
        for f in filter_funcs:
            if f(entry) == permissive:
                wanted = permissive  # change wanted status from default
                break

        if not wanted:
            for ep in entry.episodes:
                ep.wanted = False
        return wanted

    def filter_all(filters, permissive):
        for sh in shows.itervalues():
            if not filter_entry(sh, [f.filter_show for f in filters],
                                permissive):
                continue

            for se in sh.itervalues():
                if not filter_entry(se, [f.filter_season for f in filters],
                                    permissive):
                    continue

                for ep in se.itervalues():
                    filter_entry(ep, [f.filter_episode for f in filters],
                                 permissive)

    # first filter using show sources and permissive filtering
    filter_all(ShowSource.get_all(config.config["shows"]["watching"]), True)

    # filter using show filters and strict filtering (must meet all criteria)
    filter_all(ShowFilter.get_all(config.config["shows"]["filters"]), False)

    _log.info("Found %s needed episode(s)" % len(shows.epwanted))
    for ep in shows.epwanted:
        _log.info(ep)
