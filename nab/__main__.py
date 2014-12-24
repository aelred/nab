""" Starts nab. """
from nab import show_manager
from nab import file_manager
from nab import config
from nab import scheduler
from nab import server
from nab import log
from nab import downloader
from nab import plugins
from nab import renamer

import os
import logging
import appdirs
import traceback
import sys

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
        self.config = config.Config(_CONFIG_DIR, self.scheduler,
                                    self._on_config_reload)

        self.show_manager = show_manager.ShowManager(
            self.config.config['shows']['following'],
            self.config.config['shows']['library'],
            self.config.config['shows']['filters'],
            self.config.config['databases'])

        self.renamer = renamer.Renamer(
            self.config.config['settings']['videos'],
            self.config.config['renamer'], self.shows)

        self.download_manager = downloader.DownloadManager(
            self.config.config['downloader'], self.options.test)

        self.file_manager = file_manager.FileManager(
            self.scheduler, self.download_manager,
            self.config.config['files']['sources'],
            self.config.config['files']['filters'])

        self._check_downloads_sched = self.scheduler(self._check_downloads)
        self._rename_file_sched = self.scheduler(self.renamer.rename_file)
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

        # check downloads every 15 seconds
        self._check_downloads_sched('repeat', 15)

        # add command to refresh data every hour
        self._refresh_sched('repeat', 60 * 60)

        # update shows a week from now, on repeat every week
        self._update_shows_sched('drepeat', 60 * 60 * 24 * 7)

        # start scheduler
        self.scheduler.start()

        # start server
        server.run()

    def _on_config_reload(self):
        """ When config reloads, set new values in all objects. """
        self.show_manager.following = self.config.config['shows']['following']
        self.show_manager.library = self.config.config['shows']['library']
        self.show_manager.filters = self.config.config['shows']['filters']
        self.show_manager.databases = self.config.config['databases']

        self.file_manager.sources = self.config.config['files']['sources']
        self.file_manager.filters = self.config.config['files']['filters']

        self.download_manager.downloader = self.config.config['downloader']

    def _update_shows(self):
        """ Update data for all shows. """
        self.shows.update_data(self.config.config['databases'])

    def _refresh(self):
        """ Refresh list of shows and find files for any wanted episodes. """
        # add all shows
        for show in self.show_manager.get_shows():
            self.shows[show.title] = show

        self.show_manager.filter_shows(self.shows)
        self.file_manager.find_files(self.shows)

        # write data to file for backup purposes
        self.shows.save()

    def _check_downloads(self):
        for path in self.download_manager.pop_completed():
            success = self._rename_file_sched('asap', path)
            if not success:
                # retry again later
                self._rename_file_sched('delay', 5 * 60, path)

    def _show_plugins(self):
        """ Display information about plugins. """
        if not self.args:
            # list all plugins
            for plugin_type in plugins.PLUGIN_TYPES:
                print plugin_type.type()
                for entry in plugin_type.list_entries():
                    print "\t" + entry.name
        else:
            # show data for given plugins
            for arg in self.args:
                for plugin_type in plugins.PLUGIN_TYPES:
                    for entry in plugin_type.list_entries():
                        if entry.name == arg:
                            print entry.help_text() + "\n"

    def downloader(self):
        return self.config.config['downloader']


def _clean():
    # clean up schedule and show files, start fresh
    try:
        os.remove(_SHOWS_FILE)
    except OSError:
        # file may not exist
        pass
    try:
        os.remove(_SCHEDULE_FILE)
    except OSError:
        pass

# Create main nab object and start!
_Nab()
