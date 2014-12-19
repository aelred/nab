""" Module used for renaming and moving downloaded video files. """
import os
import os.path
import shutil
import string

from nab import log
from nab import files
from nab import scheduler

_log = log.log.getChild("renamer")


def _find_episode(file_, shows):
    for ep in shows.episodes:
        if ep.match(file_):
            return ep
    return None


def _new_name(file_, episode, videos_path, pattern):
    # valid range of characters for a filename
    valid_fname = "-_.()[]! %s%s" % (string.ascii_letters, string.digits)

    def format_fname(name):
        # eliminate invalid filename characters
        return "".join(c for c in name if c in valid_fname)

    # check if file is a range of episodes (e.g. a two-parter)
    if file_.episode is not None and file_.episode == file_.eprange:
        epnum = "%02d" % episode.num
    else:
        epnum = "%02d-%02d" % (file_.episode, file_.eprange)

    # format pattern with episode information
    mapping = {
        "videos": videos_path,
        "t": format_fname(episode.show.title),
        "st": format_fname(episode.show.title),
        "et": format_fname(episode.title),
        "s": "%02d" % episode.season.num,
        "e": epnum
    }
    if episode.season.title:
        mapping["st"] = format_fname(episode.season.title)

    return ".".join([pattern.format(**mapping), file_.ext])


def _move_file(origin, dest, copy):
    dest_dir = os.path.dirname(dest)

    # create directory if necessary
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError as e:
            _log.warning(
                "Error creating directory %s: %s" % (dest_dir, str(e)))
            return False

    try:
        if copy:
            shutil.copyfile(origin, dest)
        else:
            shutil.move(origin, dest)
    except IOError, e:
        _log.error(str(e))
        return False
    else:
        return True


def rename_file(path, scheduler, shows, pattern, videos_path, copy):
    """ Rename and move the video file on the given path. """
    # must be a file
    if not os.path.isfile(path):
        return

    f = files.File(os.path.basename(path))

    # must be a video file
    if f.ext not in files.video_exts + files.sub_exts:
        _log.debug("Ignoring non-video file %s" % f)
        return

    # check if this is a video file (as oppposed to e.g. a subtitle file)
    is_video = f.ext in files.video_exts

    if "sample" in f.filename.lower():
        _log.debug("Ignoring sample file %s" % f)
        return

    _log.debug("File created %s" % f)

    # look for a matching episode
    episode = _find_episode(f, shows)

    # if no match, try again with parent directories prefixed
    parent = path
    while episode is None:
        nparent = os.path.dirname(parent)
        if nparent == parent:
            break
        parent = nparent

        pname = os.path.basename(parent)
        f = files.File(" ".join([pname, f.filename]))
        episode = _find_episode(f, shows)

    if episode is None:
        _log.warning("No match found for %s" % f)
        return

    _log.debug("%s matches %s" % (f, episode))

    dest = _new_name(f, episode, videos_path, pattern)

    _log.info("Moving %s to %s" % (f, dest))

    if _move_file(path, dest, copy):
        _log.info("Successfully moved %s" % f)

        # mark episode as owned
        if is_video:
            episode.owned = True
    else:
        # retry again later
        scheduler.add(5 * 60, "rename_file", path, scheduler, shows,
                      videos_path, copy)

scheduler.tasks["rename_file"] = rename_file
