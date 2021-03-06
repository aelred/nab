import libtorrent as lt
import threading
import time
import os
import errno
import appdirs
import yaml
import tempfile
import urllib2
from StringIO import StringIO
import gzip

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

libtorrent_file = os.path.join(appdirs.user_data_dir('nab'), 'libtorrent.yaml')


class Libtorrent(Downloader):

    _instance = None

    # make this a singleton
    # by jojo on StackOverflow
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Libtorrent, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, ratio=2.0, ports=[6881, 6891]):
        # create session
        self.session = lt.session()
        self.session.add_dht_router("router.bittorrent.com", 6881)
        self.session.start_dht()
        self.session.listen_on(*ports)
        self.session.start_upnp()
        self.session.start_natpmp()
        self.session.start_lsd()

        self.downloads = {}
        self.files = {}
        self.upload_total = {}
        self.download_total = {}

        self.folder = config["settings"]["downloads"]
        # begin thread to watch downloads
        thread = threading.Thread(target=self._watch_thread)
        thread.daemon = True
        thread.start()

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
        try:
            with file(libtorrent_file) as f:
                data = yaml.load(f)
                for torrent in data['torrents']:
                    self._add_torrent(torrent['torrent'])
                    self.upload_total[torrent['torrent']] = torrent['up']
                    self.download_total[torrent['torrent']] = torrent['down']

                self.session.load_state(data['state'])
        except IOError:
            self.log.debug("libtorrent.yaml not found")
        else:
            self.log.debug("Loaded from libtorrent.yaml")

        self.session.resume()

    def download(self, torrent):
        self._add_torrent(torrent)
        self.save_state()

    def get_size(self, torrent):
        try:
            i = self.files[torrent].get_torrent_info()
        except RuntimeError:
            # caused if no metadata acquired
            return 0
        else:
            return i.total_size()

    def get_progress(self, torrent):
        return self.files[torrent].status().progress
    
    def get_downspeed(self, torrent):
        return self.files[torrent].status().download_rate

    def get_upspeed(self, torrent):
        return self.files[torrent].status().upload_rate

    def get_num_seeds(self, torrent):
        return self.files[torrent].status().num_seeds

    def get_num_peers(self, torrent):
        return self.files[torrent].status().num_peers

    def save_state(self):
        # write new state to file
        state = {
            'state': self.session.save_state(0x0ff),
            'torrents': [{'torrent': f,
                          'up': self._get_upload_total(f),
                          'down': self._get_download_total(f)}
                         for f, h in self.files.iteritems()]
        }
        with file(libtorrent_file, 'w') as f:
            yaml.dump(state, f)

    def is_completed(self, torrent):
        return self.files[torrent].status().state in _completed_states

    def get_files(self, torrent):
        handle = self.files[torrent]
        files = handle.get_torrent_info().files()
        return [os.path.join(handle.save_path(), f.path) for f in files]

    def _get_ratio(self, torrent):
        try:
            return (float(self._get_upload_total(torrent)) /
                    float(self._get_download_total(torrent)))
        except ZeroDivisionError:
            return 0.0

    def _get_upload_total(self, torrent):
        return (self.upload_total[torrent] +
                self.files[torrent].status().all_time_upload)

    def _get_download_total(self, torrent):
        return (self.download_total[torrent] +
                self.files[torrent].status().all_time_download)

    def _add_torrent(self, torrent):
        if torrent in self.files:
            # silently return if already downloading
            return

        if torrent.url:
            # download torrent file
            handle, path = tempfile.mkstemp('.torrent')
            request = urllib2.Request(torrent.url)
            request.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(request)
            if response.info().get('Content-encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
            os.write(handle, f.read())
            os.close(handle)
            ti = lt.torrent_info(path)
        else:
            # use magnet link
            ti = lt.torrent_info(torrent.magnet)
        
        handle = self.session.add_torrent({
            'save_path': self.folder, 'ti': ti})

        if torrent.url:
            # delete torrent file
            os.remove(path)

        self.downloads[handle] = torrent
        self.files[torrent] = handle
        self.upload_total[torrent] = 0
        self.download_total[torrent] = 0

    def _remove_torrent(self, torrent):
        handle = self.files[torrent]
        # 1 == delete files
        self.session.remove_torrent(handle, 1)
        del self.downloads[handle]
        del self.files[torrent]
        del self.upload_total[torrent]
        del self.download_total[torrent]

    def _watch_thread(self):
        while True:
            time.sleep(1.0)

            self._progress_ticker += 1
            if self._progress_ticker >= 30:
                # save current torrent status
                self.save_state()
                self._progress_ticker = 0

            # check torrent ratios
            for h in list(self.downloads):
                try:
                    ratio = self._get_ratio(self.downloads[h])
                except KeyError:
                    # if torrent handle not in downloads
                    continue

                # delete files when over ratio and completed
                if ratio >= self.ratio and h.status().is_finished:
                    self._remove_torrent(self.downloads[h])
                    self.log.debug(
                        "%s reached seed ratio, deleting." % h.name())

                # test error state
                if h.status().error != '':
                    self.log.info(h.status().error)

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

            if p.category() == lt.alert.category_t.error_notification:
                self.log.debug(p)

Libtorrent.register('libtorrent')
