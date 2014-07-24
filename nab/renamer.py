import os
import os.path
import shutil
import string

from nab import config
from nab import log
from nab import files
from nab.scheduler import scheduler, tasks

pattern = config.config["renamer"]["pattern"]
copy = config.config["renamer"].get("copy", True)

_shows = None

_log = log.log.getChild("renamer")


def init(shows):
    global _shows
    _shows = shows


def _find_episode(file_):
    for ep in _shows.episodes:
        if ep.match(file_):
            return ep
    return None


def rename_file(path):
    # must be a file
    if not os.path.isfile(path):
        return

    f = files.File(os.path.basename(path))

    # must be a video file
    if not f.ext in files.video_exts + files.sub_exts:
        _log.debug("Ignoring non-video file %s" % f)
        return

    # check if this is a video file (as oppposed to e.g. a subtitle file)
    is_video = f.ext in files.video_exts

    if "sample" in f.filename.lower():
        _log.debug("Ignoring sample file %s" % f)
        return

    _log.debug("File created %s" % f)

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
        f = files.File(" ".join([pname, f.filename]))
        episode = _find_episode(f)

    if episode is None:
        _log.warning("No match found for %s" % f)
        return

    _log.debug("%s matches %s" % (f, episode))

    # mark episode as owned
    if is_video:
        episode.owned = True

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
            _log.warning(
                "Error creating directory %s: %s" % (dest_dir, str(e)))

    # copy across
    _log.info("Moving %s to %s" % (f, dest))
    try:
        if copy:
            shutil.copyfile(path, dest)
        else:
            shutil.move(path, dest)
    except IOError, e:
        _log.error(str(e))
        scheduler.add(5 * 60, "rename_file", path)
    else:
        _log.info("Successfully moved %s" % f)
tasks["rename_file"] = rename_file
