""" Starts nab. """
from nab import show_manager
from nab import database
from nab import files
from nab import renamer
from nab import config
from nab import plugins
from nab import downloader
from nab import scheduler
from nab import server
import nab.plugins.shows
import nab.plugins.databases
import nab.plugins.filesources
import nab.plugins.downloaders
from nab.plugins.downloaders import libtorrent_downloader

import os


if config.options.clean:
    # clean up schedule, show and libtorrent files, start fresh
    try:
        os.remove(show_manager.shows_file)
    except OSError:
        # file may not exist
        pass
    try:
        os.remove(scheduler.schedule_file)
    except OSError:
        pass
    try:
        os.remove(libtorrent_downloader.libtorrent_file)
    except OSError:
        pass

shows = show_manager.ShowTree()

plugin_types = [
    nab.plugins.shows.ShowSource,
    nab.plugins.databases.Database,
    nab.plugins.shows.ShowFilter,
    nab.plugins.filesources.FileSource,
    nab.plugins.filesources.FileFilter,
    nab.plugins.downloaders.Downloader
]


def refresh():
    """ Refresh list of shows and find files for any wanted episodes. """
    # reschedule to get data every hour
    scheduler.scheduler.add(60 * 60, "refresh")

    # add all shows
    for sh in show_manager.get_shows():
        shows[sh.title] = sh

    show_manager.filter_shows(shows)
    files.find_files(shows)

    # write data to file for backup purposes
    shows.save()

scheduler.tasks["refresh"] = refresh


def update_shows():
    """ Update data for all shows. """
    # reschedule to refresh show data in a week's time
    scheduler.scheduler.add(60 * 60 * 24 * 7, "update_shows")
    shows.update_data()

scheduler.tasks["update_shows"] = update_shows

config.init()

if config.options.plugin:
    # load plugins
    plugins.load()

    if not config.args:
        # list all plugins
        for plugin_type in plugin_types:
            print plugin_type.type
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
    try:
        # start nabbing shows
        renamer.init(shows)
        scheduler.init(shows)
        server.init(shows)

        # add command to refresh data
        # if command is already scheduled, this will be ignored
        scheduler.scheduler.add_asap("refresh")

        # schedule first refresh of show data a week from now
        scheduler.scheduler.add(60 * 60 * 24 * 7, "update_shows")

        # add command to check download progress
        scheduler.scheduler.add_asap("check_downloads")

        # start server
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        # stop other running threads on interrupt
        scheduler.scheduler.stop()
        config.stop()
