""" Handles show databases used to retrieve show data. """
from nab import config
from nab import register
from nab import log

_log = log.log.getChild("database")


def _databases():
    """ Return all databases in config file. """
    return config.config["databases"]


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
