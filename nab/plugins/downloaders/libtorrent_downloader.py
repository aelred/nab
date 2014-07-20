import libtorrent as lt
import threading
import time

from nab.downloader import Downloader
from nab.config import config


_state_str = {
    lt.torrent_status.states.queued_for_checking: 'Check Queue',
    lt.torrent_status.states.checking_files: 'Checking',
    lt.torrent_status.states.downloading_metadata: 'Metadata',
    lt.torrent_status.states.downloading: 'Downloading',
    lt.torrent_status.states.finished: 'Finished',
    lt.torrent_status.states.seeding: 'Seeding',
    lt.torrent_status.states.allocating: 'Allocating',
    lt.torrent_status.states.checking_resume_data: 'Resuming'
}


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
        size,
        _progress_bar(s.progress),
        '%d%%' % (s.progress * 100.0),
        '%s/s' % _sizeof_fmt(s.download_rate),
        handle.name()
    ])


class Libtorrent(Downloader):

    def __init__(self, ratio=2.0, ports=[6881, 6891]):
        self.session = lt.session()
        self.session.listen_on(*ports)

        self.downloads = set()
        self.urls = set()
        self.folder = config["settings"]["downloads"]
        threading.Thread(target=self._watch_thread).start()

        self.ratio = ratio
        settings = lt.session_settings()
        settings.share_ratio_limit = ratio
        self.session.set_settings(settings)

        self.session.set_alert_mask(
            lt.alert.category_t.error_notification |
            lt.alert.category_t.status_notification
            )

        self._progress_ticker = 0

    def download(self, file_):
        if file_.url in self.urls:
            # silently return if already downloading
            return

        handle = self.session.add_torrent({
            'save_path': self.folder,
            'url': file_.url})

        self.downloads.add(handle)
        self.urls.add(file_.url)

    def _watch_thread(self):
        while True:
            time.sleep(1.0)

            self._progress_ticker += 1
            # get list of active downloads
            downloads = [h for h in self.downloads
                         if h.status().state not in
                         [lt.torrent_status.states.seeding,
                          lt.torrent_status.states.finished]]
            # print progress only if active downloads
            if self._progress_ticker >= 30 and downloads:
                # print progress
                info_str = [_torrent_info(h) for h in self.downloads]
                self.log.info("\n".join(["Progress:"] + info_str))
                self._progress_ticker = 0

            p = self.session.pop_alert()
            if not p:
                continue

            if (p.what() == "torrent_finished_alert"):
                self.log.info(p)

                # move torrent to downloads directory
                p.handle.move_storage(config["settings"]["completed"])
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
                    # 1 == delete files
                    p.handle.remove_torrent(1)
                continue

            if p.category() == lt.alert.category_t.error_notification:
                self.log.debug(p)

Libtorrent.register('libtorrent')
