import libtorrent as lt
import threading
import time

from nab.downloader import Downloader
from nab.config import config


class Libtorrent(Downloader):

    def __init__(self, ratio=2.0, ports=[6881, 6891]):
        self.session = lt.session()
        self.session.listen_on(*ports)

        self.downloads = []
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
        handle = self.session.add_torrent({
            'save_path': self.folder,
            'url': file_.url})

        self.downloads.append(handle)

    def _progress_bar(self, percent):
        length = 20
        filled = int(percent * length)
        unfilled = int(length - filled)
        return '[%s%s]\t%d%%' % ('=' * filled, ' ' * unfilled, percent * 100.0)

    def _watch_thread(self):
        while True:
            time.sleep(1.0)

            self._progress_ticker += 1
            if self._progress_ticker >= 10:
                # print progress
                progress = [(d.name(), d.status().progress)
                            for d in self.downloads]
                info_str = ["%s\t%s" % (self._progress_bar(prog), n)
                            for n, prog in progress]
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
