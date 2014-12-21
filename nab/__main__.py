""" Starts nab. """
from nab import show_manager
from nab import file_manager
from nab import config
from nab import plugins
from nab import scheduler
from nab import server
from nab import log
from nab import downloader
from nab import renamer
import nab.plugins.shows
import nab.plugins.databases
import nab.plugins.filesources
import nab.plugins.downloaders

import os
import logging
import appdirs
import traceback
import sys

_PLUGIN_TYPES = (
    nab.plugins.shows.ShowSource,
    nab.plugins.databases.Database,
    nab.plugins.shows.ShowFilter,
    nab.plugins.filesources.FileSource,
    nab.plugins.filesources.FileFilter,
    nab.plugins.downloaders.Downloader
)

_SHOWS_FILE = os.path.join(appdirs.user_data_dir('nab'), 'shows.yaml')
_CONFIG_DIR = appdirs.user_config_dir('nab')
_LOG_FILE = os.path.join(appdirs.user_log_dir('nab'), 'log.txt')
_SCHEDULE_FILE = os.path.join(appdirs.user_data_dir('nab'), 'schedule.yaml')


class _Nab:

    """ Class that organizes nab. """

    def __init__(self):
        """ Initialize nab. """
        self.logger = log.Logger(_LOG_FILE)

        # handle exceptions here in logger
        sys.excepthook = self._handle_exception

        # load all plugins
        plugins.load(self.logger.get_child('plugin'))

        self.shows = show_manager.ShowTree(_SHOWS_FILE)
        self.scheduler = scheduler.Scheduler(
            self.logger.get_child('scheduler'), _SCHEDULE_FILE, self.shows)
        self.config = config.Config(
            _CONFIG_DIR, self.logger.get_child('config'), self.scheduler)
        self.renamer = renamer.Renamer(self.logger.get_child('renamer'),
                                       self.scheduler, self.config, self.shows)

        self.show_manager = show_manager.ShowManager(
            self.logger.get_child('show'), self.config)
        self.download_manager = downloader.DownloadManager(
            self.logger.get_child('download'), self.scheduler, self.config)
        self.file_manager = file_manager.FileManager(
            self.logger.get_child('file'), self.scheduler, self.config,
            self.download_manager)

        # set scheduler tasks to point to this object
        self.scheduler.tasks["update_shows"] = self._update_shows
        self.scheduler.tasks["refresh"] = self._refresh
        self.scheduler.tasks["check_downloads"] = self._check_downloads

        # Begin logging
        if self.config.options.debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        self.logger.set_level(log_level)

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

    def _handle_exception(self, *exception):
        " Pass exception to nab log. """
        log = self.logger.get_child('error')
        log.exception(''.join(traceback.format_exception(*exception)))

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
        for show in self.show_manager.get_shows():
            self.shows[show.title] = show

        self.show_manager.filter_shows(self.shows)
        self.file_manager.find_files(self.shows)

        # write data to file for backup purposes
        self.shows.save()

    def _check_downloads(self):
        # every 15 seconds
        self.scheduler.add(15, "check_downloads")
        self.download_manager.check_downloads()

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
    from nab.plugins.downloaders import libtorrent_downloader
    try:
        os.remove(_SHOWS_FILE)
    except OSError:
        # file may not exist
        pass
    try:
        os.remove(_SCHEDULE_FILE)
    except OSError:
        pass
    try:
        os.remove(libtorrent_downloader.libtorrent_file)
    except OSError:
        pass

# Create main nab object and start!
_Nab()
