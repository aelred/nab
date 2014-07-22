import pprint
import math
import time
import re

from nab import register
from nab import log
from nab import match
from nab import config
from nab import downloader
from nab.scheduler import scheduler, tasks
from nab.show_tree import Show, Season, Episode


_log = log.log.getChild("files")


video_exts = ['mpg', 'mpe', 'mpeg', 'mp2v', 'm2v', 'm2s', 'avi', 'mov', 'qt',
              'asf', 'asx', 'wmv', 'wmx', 'rm', 'ram', 'rmvb', 'mp4', '3gp',
              'ogm', 'flv', 'mkv']
sub_exts = ['srt', 'sub', 'smi']


class FileSource(register.Entry):
    _register = register.Register()
    _type = "file source"

    def find(self, show, season=None, episode=None):
        raise NotImplemented()


class FileFilter(register.Entry):
    _register = register.Register()
    _type = "file filter"

    def filter(self, f):
        raise NotImplemented()


class Searcher(FileSource):
    def __init__(self, search_by=None, match_by=None):
        _conv = {
            "show": Show,
            "season": Season,
            "episode": Episode
        }
        self.search_by = search_by or ["show", "season", "episode"]
        self.search_by = [_conv[s] for s in self.search_by]
        self.match_by = match_by or ["season", "episode"]
        self.match_by = [_conv[m] for m in self.match_by]

    def search(self, term=None):
        raise NotImplemented()

    def _search_all(self, s_terms, entry):

        def valid_file(f):
            # title must not contain bad words!
            badwords = ["raw", "internal"]
            for tag in f.tags:
                if tag in badwords:
                    return False
                # no tags that are just numbers (avoiding obscure files)
                if re.match(r"\d+$", tag):
                    return False

            # there must be at least one seeder
            if f.seeds is not None and f.seeds == 0:
                return False

            return entry.match(f)

        # search under every title
        files = []
        for term in s_terms:
            self.__class__.log.debug('Searching "%s"' % term)
            results = self.search(term)
            files += results

        return filter(valid_file, files)

    def find(self, entry):
        # Only search for things this searcher supports
        for m in self.match_by:
            if isinstance(entry, m):
                break
        else:
            return []

        # choose to search by show, season or episode
        s_terms = None
        if Episode in self.search_by:
            try:
                s_terms = entry.episode.search_terms()
            except AttributeError:
                pass
        if s_terms is None and Season in self.search_by:
            try:
                s_terms = entry.season.search_terms()
            except AttributeError:
                pass
        if s_terms is None and Show in self.search_by:
            try:
                s_terms = entry.show.search_terms()
            except AttributeError:
                pass
        if s_terms is None:
            return

        # get results
        return self._search_all(s_terms, entry)


class File(object):

    def __init__(self, filename):
        self.filename = filename

        data = File._split_filename(filename)

        self.ext = None
        if 'ext' in data:
            self.ext = data['ext']

        self.group = None
        if 'group' in data:
            self.group = data['group']

        self.title = data['title']

        self.season = None
        if 'season' in data:
            self.season = int(data['season'])

        self.episode = None
        if 'episode' in data:
            self.episode = int(data['episode'])

        self.eptitle = None
        if 'eptitle' in data:
            self.eptitle = data['eptitle']

        self.tags = data['tags']

    @staticmethod
    def _split_filename(filename):
        data = {"title": match.format_title(filename)}

        data.update(File._split_ext(data["title"]))
        data.update(File._split_group(data["title"]))
        data.update(File._split_tags(data["title"]))
        data.update(File._split_numbering(data["title"]))

        return data

    @staticmethod
    def _split_numbering(title):
        num_re = (r'(?P<title>.*?)\s+'
                  's?(?P<season>\d+)\s*'
                  '(ep?|\s+)(?P<episode>\d+)\s*(?P<eptitle>.*)$')
        match = re.match(num_re, title)
        if match:
            d = match.groupdict()
            if d["eptitle"] == "":
                del d["eptitle"]
            return d

        num_re = r"(?P<title>.*?)\s+s(eason)?\s*(?P<season>\d+)$"
        match = re.match(num_re, title)
        if match:
            return match.groupdict()

        num_re = r"(?P<title>.*?)\s+(ep?)?(?P<episode>\d+)\s*(?P<eptitle>.*)$"
        match = re.match(num_re, title)
        if match:
            d = match.groupdict()
            if d["eptitle"] == "":
                del d["eptitle"]
            return d

        return {}

    @staticmethod
    def _split_ext(title):
        ext_re = r"(.*?)\s+\.?(%s)$" % '|'.join(video_exts + sub_exts)
        match = re.match(ext_re, title)
        if match:
            return {"title": match.group(1), "ext": match.group(2)}

        return {}

    @staticmethod
    def _split_group(title):
        group_end_re = (r'(?P<title>.*?)'
                        '(-\s*(?P<group>[^\s]+?))\s*'
                        '(?P<title2>(?:\[.*)?)$')
        match = re.match(group_end_re, title)
        if match:
            d = match.groupdict()
            d["title"] += d["title2"]
            del d["title2"]
            return d

        group_begin_re = r"[\[\(\{](?P<group>.*?)[\]\)\}](?P<title>.*)$"
        match = re.match(group_begin_re, title)
        if match:
            return match.groupdict()

        return {}

    @staticmethod
    def _split_tags(title):
        tags = []

        bracket_re = r"[\[\{](.*?)[\]\}]"
        match = re.findall(bracket_re, title)
        if match:
            title = re.sub(bracket_re, "", title).strip()
            for m in match:
                tags += m.split()

        tag_re = (r'(.*?)\s+'
                  '((?:bd|hdtv|proper|web-dl|x264|dd5.1|hdrip|dvdrip|xvid|'
                  'cd[0-9]|dvdscr|brrip|divx|complete|batch|internal|'
                  '\d{3,4}x\d{3,4}|\d{3,4}p).*?)$')
        match = re.match(tag_re, title)
        if match:
            title = match.group(1).strip()
            tags += match.group(2).split()

        return {"title": title, "tags": tags}

    def __str__(self):
        return self.filename


class Torrent(File):

    def __init__(self, filename, url, seeds=None):
        File.__init__(self, filename)
        self.url = url
        self.seeds = seeds


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
    filters = FileFilter.get_all(config.config["files"]["filters"])
    return sum(filt.filter(f) for filt in filters)


def _best_file(files):
    if files:
        return max(files, key=lambda f: _rank_file(f))
    return None


def _find_all_files(entry):
    # only search for aired shows
    if not entry.has_aired():
        return None

    _log.info("Searching for %s" % entry)
    files = []
    for source in FileSource.get_all(config.config["files"]["sources"]):
        source.__class__.log.debug("Searching in %s" % source)
        files += source.find(entry)

    if not files:
        _log.info("No file found for %s" % entry)

    return files


def find_file(entry, reschedule):
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
                scheduler.add(0, "find_file", child, reschedule)
    except AttributeError:
        pass
tasks["find_file"] = find_file


def find_files(shows):
    _log.info("Finding files")

    for sh in sorted(shows.values(), key=lambda sh: sh.aired, reverse=True):
        if len(sh.epwanted):
            scheduler.add(0, "find_file", sh, True)
