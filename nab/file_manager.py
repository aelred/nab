""" Module handling finding torrent files. """
import math
import time

from nab import downloader
from nab import exception
from nab import files


class FileManager:

    def __init__(self, file_log, scheduler, config, download_manager):
        self._scheduler = scheduler
        self._config = config
        self._download_manager = download_manager
        self._log = file_log

    def _sources(self):
        return self._config.config['files']['sources']

    def _filters(self):
        return self._config.config['files']['filters']

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

        self._scheduler(self.find_file)('timed', delay, entry, True)

    def _rank_file(self, f):
        self._log.debug(f.filename)
        rank = sum(filt.filter(f) for filt in self._filters())
        self._log.debug(rank)
        return rank

    def _best_file(self, files):
        if files:
            self._log.debug("Finding best file:")
            best = max(files, key=lambda f: self._rank_file(f))
            self._log.debug("Best file found:")
            self._log.debug(best.filename)
            return best
        return None

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
        return entry.match(f)

    def _find_all_files(self, entry):
        # only search for aired shows
        if not entry.has_aired():
            return None

        self._log.info("Searching for %s" % entry)
        results = []
        try:
            for source in self._sources():
                source.__class__.log.debug("Searching in %s" % source)

                for result in source.find(entry):
                    results.append(files.Torrent(**result))
        except exception.PluginError:
            return None

        if not results:
            self._log.info("No file found for %s" % entry)

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
                    self._scheduler(self.find_file)(
                        'lazy', child, reschedule)
        except AttributeError:
            pass

    def find_files(self, shows):
        """ Find torrents for all wanted episodes in the list of shows. """
        self._log.info("Finding files")

        for sh in sorted(shows.values(), key=lambda sh: sh.aired,
                         reverse=True):
            if len(sh.epwanted):
                self._scheduler(self.find_file)('lazy', sh, True)
