import config
import register
import log

_log = log.log.getChild("show")


class ShowSource(register.Entry):
    _register = register.Register(config.config["shows"]["sources"])
    _type = "show source"

    def get_shows(self):
        raise NotImplemented()

    def is_watched(self, episode):
        return False

    def is_owned(self, episode):
        return NotImplemented()


class ShowFilter(register.Entry):
    _register = register.Register(config.config["shows"]["filters"])
    _type = "show filter"

    def filter_show(self, show):
        return True

    def filter_season(self, season):
        return True

    def filter_episode(self, episode):
        return True


def get_shows():
    _log.info("Getting shows")

    shows = []
    for source in ShowSource.get_all():
        source.__class__.log.info("Searching show source %s" % source)
        shows += source.get_shows()

    return shows


def filter_shows(shows):
    _log.info("Filtering shows")

    for ep in shows.episodes:
        for source in ShowSource.get_all():
            if source.is_owned(ep):
                ep.owned = True
                break
        for source in ShowSource.get_all():
            if source.is_watched(ep):
                ep.watched = True
                break

    _log.info("Applying filters")

    def filter_entry(entry, filter_funcs):
        wanted = True
        for f in filter_funcs:
            if not f(entry):
                wanted = False
                break

        if not wanted:
            for ep in entry.episodes:
                ep.wanted = False
        return wanted

    filters = ShowFilter.get_all()

    for sh in shows.itervalues():
        if not filter_entry(sh, [f.filter_show for f in filters]):
            continue

        for se in sh.itervalues():
            if not filter_entry(se, [f.filter_season for f in filters]):
                continue

            for ep in se.itervalues():
                filter_entry(ep, [f.filter_episode for f in filters])

    _log.info("Found %s needed episodes" % len(shows.epwanted))
    for ep in shows.epwanted:
        _log.info(ep)
