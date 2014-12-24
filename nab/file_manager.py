""" Module handling finding torrent files. """
import math
import time
import logging

from nab import exception
from nab import files

_LOG = logging.getLogger(__name__)


class FileManager:

    def __init__(self, scheduler, download_manager,
                 sources=None, filters=None):
        self.sources = sources or []
        self.filters = filters or []
        self._download_manager = download_manager
        self._find_file_sched = scheduler(self.find_file)

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

        self._find_file_sched('delay', delay, entry, True)

    def _rank_file(self, f):
        _LOG.debug(f.filename)
        values = [filt.filter(f) for filt in self.filters]
        if None in values:
            # None indicates reject this file
            rank = None
        else:
            rank = sum(values)
        _LOG.debug(rank)
        return rank

    def _best_file(self, files):
        if len(files) == 0:
            # No files given
            return None

        _LOG.debug("Finding best file:")
        best = max(files, key=lambda f: self._rank_file(f))

        if best is None:
            # none of the files are accepted by the filters
            return None

        _LOG.debug("Best file found:")
        _LOG.debug(best.filename)
        return best

    def _is_valid_file(self, f, entry):
        # no 'bad' tags
        bad_tags = ['raw', 'internal']

        for tag in f.tags:
            if tag in bad_tags:
                return False

        # must have at least one seeder
        if f.seeds is not None and f.seeds == 0:
            return False

        # must match given entry
        return entry.match(f.filename)

    def _find_all_files(self, entry):
        # only search for aired shows
        if not entry.has_aired():
            return []

        _LOG.info("Searching for %s" % entry)
        results = []
        try:
            for source in self.sources:
                source.__class__.log.debug("Searching in %s" % source)

                for result in source.find(entry):
                    results.append(files.Torrent(**result))
        except exception.PluginError:
            return []

        if not results:
            _LOG.info("No file found for %s" % entry)

        return [r for r in results if self._is_valid_file(r, entry)]

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
                    self._download_manager.download(entry, f)
                except exception.DownloadException:
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
                    self._find_file_sched('lazy', child, reschedule)
        except AttributeError:
            pass

    def find_files(self, shows):
        """ Find torrents for all wanted episodes in the list of shows. """
        _LOG.info("Finding files")

        for sh in sorted(shows.values(), key=lambda sh: sh.aired,
                         reverse=True):
            if len(sh.epwanted):
                self._find_file_sched('lazy', sh, True)
