from nab import config
from nab import register
from nab import log

_log = log.log.getChild("database")


class Database(register.Entry):
    _register = register.Register()
    _type = "database"

    def get_show_titles(self, show):
        return []

    def get_show_absolute_numbering(self, show):
        return False

    def get_show_ids(self, show):
        return {}

    def get_seasons(self, show):
        return []

    def get_episodes(self, season):
        return []


def databases():
    return Database.get_all(config.config["databases"])


def get_data(show):
    _log.debug("Searching for %s" % show)

    # get all titles for show
    _log.debug("Getting titles")
    for db in databases():
        show.titles.update(db.get_show_titles(show))

    # get if should use absolute numbering
    _log.debug("Getting absolute numbering")
    for db in databases():
        if db.get_show_absolute_numbering(show):
            show.absolute = True
            break

    # get ids of show
    _log.debug("Getting ids")
    for db in databases():
        show.ids = dict(show.ids.items() + db.get_show_ids(show).items())

    # get seasons for show
    _log.debug("Getting seasons and episodes")
    for db in databases():
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
