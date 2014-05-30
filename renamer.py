import os
import os.path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
import string

import config
import log
from files import File
from scheduler import scheduler

path = config.config["settings"]["completed"]
pattern = config.config["renamer"]["pattern"]
copy = config.config["renamer"].get("copy", True)


def init(shows):
    handler = Renamer(shows)
    observer = Observer()
    observer.schedule(handler, path, recursive=True)
    observer.start()


class Renamer(FileSystemEventHandler):
    log = log.log.getChild("renamer")

    def __init__(self, shows):
        self.shows = shows
        FileSystemEventHandler.__init__(self)

    def _find_episode(self, file_):
        for ep in self.shows.episodes:
            if ep.match(file_):
                return ep
        return None

    def rename_file(self, path):
        # must be a file
        if not os.path.isfile(path):
            return

        f = File(os.path.basename(path))

        # must be a video file
        if not f.ext in ["mpg", "mpe", "mpeg", "mp2v", "m2v", "m2s",
                         "avi", "mov", "qt", "asf", "asx", "wmv", "wmx",
                         "rm", "ram", "rmvb", "mp4", "3gp", "ogm",
                         "mkv", "srt", "sub", "smi"]:
            Renamer.log.debug("Ignoring non-video file %s" % f)
            return

        if "sample" in f.tags:
            Renamer.log.debug("Ignoring sample file %s" % f)
            return

        Renamer.log.debug("File created %s" % f)

        # look for a matching episode
        episode = self._find_episode(f)

        # if no match, try again with parent directories prefixed
        parent = path
        while episode is None:
            nparent = os.path.dirname(parent)
            if nparent == parent:
                break
            parent = nparent

            pname = os.path.basename(parent)
            f = File(" ".join([pname, f.filename]))
            episode = self._find_episode(f)

        if episode is None:
            Renamer.log.warning("No match found for %s" % f)
            return

        Renamer.log.debug("%s matches %s" % (f, episode))

        valid_fname = "-_.()[]! %s%s" % (string.ascii_letters, string.digits)

        def format_fname(name):
            return "".join(c for c in name if c in valid_fname)

        # move episode to destination
        mapping = {
            "videos": config.config["settings"]["videos"][0],
            "t": format_fname(episode.show.title),
            "st": format_fname(episode.show.title),
            "et": format_fname(episode.title),
            "s": episode.season.num,
            "e": episode.num
        }
        if episode.season.title:
            mapping["st"] = format_fname(episode.season.title)

        dest = ".".join([pattern.format(**mapping), f.ext])
        dest_dir = os.path.dirname(dest)

        # create directory if necessary
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
            except OSError as e:
                Renamer.log.warning(
                    "Error creating directory %s: %s" % (dest_dir, str(e)))

        # copy across
        Renamer.log.info("Moving %s to %s" % (f, dest))
        if copy:
            shutil.copyfile(path, dest)
        else:
            shutil.move(path, dest)
        Renamer.log.info("Successfully moved %s" % f)

    def on_created(self, event):
        scheduler.add_asap(self.rename_file, event.src_path)
