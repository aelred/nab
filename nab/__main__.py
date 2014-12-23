""" Starts nab. """
from nab import show_manager
from nab import file_manager
from nab import config
from nab import scheduler
from nab import server
from nab import log
from nab import downloader
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

_LOG = logging.getLogger(__name__)


class _Nab:

    """ Class that organizes nab. """

    def __init__(self):
        """ Initialize nab. """
        self.options, self.args = config.parse_options()
        self.log_manager = log.LogManager(_LOG_FILE)

        # Begin logging
        if self.options.debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        self.log_manager.set_level(log_level)

        # handle exceptions here in logger
        self._excepthook = sys.excepthook
        sys.excepthook = self._handle_exception

        if self.options.clean:
            _clean()

        self.shows = show_manager.ShowTree(_SHOWS_FILE)
        self.scheduler = scheduler.NabScheduler(_SCHEDULE_FILE, self.shows)
        self.config = config.Config(_CONFIG_DIR, self.scheduler)

        self.show_manager = show_manager.ShowManager(self.config)
        self.download_manager = downloader.DownloadManager(
            self.scheduler, self.config, self.options, self.shows)
        self.file_manager = file_manager.FileManager(
            self.scheduler, self.config, self.download_manager)

        self._refresh_sched = self.scheduler(self._refresh)
        self._update_shows_sched = self.scheduler(self._update_shows)

        if self.options.plugin:
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
        _LOG.exception(''.join(traceback.format_exception(*exception)))
        # pass to python exception handler
        self._excepthook(*exception)

    def _start(self):
        """ Start nabbing shows. """
        server.init(self)

        # add command to refresh data
        # if command is already scheduled, this will be ignored
        self._refresh_sched('asap')

        # schedule first refresh of show data a week from now
        self._update_shows_sched('timed', 60 * 60 * 24 * 7)

        # start scheduler
        self.scheduler.start()

        # start server
        server.run()

    def _update_shows(self):
        """ Update data for all shows. """
        # reschedule to refresh show data in a week's time
        self._update_shows_sched('timed', 60 * 60 * 24 * 7)
        self.shows.update_data(self.config.config['databases'])

    def _refresh(self):
        """ Refresh list of shows and find files for any wanted episodes. """
        # reschedule to get data every hour
        self._refresh_sched('timed', 60 * 60)

        # add all shows
        for show in self.show_manager.get_shows():
            self.shows[show.title] = show

        self.show_manager.filter_shows(self.shows)
        self.file_manager.find_files(self.shows)

        # write data to file for backup purposes
        self.shows.save()

    def _show_plugins(self):
        """ Display information about plugins. """
        if not self.args:
            # list all plugins
            for plugin_type in _PLUGIN_TYPES:
                print plugin_type.type()
                for entry in plugin_type.list_entries():
                    print "\t" + entry.name
        else:
            # show data for given plugins
            for arg in self.args:
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
