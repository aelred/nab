""" Module used for renaming and moving downloaded video files. """
import os
import os.path
import shutil
import string
import logging

from nab import files

_LOG = logging.getLogger(__name__)


class Renamer:

    def __init__(self, videos_path, settings, shows):
        self.videos_path = videos_path
        self.settings = settings
        self._shows = shows

    def _find_episode(self, file_):
        for ep in self._shows.episodes:
            if ep.match(file_):
                return ep
        return None

    def _new_name(self, file_, episode):
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
            "videos": self.videos_path,
            "t": format_fname(episode.show.title),
            "st": format_fname(episode.show.title),
            "et": format_fname(episode.title),
            "s": "%02d" % episode.season.num,
            "e": epnum
        }
        if episode.season.title:
            mapping["st"] = format_fname(episode.season.title)

        return ".".join([self.settings['pattern'].format(**mapping),
                         file_.ext])

    def _move_file(self, origin, dest):
        dest_dir = os.path.dirname(dest)

        # create directory if necessary
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
            except OSError as e:
                _LOG.warning(
                    "Error creating directory %s: %s" % (dest_dir, str(e)))
                return False

        try:
            if self.settings['copy']:
                shutil.copyfile(origin, dest)
            else:
                shutil.move(origin, dest)
        except IOError, e:
            _LOG.error(str(e))
            return False
        else:
            return True

    def rename_file(self, path):
        """ Rename and move the video file on the given path. """
        # must be a file
        if not os.path.isfile(path):
            return

        f = files.File(os.path.basename(path))

        # must be a video file
        if f.ext not in files.VIDEO_EXTS + files.SUB_EXTS:
            _LOG.debug("Ignoring non-video file %s" % f)
            return

        # check if this is a video file (as oppposed to e.g. a subtitle file)
        is_video = f.ext in files.VIDEO_EXTS

        if "sample" in f.filename.lower():
            _LOG.debug("Ignoring sample file %s" % f)
            return

        _LOG.debug("File created %s" % f)

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
            f = files.File(" ".join([pname, f.filename]))
            episode = self._find_episode(f)

        if episode is None:
            _LOG.warning("No match found for %s" % f)
            return

        _LOG.debug("%s matches %s" % (f, episode))

        dest = self._new_name(f, episode)

        _LOG.info("Moving %s to %s" % (f, dest))

        if self._move_file(path, dest):
            _LOG.info("Successfully moved %s" % f)

            # mark episode as owned
            if is_video:
                episode.owned = True
        else:
            # retry again later
            self._rename_file_sched('delay', 5 * 60, path)
