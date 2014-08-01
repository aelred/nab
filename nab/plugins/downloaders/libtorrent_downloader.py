import libtorrent as lt
import threading
import time
import os
import errno
import appdirs
import yaml

from nab.downloader import Downloader
from nab.config import config


_state_str = {
    lt.torrent_status.states.queued_for_checking: 'Check Queue',
    lt.torrent_status.states.checking_files: 'Checking',
    lt.torrent_status.states.downloading_metadata: 'Metadata',
    lt.torrent_status.states.downloading: 'Downloading',
    lt.torrent_status.states.finished: 'Finished',
    lt.torrent_status.states.seeding: 'Seeding ',
    lt.torrent_status.states.allocating: 'Allocating',
    lt.torrent_status.states.checking_resume_data: 'Resuming'
}

_completed_states = [lt.torrent_status.states.seeding,
                     lt.torrent_status.states.finished]


def _sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def _progress_bar(percent):
    length = 20
    filled = int(percent * length)
    unfilled = int(length - filled)
    return '[%s%s]' % ('=' * filled, ' ' * unfilled)


def _torrent_info(handle):
    s = handle.status()
    try:
        i = handle.get_torrent_info()
    except RuntimeError:
        # caused if no metadata acquired
        size = ''
    else:
        size = _sizeof_fmt(i.total_size())

    return '\t'.join([
        _state_str[s.state],
        size.ljust(10),  # pad with spaces to format neatly
        _progress_bar(s.progress),
        '%d%%' % (s.progress * 100.0),
        '%s/s' % _sizeof_fmt(s.download_rate),
        handle.name()
    ])


class Libtorrent(Downloader):

    def __init__(self, ratio=2.0, ports=[6881, 6891]):
        # create session
        self.session = lt.session()
        self.session.listen_on(*ports)

        self.downloads = {}
        self.files = {}

        self.folder = config["settings"]["downloads"]
        # begin thread to watch downloads
        threading.Thread(target=self._watch_thread).start()

        # set session options
        self.ratio = ratio
        settings = lt.session_settings()
        settings.share_ratio_limit = ratio
        self.session.set_settings(settings)

        self.session.set_alert_mask(
            lt.alert.category_t.error_notification |
            lt.alert.category_t.status_notification
            )

        self._progress_ticker = 0

        # reload persistent data
        data_dir = appdirs.user_data_dir('nab')
        self.data_file = os.path.join(data_dir, 'libtorrent.yaml')
        try:
            os.makedirs(data_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                self.log.error("Couldn't create directory %s" % data_dir)
                return
        try:
            with file(self.data_file) as f:
                data = yaml.load(f)
                for torrent in data['torrents']:
                    h = self._add_torrent(torrent['torrent'])
                    h.all_time_upload = torrent['up']
                    h.all_time_download = torrent['down']

                self.session.load_state(data['state'])
        except IOError:
            self.log.debug("libtorrent.yaml not found")
        else:
            self.log.debug("Loaded from libtorrent.yaml")

        self.session.resume()

    def download(self, torrent):
        self._add_torrent(torrent)
        self.save_state()

    def save_state(self):
        # write new state to file
        def ratio(h):
            s = h.status()
            try:
                return s.all_time_upload / s.all_time_download
            except ZeroDivisionError:
                return 0.0
        state = {
            'state': self.session.save_state(0x0ff),
            'torrents': [{'torrent': f,
                          'up': h.status().all_time_upload,
                          'down': h.status().all_time_download}
                         for f, h in self.files.iteritems()]
        }
        with file(self.data_file, 'w') as f:
            yaml.dump(state, f)

    def is_completed(self, torrent):
        return self.files[torrent].status().state in _completed_states

    def get_files(self, torrent):
        handle = self.files[torrent]
        files = handle.get_torrent_info().files()
        return [os.path.join(handle.save_path(), f.path) for f in files]

    def _add_torrent(self, torrent):
        if torrent in self.files:
            # silently return if already downloading
            return

        handle = self.session.add_torrent({
            'save_path': self.folder,
            'url': torrent.url})

        self.downloads[handle] = torrent
        self.files[torrent] = handle
        return handle

    def _remove_torrent(self, torrent):
        # 1 == delete files
        handle = self.files[torrent]
        handle.remove_torrent(1)
        del self.downloads[handle]
        del self.files[torrent]

    def _watch_thread(self):
        while True:
            time.sleep(1.0)

            self._progress_ticker += 1
            # get list of active downloads
            downloads = [h for h in self.downloads
                         if h.status().state not in _completed_states]
            # print progress only if active downloads
            if self._progress_ticker >= 30 and downloads:
                # save current torrent status
                self.save_state()
                # print progress
                info_str = [_torrent_info(h) for h in self.downloads]
                self.log.info("\n".join(["Progress:"] + info_str))
                self._progress_ticker = 0

            p = self.session.pop_alert()
            if not p:
                continue

            if (p.what() == "torrent_finished_alert"):
                self.log.info(p)
                continue

            if (p.what() == "torrent_added_alert"):
                self.log.info(p)
                continue

            if p.what() == "state_changed_alert":
                self.log.debug(p)

                status = p.handle.status()
                try:
                    ratio = status.all_time_upload / status.all_time_download
                except ZeroDivisionError:
                    ratio = 0.0

                # delete files when over ratio and completed
                if ratio >= self.ratio and p.handle.status().is_finished:
                    self._remove_torrent(self.downloads[p.handle])
                continue

            if p.category() == lt.alert.category_t.error_notification:
                self.log.debug(p)

Libtorrent.register('libtorrent')
