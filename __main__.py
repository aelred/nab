import show
import database
import files
import renamer
import show_tree
import config
import plugins
import downloader
from scheduler import scheduler

shows = show_tree.ShowTree()

plugin_types = [
    show.ShowSource,
    database.Database,
    show.ShowFilter,
    files.FileSource,
    files.FileFilter,
    downloader.Downloader
]


def get_data():
    new_shows = show.get_shows()

    for sh in new_shows:
        if not sh.title in shows:
            # get database info and add to shows
            database.get_data(sh)
            shows[sh.title] = sh

    show.filter_shows(shows)
    files.find_files(shows)

    # reschedule to get data every hour
    scheduler.add(60 * 60, get_data)

config.init()

if config.options.plugin:
    # load plugins
    plugins.load()

    if not config.args:
        # list all plugins
        for plugin_type in plugin_types:
            print plugin_type._type
            for entry in plugin_type.list_entries():
                print "\t" + entry.name
    else:
        # show data for given plugins
        for arg in config.args:
            for plugin_type in plugin_types:
                for entry in plugin_type.list_entries():
                    if entry.name == arg:
                        print entry.help_text() + "\n"
else:
    # start nabbing shows
    renamer.init(shows)
    scheduler.add(0, get_data)
