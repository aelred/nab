""" Module used for renaming and moving downloaded video files. """
import os
import os.path
import shutil
import string

from nab import files


class Renamer:

    def __init__(self, renamer_log, scheduler, config, shows):
        self._scheduler = scheduler
        self._config = config
        self._shows = shows
        self._log = renamer_log
        self._scheduler.tasks['rename_file'] = self.rename_file

    def _videos_path(self):
        return self._config.config['settings']['videos']

    def _pattern(self):
        return self._config.config['renamer']['pattern']

    def _copy(self):
        return self._config.config['renamer']['copy']

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
            "videos": self._videos_path(),
            "t": format_fname(episode.show.title),
            "st": format_fname(episode.show.title),
            "et": format_fname(episode.title),
            "s": "%02d" % episode.season.num,
            "e": epnum
        }
        if episode.season.title:
            mapping["st"] = format_fname(episode.season.title)

        return ".".join([self._pattern().format(**mapping), file_.ext])

    def _move_file(self, origin, dest):
        dest_dir = os.path.dirname(dest)

        # create directory if necessary
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
            except OSError as e:
                self._log.warning(
                    "Error creating directory %s: %s" % (dest_dir, str(e)))
                return False

        try:
            if self._copy():
                shutil.copyfile(origin, dest)
            else:
                shutil.move(origin, dest)
        except IOError, e:
            self._log.error(str(e))
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
            self._log.debug("Ignoring non-video file %s" % f)
            return

        # check if this is a video file (as oppposed to e.g. a subtitle file)
        is_video = f.ext in files.VIDEO_EXTS

        if "sample" in f.filename.lower():
            self._log.debug("Ignoring sample file %s" % f)
            return

        self._log.debug("File created %s" % f)

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
            self._log.warning("No match found for %s" % f)
            return

        self._log.debug("%s matches %s" % (f, episode))

        dest = self._new_name(f, episode)

        self._log.info("Moving %s to %s" % (f, dest))

        if self._move_file(path, dest):
            self._log.info("Successfully moved %s" % f)

            # mark episode as owned
            if is_video:
                episode.owned = True
        else:
            # retry again later
            self._scheduler.add(5 * 60, "rename_file", path)
