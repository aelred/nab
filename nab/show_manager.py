""" Module for managing TV shows. """
import yaml
import os
import appdirs

from nab import config
from nab import log
from nab import exception
from nab import show_elem
from nab import show

_log = log.log.getChild("show")
shows_file = os.path.join(appdirs.user_data_dir('nab'), 'shows.yaml')


class ShowTree(show_elem.ShowParentElem):

    """
    A collection of shows, part of a collection of ShowElem classes.

    This is the root of ShowElems, representing a tree from:
        ShowTree -> Show -> Season -> Episode
    """

    def __init__(self):
        """ Create ShowTree, automatically loading from yaml file. """
        show_elem.ShowParentElem.__init__(self)
        try:
            with file(shows_file, 'r') as f:
                self.update(ShowTree.from_yaml(yaml.load(f), show.Show, self))
        except IOError:
            pass  # no shows.yaml file, doesn't matter!

    def find(self, id_):
        """ Return ShowElem matching ID if present, else return None. """
        if isinstance(id_, str):
            id_ = (id_,)

        for child in self.itervalues():
            f = child.find(id_)
            if f is not None:
                return f

    def save(self):
        """ Save ShowTree to yaml file. """
        yaml.safe_dump(self.to_yaml(), file(shows_file, 'w'))

    def to_yaml(self):
        """ Return yaml representation of ShowTree. """
        return show_elem.ShowParentElem.to_yaml(self)

    def update_data(self):
        """ Update show data for all shows. """
        for show in self.values():
            show.update_data()


def get_shows():
    """ Get shows from all ShowSources. """
    _log.info("Getting shows")

    # get wanted shows from 'following' list
    titles = []
    for source in config.config["shows"]["following"]:
        source.__class__.log.info("Searching show source %s" % source)
        try:
            titles += source.get_cached_shows()
        except exception.PluginError:
            # errors are printed, but keep running
            # shows will be looked up again in an hour
            pass

    return [show.Show(title) for title in titles]


def _filter_entry(entry, filter_funcs, permissive):
    wanted = not permissive
    for f in filter_funcs:
        if f(entry) == permissive:
            wanted = permissive  # change wanted status from default
            break

    if not wanted:
        for ep in entry.episodes:
            ep.wanted = False
    return wanted


def _apply_filters(shows, filters, permissive):
    # permissive = False means must be accepted by ALL filters
    for sh in shows.itervalues():
        if not _filter_entry(sh, [f.filter_show for f in filters], permissive):
            continue

        for se in sh.itervalues():
            if not _filter_entry(se, [f.filter_season for f in filters],
                                 permissive):
                continue

            for ep in se.itervalues():
                _filter_entry(ep, [f.filter_episode for f in filters],
                              permissive)


def filter_shows(shows):
    """
    Filter unwanted shows, seasons and episodes from list of shows.

    The rules for this are:
        1. Filter shows using 'following' ShowSources. If all of the ShowSources
           filter a show, season or episode, then it is marked unwanted.

        2. Filter shows using the 'filters' ShowFilters. If ANY ShowFilter
           filters a show, season or episode, then it is marked unwanted.

        The result of this is that if a show is wanted by any of the
        'following' plugins, then it is kept as 'wanted', but if any
        of the 'filter' plugins filter it out, it is removed.
    """
    _log.info("Filtering shows")

    following = config.config["shows"]["following"]
    library = config.config["shows"]["library"]
    filters = config.config["shows"]["filters"]

    # get owned/watched info for all episodes
    sources = following + library
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

    # first filter using show sources and permissive filtering
    _apply_filters(shows, following, True)

    # filter using show filters and strict filtering (must meet all criteria)
    _apply_filters(shows, filters, False)

    _log.info("Found %s needed episode(s)" % len(shows.epwanted))
    for ep in shows.epwanted:
        _log.info(ep)
