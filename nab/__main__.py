from nab import show
from nab import database
from nab import files
from nab import renamer
from nab import show_tree
from nab import config
from nab import plugins
from nab import downloader
from nab import scheduler

import os

shows = show_tree.ShowTree()

plugin_types = [
    show.ShowSource,
    database.Database,
    show.ShowFilter,
    files.FileSource,
    files.FileFilter,
    downloader.Downloader
]


def refresh():
    # reschedule to get data every hour
    scheduler.scheduler.add(60 * 60, "refresh")

    new_shows = show.get_shows()

    for sh in new_shows:
        if not sh.title in shows:
            # get database info and add to shows
            database.get_data(sh)
            shows[sh.title] = sh

    show.filter_shows(shows)
    files.find_files(shows)

    # write data to file for backup purposes
    shows.save()

scheduler.tasks["refresh"] = refresh

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

    if config.options.clean:
        # clean up schedule and show files, start fresh
        try:
            os.remove("shows.yaml")
        except Exception:  # don't know exception, depends on OS
            # file may not exist
            pass
        try:
            os.remove("schedule.yaml")
        except Exception:  # don't know exception, depends on OS
            # file may not exist
            pass

    # start nabbing shows
    renamer.init(shows)
    scheduler.init(shows)

    # add command to refresh data
    # if command is already scheduled, this will be ignored
    scheduler.scheduler.add(0, "refresh")
