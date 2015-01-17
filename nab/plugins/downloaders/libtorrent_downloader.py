""" Built-in libtorrent downloader. """
import libtorrent as lt
import threading
import time
import os
import appdirs
import yaml
import tempfile
import urllib2
from StringIO import StringIO
import gzip
import re

from nab.plugins.downloaders import Downloader
from nab.exception import PluginError


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

    """ Built-in downloader in nab using libtorrent. """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """ Make this a singleton, by jojo on StackOverflow. """
        if not cls._instance:
            cls._instance = super(Libtorrent, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, settings, options, args, ratio=2.0, ports=[6881, 6891]):
        """
        Create a libtorrent downloader.

        A singleton - I'm sorry, good design practices!

        Args:
            ratio (float): The upload:download target before deleting files.
            ports: ([int]): List of ports to use.
        """
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

        self.folder = settings["downloads"]
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
        if options.clean:
            # if 'clean' option enabled, then remove libtorrent file
            try:
                os.remove(libtorrent_file)
            except OSError:
                self.log.debug('Failed to remove libtorrent.yaml')
            else:
                self.log.debug('Removed litorrent.yaml')
        else:
            try:
                with file(libtorrent_file) as f:
                    data = yaml.load(f)
                    for torrent in data['torrents']:
                        self.download_url(torrent['tid'], torrent['tid'])
                        self.upload_total[torrent['tid']] = torrent['up']
                        self.download_total[torrent['tid']] = torrent['down']

                    self.session.load_state(data['state'])
            except IOError:
                self.log.debug("libtorrent.yaml not found")
            else:
                self.log.debug("Loaded from libtorrent.yaml")

        self.session.resume()

    def download_url(self, tid, url):
        # download torrent file
        handle, path = tempfile.mkstemp('.torrent')
        request = urllib2.Request(url)
        request.add_header('Accept-encoding', 'gzip')
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError:
            raise PluginError(self, "Error downloading torrent file")
        if response.info().get('Content-encoding') == 'gzip':
            buf = StringIO(response.read())
            f = gzip.GzipFile(fileobj=buf)
        os.write(handle, f.read())
        os.close(handle)
        torrent_info = lt.torrent_info(path)

        self._add_torrent(tid, torrent_info)

        # delete torrent file
        os.remove(path)

    def download_magnet(self, tid, magnet):
        # use magnet link
        infohash = re.search(r"\burn:btih:([A-F\d]+)\b", magnet).group()
        torrent_info = lt.torrent_info(infohash)
        self._add_torrent(tid, torrent_info)

    def get_download_status(self, tid):
        status = self.files[tid].status()

        data = {
            'progress': status.progress,
            'downspeed': status.download_rate,
            'upspeed': status.upload_rate,
            'num_seeds': status.num_seeds,
            'num_peers': status.num_peers,
            'completed': status.state in _completed_states
        }

        try:
            info = self.files[tid].get_torrent_info()
        except RuntimeError:
            # caused if no metadata acquired
            return {}
        else:
            data['size'] = info.total_size()

        return data

    def get_files(self, tid):
        """ Return the files in the torrent. """
        handle = self.files[tid]
        files = handle.get_torrent_info().files()
        return [os.path.join(handle.save_path(), f.path) for f in files]

    def _save_state(self):
        # write new state to file
        state = {
            'state': self.session.save_state(0x0ff),
            'torrents': [{'tid': f,
                          'up': self._get_upload_total(f),
                          'down': self._get_download_total(f)}
                         for f, h in self.files.iteritems()]
        }
        with file(libtorrent_file, 'w') as f:
            yaml.dump(state, f)

    def _get_ratio(self, tid):
        try:
            return (float(self._get_upload_total(tid)) /
                    float(self._get_download_total(tid)))
        except ZeroDivisionError:
            return 0.0

    def _get_upload_total(self, tid):
        return (self.upload_total[tid] +
                self.files[tid].status().all_time_upload)

    def _get_download_total(self, tid):
        return (self.download_total[tid] +
                self.files[tid].status().all_time_download)

    def _add_torrent(self, tid, torrent_info):
        if tid in self.files:
            # silently return if already downloading
            return

        handle = self.session.add_torrent({
            'save_path': self.folder, 'ti': torrent_info})

        self.downloads[handle] = tid
        self.files[tid] = handle
        self.upload_total[tid] = 0
        self.download_total[tid] = 0

        self._save_state()

    def _remove_torrent(self, tid):
        handle = self.files[tid]
        # 1 == delete files
        self.session.remove_torrent(handle, 1)
        del self.downloads[handle]
        del self.files[tid]
        del self.upload_total[tid]
        del self.download_total[tid]

    def _watch_thread(self):
        while True:
            time.sleep(1.0)

            self._progress_ticker += 1
            if self._progress_ticker >= 30:
                # save current torrent status
                self._save_state()
                self._progress_ticker = 0

            # check torrent ratios
            for h in list(self.downloads):
                try:
                    ratio = self._get_ratio(self.downloads[h])
                except KeyError:
                    # if torrent handle not in downloads
                    continue

                # delete files when over ratio and completed
                if (ratio >= self.ratio and
                   self.get_download_status(self.downloads[h])['completed']):
                    self._remove_torrent(self.downloads[h])
                    self.log.debug(
                        "%s reached seed ratio, deleting." % h.name())

                # test error state
                if h.status().error != '':
                    self.log.info(h.status().error)

            p = self.session.pop_alert()
            while p:
                if p.what() in ["torrent_finished_alert",
                                "torrent_added_alert"]:
                    self.log.info(p)
                    continue

                if (p.what() == "state_changed_alert" or
                   p.category() == lt.alert.category_t.error_notification):
                    self.log.debug(p)

                p = self.session.pop_alert()

Libtorrent.register('libtorrent', req_settings=True, req_options=True)
