""" Starts nab. """
from nab import show_manager
from nab import file_manager
from nab import config
from nab import plugins
from nab import scheduler
from nab import server
from nab import log
from nab import downloader
import nab.plugins.shows
import nab.plugins.databases
import nab.plugins.filesources
import nab.plugins.downloaders
from nab.plugins.downloaders import libtorrent_downloader

import os
import logging

_PLUGIN_TYPES = (
    nab.plugins.shows.ShowSource,
    nab.plugins.databases.Database,
    nab.plugins.shows.ShowFilter,
    nab.plugins.filesources.FileSource,
    nab.plugins.filesources.FileFilter,
    nab.plugins.downloaders.Downloader
)


class _Nab:

    """ Class that organizes nab. """

    def __init__(self):
        """ Initialize nab. """
        self.shows = show_manager.ShowTree()
        self.scheduler = scheduler.Scheduler(self.shows)
        self.config = config.create(self.scheduler)

        # set scheduler tasks to point to this object
        scheduler.tasks["update_shows"] = self._update_shows
        scheduler.tasks["refresh"] = self._refresh
        scheduler.tasks["check_downloads"] = self._check_downloads

        # Begin logging
        if self.config.options.debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        log.set_level(log_level)

        if self.config.options.clean:
            _clean()

        if self.config.options.plugin:
            self._show_plugins()
        else:
            try:
                self._start()
            except KeyboardInterrupt:
                pass
            finally:
                # stop other running threads on interrupt
                try:
                    self.scheduler.stop()
                except AttributeError:
                    pass
                del self.config

    def _start(self):
        """ Start nabbing shows. """
        server.init(self)

        # add command to refresh data
        # if command is already scheduled, this will be ignored
        self.scheduler.add_asap("refresh")

        # schedule first refresh of show data a week from now
        self.scheduler.add(60 * 60 * 24 * 7, "update_shows")

        # add command to check download progress
        self.scheduler.add_asap("check_downloads")

        # start scheduler
        self.scheduler.start()

        # start server
        server.run()

    def _update_shows(self):
        """ Update data for all shows. """
        # reschedule to refresh show data in a week's time
        self.scheduler.add(60 * 60 * 24 * 7, "update_shows")
        self.shows.update_data(self.config.config['databases'])

    def _refresh(self):
        """ Refresh list of shows and find files for any wanted episodes. """
        # reschedule to get data every hour
        self.scheduler.add(60 * 60, "refresh")

        # add all shows
        for show in show_manager.get_shows(
                self.config.config['databases'],
                self.config.config['shows']['following']):
            self.shows[show.title] = show

        show_manager.filter_shows(self.shows,
                                  self.config.config['shows']['following'],
                                  self.config.config['shows']['library'],
                                  self.config.config['shows']['filters'])
        file_manager.find_files(self.shows, self.scheduler,
                                self.config.config['files']['sources'],
                                self.config.config['files']['filters'])

        # write data to file for backup purposes
        self.shows.save()

    def _check_downloads(self):
        # every 15 seconds
        self.scheduler.add(15, "check_downloads")
        downloader.check_downloads(self.downloader(), self.scheduler,
                                   self.shows,
                                   self.config.config['renamer']['pattern'],
                                   self.config.config['settings']['videos'],
                                   self.config.config['renamer']['copy'])

    def _show_plugins(self):
        """ Display information about plugins. """
        # load plugins
        plugins.load()

        if not self.config.args:
            # list all plugins
            for plugin_type in _PLUGIN_TYPES:
                print plugin_type.type
                for entry in plugin_type.list_entries():
                    print "\t" + entry.name
        else:
            # show data for given plugins
            for arg in self.config.args:
                for plugin_type in _PLUGIN_TYPES:
                    for entry in plugin_type.list_entries():
                        if entry.name == arg:
                            print entry.help_text() + "\n"

    def downloader(self):
        return self.config.config['downloader'][0]


def _clean():
    # clean up schedule, show and libtorrent files, start fresh
    try:
        os.remove(show_manager.shows_file)
    except OSError:
        # file may not exist
        pass
    try:
        os.remove(scheduler._SCHEDULE_FILE)
    except OSError:
        pass
    try:
        os.remove(libtorrent_downloader.libtorrent_file)
    except OSError:
        pass

# Create main nab object and start!
_Nab()
