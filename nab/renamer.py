import os
import os.path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
import string

from nab import config
from nab import log
from nab.files import File
from nab.scheduler import scheduler, tasks

path = config.config["settings"]["completed"]
pattern = config.config["renamer"]["pattern"]
copy = config.config["renamer"].get("copy", True)

_shows = None


def init(shows):
    global _shows
    _shows = shows
    renamer = Renamer()
    observer = Observer()
    observer.schedule(renamer, path, recursive=True)
    observer.start()


class Renamer(FileSystemEventHandler):
    log = log.log.getChild("renamer")

    def on_created(self, event):
        scheduler.add_asap("rename_file", event.src_path)


def _find_episode(file_):
    for ep in _shows.episodes:
        if ep.match(file_):
            return ep
    return None


def rename_file(path):
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

    if "sample" in f.filename.lower():
        Renamer.log.debug("Ignoring sample file %s" % f)
        return

    Renamer.log.debug("File created %s" % f)

    # look for a matching episode
    episode = _find_episode(f)

    # if no match, try again with parent directories prefixed
    parent = path
    while episode is None:
        nparent = os.path.dirname(parent)
        if nparent == parent:
            break
        parent = nparent

        pname = os.path.basename(parent)
        f = File(" ".join([pname, f.filename]))
        episode = _find_episode(f)

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
    try:
        if copy:
            shutil.copyfile(path, dest)
        else:
            shutil.move(path, dest)
    except IOError, e:
        Renamer.log.error(str(e))
        scheduler.add(5 * 60, "rename_file", path)
    else:
        Renamer.log.info("Successfully moved %s" % f)
tasks["rename_file"] = rename_file
