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

    def _find_episode(self, name):
        for ep in self._shows.episodes:
            if ep.match(name):
                return ep
        return None

    def _new_name(self, name, episode):
        # valid range of characters for a filename
        valid_fname = "-_.()[]! %s%s" % (string.ascii_letters, string.digits)
        file_ = files.parse_name(name)

        def format_fname(name):
            # eliminate invalid filename characters
            return "".join(c for c in name if c in valid_fname)

        # check if file is a range of episodes (e.g. a two-parter)
        if 'episode' in file_ and file_['episode'] == file_.get('eprange'):
            epnum = "%02d" % episode.num
        else:
            epnum = "%02d-%02d" % (file_['episode'], file_['eprange'])

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
                         file_['ext']])

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
        """
        Rename and move the video file on the given path.

        Return true if successful.
        """
        # must be a file
        if not os.path.isfile(path):
            return True

        name = os.path.basename(path)
        ext = os.path.splitext(name)[1]

        # must be a video file
        if ext not in files.VIDEO_EXTS + files.SUB_EXTS:
            _LOG.debug("Ignoring non-video file %s" % name)
            return True

        # check if this is a video file (as oppposed to e.g. a subtitle file)
        is_video = ext in files.VIDEO_EXTS

        if "sample" in name.lower():
            _LOG.debug("Ignoring sample file %s" % name)
            return True

        _LOG.debug("File created %s" % name)

        # look for a matching episode
        episode = self._find_episode(name)

        # if no match, try again with parent directories prefixed
        parent = path
        while episode is None:
            nparent = os.path.dirname(parent)
            if nparent == parent:
                break
            parent = nparent

            pname = os.path.basename(parent)
            name = " ".join([pname, name])
            episode = self._find_episode(name)

        if episode is None:
            _LOG.warning("No match found for %s" % name)
            return False

        _LOG.debug("%s matches %s" % (name, episode))

        dest = self._new_name(name, episode)

        _LOG.info("Moving %s to %s" % (name, dest))

        if self._move_file(path, dest):
            _LOG.info("Successfully moved %s" % name)

            # mark episode as owned
            if is_video:
                episode.owned = True

            return True
        else:
            return False
