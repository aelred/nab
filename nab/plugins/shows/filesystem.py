import os
import re

from nab.show import ShowSource
from nab.files import File
from nab.show_tree import Show
from nab import config


class FileSystem(ShowSource):
    """
    Show source that finds shows and episode files in the filesystem.
    """

    def __init__(self):
        """
        Args:
            paths: A list of path strings specifying where to search for files.
        """
        ShowSource.__init__(self)

        self.paths = config.config["settings"]["videos"]

        # find show directories
        dirs = []
        for p in self.paths:
            for d in os.listdir(p):
                if os.path.isdir(os.path.join(p, d)):
                    dirs.append((p, d))

        # find all files in show directories
        files = {}
        for p, d in dirs:
            if not d in files:
                files[d] = set()
            for pp, dd, ff in os.walk(os.path.join(p, d)):
                for f in ff:
                    files[d].add(os.path.splitext(f)[0])

        # find all recognised episodes in show directories
        r = r'(?:\W|^)S?(\d+)[Ex](\d+)(?:\W|$)'
        episodes = set()
        for d in files:
            del_files = set()
            for f in files[d]:
                regex = re.search(r, f, re.IGNORECASE)
                if regex is not None:
                    senum, epnum = regex.groups()
                    episodes.add((d, int(senum), int(epnum)))
                    del_files.add(f)
            files[d] -= del_files

        self.dirs = dirs
        self.files = files
        self.episodes = episodes

    def show_dirs(self, show):
        """
        Return all the directories for a show.
        """
        dirs = []
        for p, d in self.dirs:
            if show.match(File(d), False):
                dirs.append(d)
        return dirs

    def get_shows(self):
        shows = []
        for p, d in self.dirs:
            shows.append(Show(d))
        return shows

    def is_owned(self, ep):
        # find show directories
        dirs = self.show_dirs(ep.show)

        for d in dirs:
            # check if episode is already listed
            if (d, ep.season.num, ep.num) in self.episodes:
                return True

        for d in dirs:
            # else, search files individually for matching episode
            match = None
            for f in self.files[d]:
                if ep.match(File(f)):
                    match = f
                    break

            if match is not None:
                self.files[d].remove(match)
                return True

        return False
FileSystem.register("filesystem")
