""" Module handling finding torrent files. """
import math
import time

from nab import log
from nab import downloader
from nab import exception


_log = log.log.getChild("files")


class FileManager:

    def __init__(self, scheduler, config):
        self._scheduler = scheduler
        self._config = config
        self._scheduler.tasks['find_file'] = self.find_file

    def _sources(self):
        return self._config.config['files']['sources']

    def _filters(self):
        return self._config.config['files']['filters']

    def _downloader(self):
        return self._config.config['downloader'][0]

    def _schedule_find(self, entry):
        if entry.aired is None:
            time_since_aired = time.time()
        else:
            time_since_aired = time.time() - entry.aired

        if time_since_aired > 0:
            delay = time_since_aired * math.log(time_since_aired) / 200
            delay = min(delay, 30 * 24 * 60 * 60)  # at least once a month
            delay = max(delay, 60 * 60)  # no more than once an hour
        else:
            delay = -time_since_aired  # nab as soon as it airs

        self._scheduler.add(delay, "find_file", entry, True)

    def _rank_file(self, f):
        _log.debug(f.filename)
        rank = sum(filt.filter(f) for filt in self._filters())
        _log.debug(rank)
        return rank

    def _best_file(self, files):
        if files:
            _log.debug("Finding best file:")
            best = max(files, key=lambda f: self._rank_file(f))
            _log.debug("Best file found:")
            _log.debug(best.filename)
            return best
        return None

    def _find_all_files(self, entry):
        # only search for aired shows
        if not entry.has_aired():
            return None

        _log.info("Searching for %s" % entry)
        files = []
        try:
            for source in self._sources():
                source.__class__.log.debug("Searching in %s" % source)
                files += source.find(entry)
        except exception.PluginError:
            return None

        if not files:
            _log.info("No file found for %s" % entry)

        return files

    def find_file(self, entry, reschedule):
        """
        Find a torrent for the given ShowElem entry using FileSource plugins.

        After a torrent is found, add it to the downloader.
        If the entry is not wanted, then do nothing.

        If a torrent is not found and reschedule is set to true, nab will
        search for a torrent again later.
        """
        # get entry only if wanted
        if entry.wanted:
            f = self._best_file(self._find_all_files(entry))
            if f:
                try:
                    downloader.download(self._downloader(), entry, f,
                                        self._config.options.test)
                except downloader.DownloadException:
                    pass  # reschedule download
                else:
                    return  # succesful, return

            if reschedule:
                self._schedule_find(entry)
                reschedule = False

        try:
            for child in sorted(entry.values(),
                                key=lambda c: c.aired, reverse=True):
                if len(child.epwanted):
                    self._scheduler.add_lazy("find_file", child, reschedule)
        except AttributeError:
            pass

    def find_files(self, shows):
        """ Find torrents for all wanted episodes in the list of shows. """
        _log.info("Finding files")

        for sh in sorted(shows.values(), key=lambda sh: sh.aired,
                         reverse=True):
            if len(sh.epwanted):
                self._scheduler.add_lazy("find_file", sh, True)
