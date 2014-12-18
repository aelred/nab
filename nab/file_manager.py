""" Module handling finding torrent files. """
import math
import time

from nab import log
from nab import config
from nab import downloader
from nab import exception
from nab.scheduler import scheduler, tasks


_log = log.log.getChild("files")


def _schedule_find(entry):
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

    scheduler.add(delay, "find_file", entry, True)


def _rank_file(f):
    filters = config.config["files"]["filters"]
    _log.debug(f.filename)
    rank = sum(filt.filter(f) for filt in filters)
    _log.debug(rank)
    return rank


def _best_file(files):
    if files:
        _log.debug("Finding best file:")
        best = max(files, key=lambda f: _rank_file(f))
        _log.debug("Best file found:")
        _log.debug(best.filename)
        return best
    return None


def _find_all_files(entry):
    # only search for aired shows
    if not entry.has_aired():
        return None

    _log.info("Searching for %s" % entry)
    files = []
    try:
        for source in config.config["files"]["sources"]:
            source.__class__.log.debug("Searching in %s" % source)
            files += source.find(entry)
    except exception.PluginError:
        return None

    if not files:
        _log.info("No file found for %s" % entry)

    return files


def find_file(entry, reschedule):
    """
    Find a torrent for the given ShowElem entry using FileSource plugins.

    After a torrent is found, add it to the downloader.
    If the entry is not wanted, then do nothing.

    If a torrent is not found and reschedule is set to true, nab will
    search for a torrent again later.
    """
    # get entry only if wanted
    if entry.wanted:
        f = _best_file(_find_all_files(entry))
        if f:
            try:
                downloader.download(entry, f)
            except downloader.DownloadException:
                pass  # reschedule download
            else:
                return  # succesful, return

        if reschedule:
            _schedule_find(entry)
            reschedule = False

    try:
        for child in sorted(entry.values(),
                            key=lambda c: c.aired, reverse=True):
            if len(child.epwanted):
                scheduler.add_lazy("find_file", child, reschedule)
    except AttributeError:
        pass
tasks["find_file"] = find_file


def find_files(shows):
    """ Find torrents for all wanted episodes in the given list of shows. """
    _log.info("Finding files")

    for sh in sorted(shows.values(), key=lambda sh: sh.aired, reverse=True):
        if len(sh.epwanted):
            scheduler.add_lazy("find_file", sh, True)
