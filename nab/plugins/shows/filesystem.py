import os
import re

from nab.plugins.shows import ShowSource


class FileSystem(ShowSource):
    """
    Show source that finds shows and episode files in the filesystem.
    """

    def __init__(self, settings):
        """
        Args:
            paths: A list of path strings specifying where to search for files.
        """
        ShowSource.__init__(self)

        self.paths = settings["videos"]

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

        # Find all recognised episodes in show directories.
        # We do not use the file.File object used elsewhere in nab
        # because in this case we already know the show title from
        # the parent folder. We can be more lenient, only searching
        # for typical season/episode naming patterns.
        r = r'(?:\W|^)S?(\d+)[Ex](\d+)(?:\W|$)'

        # episodes are a tuple of (dir, season num, episode num)
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
            if show.match(d, False):
                dirs.append(d)
        return dirs

    def get_shows(self):
        return [d for p, d in self.dirs]

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
                if ep.match(f):
                    match = f
                    break

            if match is not None:
                self.files[d].remove(match)
                return True

        return False
FileSystem.register("filesystem", req_settings=True)
