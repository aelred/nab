""" Module for file and torrent classes. """
import re

from nab import match


VIDEO_EXTS = ('mpg', 'mpe', 'mpeg', 'mp2v', 'm2v', 'm2s', 'avi', 'mov', 'qt',
              'asf', 'asx', 'wmv', 'wmx', 'rm', 'ram', 'rmvb', 'mp4', '3gp',
              'ogm', 'flv', 'mkv', 'ts', 'm4v')
SUB_EXTS = ('srt', 'sub', 'smi')


class File(object):

    """
    A file for a show, season or episode.

    Contains attributes extracted from the filename such as:
        filename: the original filename.
        title: the show title.
        season: season number.
        serange: season number upper range (e.g. 'seasons 1-3' -> serange=3).
        episode: episode number.
        eprange: episode number upper range (e.g. 'eps 14-15' -> eprange=15).
        eptitle: the episode title.
        ext: file extension.
        group: release group or fansub group.
        tags: a list of tags found in the filename (e.g. 'BRRip').
    """

    def __init__(self, filename, format_filename=True):
        """
        Create a File object from the given filename.

        >>> f = File('[PublicHD] Parks.and.Recreation.S06E21E22'
        ...          '.720p.HDTV.X264-DIMENSION.mkv')
        >>> f.filename
        '[PublicHD] Parks.and.Recreation.S06E21E22...'
        >>> f.title
        'parks and recreation'
        >>> f.season, f.serange
        (6, 6)
        >>> f.episode, f.eprange
        (21, 22)
        >>> f.eptitle
        >>> f.ext
        'mkv'
        >>> f.group
        'dimension'
        >>> '720p' in f.tags and 'hdtv' in f.tags and 'x264' in f.tags
        True

        Args:
            filename (str)
            format_filename (bool, True):
                If true, the filename is formatted to remove capital leters and
                common non-alphanumeric characters. This improves recognition,
                but means the resulting attributes such as 'title' will be
                lower case and have missing punctuation.
        """
        self.filename = filename

        data = File._split_filename(filename, format_filename)

        self.ext = None
        if 'ext' in data:
            self.ext = data['ext']

        self.group = None
        if 'group' in data:
            self.group = data['group']

        self.title = data['title']
        if format_filename:
            self.title = match.format_title(self.title)

        self.season = None
        if 'season' in data:
            self.season = int(data['season'])

        if 'serange' in data and data['serange'] is not None:
            self.serange = int(data['serange'])
        else:
            self.serange = self.season

        self.episode = None
        if 'episode' in data and data['episode'] is not None:
            self.episode = int(data['episode'])

        if 'eprange' in data and data['eprange'] is not None:
            self.eprange = int(data['eprange'])
        else:
            self.eprange = self.episode

        n_eps = None
        try:
            n_eps = self.eprange - self.episode
        except TypeError:
            pass

        self.eptitle = None
        # if this file contains three episodes or more,
        # it is likely a season or batch of episodes and
        # has no episode title
        if 'eptitle' in data and n_eps is not None and n_eps < 3:
            self.eptitle = data['eptitle']

        self.tags = data['tags']

    @staticmethod
    def _split_filename(filename, format_filename):
        if format_filename:
            filename = match.format_filename(filename)
        data = {"title": filename}

        data.update(File._split_ext(data["title"]))

        # check for group data at beginning or end
        group = File._split_group_end(data["title"])
        if not group:
            group = File._split_group_begin(data["title"])
        data.update(group)

        data.update(File._split_tags(data["title"]))
        data.update(File._split_numbering(data["title"]))

        return data

    @staticmethod
    def _split_numbering(title):
        mapping = {
            'div': r'[\s-]+',
            # we do not match episode numbers greater than 999
            # because they usually indicate a year.
            'eptxt': r'(ep?|(episodes?)? )',
            'ep': r'(?P<episode>\d{1,3})([-e](?P<eprange>\d{1,3}))?(v\d+)?',
            'eprange': r'(?P<episode>\d{1,3})-(?P<eprange>\d{1,3})(v\d+)?',
            'setxt': r'(s|seasons? )',
            'se': r'(?P<season>\d{1,3})(-(?P<serange>\d{1,3}))?',
            'year': r'\d{4}(-\d{4})?',
            'title': r'(?P<title>.*?)',
            'full': r'(full|complete)'
        }

        # Match 'Title - S01 E01 - Episode name', 'Title Season 01 Episode 01'
        num_re = (r'{title}{div}'
                  '{setxt}?{se} ?{eptxt}{ep}'
                  '({div}(?P<eptitle>.*))?$'.format(**mapping))
        match = re.match(num_re, title, re.I)
        if match:
            d = match.groupdict()
            if d["eptitle"] == "":
                del d["eptitle"]
            return d

        # Match 'Title - 01x01 - Episode name'
        num_re = (r'{title}{div}{se}x{ep}'
                  '({div}(?P<eptitle>.*))$'.format(**mapping))
        match = re.match(num_re, title, re.I)
        if match:
            d = match.groupdict()
            if d["eptitle"] == "":
                del d["eptitle"]
            return d

        # Match 'Title - Season 01'
        num_re = (r'{title}{div}'
                  '({full} )?{setxt}{se}'
                  '( {full})?$'.format(**mapping))
        match = re.match(num_re, title, re.I)
        if match:
            return match.groupdict()

        # Match 'Title - 04'
        num_re = (r'{title}{div}{eptxt}{ep}'
                  '({div}(?P<eptitle>.*))?$'.format(**mapping))
        match = re.match(num_re, title, re.I)
        if match:
            d = match.groupdict()
            if d["eptitle"] == "":
                del d["eptitle"]
            return d

        # Check if this matches common 'complete series' patterns
        # e.g. Avatar (Full 3 seasons), Breaking Bad (Complete series)
        #      FLCL 1-6 Complete series
        comp_re = (r'{title}{div}'            # title
                   '\(?\s*({eprange}{div})?'  # optional episode range
                   '{full}( ((\d+ )?(series|seasons|episodes)( {year})?)|$)'
                   .format(**mapping))
        match = re.match(comp_re, title, re.I)
        if match:
            d = match.groupdict()
            # ignore any given episode ranges
            del d['episode']
            del d['eprange']
            return d

        return {}

    @staticmethod
    def _split_ext(title):
        ext_re = r"(.*?)\s+\.?(%s)$" % '|'.join(VIDEO_EXTS + SUB_EXTS)
        match = re.match(ext_re, title, re.I)
        if match:
            return {"title": match.group(1), "ext": match.group(2)}

        return {}

    @staticmethod
    def _split_group_begin(title):
        group_begin_re = r"[\[\(\{](?P<group>.*?)[\]\)\}](?P<title>.*)$"
        match = re.match(group_begin_re, title, re.I)
        if match:
            return match.groupdict()

        return {}

    @staticmethod
    def _split_group_end(title):
        # if this title does not contain any tags then do not treat this as a
        # group title, this avoids issues when the title includes a hyphen
        # e.g. Psycho-Pass
        if not File._split_tags(title)['tags']:
            return {}

        group_end_re = (r'(?P<title>.*?)'
                        '(-\s*(?P<group>\w+))$')
        match = re.match(group_end_re, title, re.I)
        if match:
            return match.groupdict()

        return {}

    @staticmethod
    def _split_tags(title):
        tags = []

        # match tags in brackets, unless it is a year, e.g. Archer (2009)
        bracket_re = r"[\(\[\{]((?!\d{4}[\]\}\)]).*?)[\]\}\)]"
        split_re = r"[-_\s]+"
        match = re.findall(bracket_re, title, re.I)
        if match:
            title = re.sub(bracket_re, "", title, flags=re.I).strip()
            for m in match:
                tags += re.split(split_re, m, flags=re.I)

        tag_re = (r'(.*?)\s+'
                  '((?:bd|hdtv|proper|web-dl|x264|dd5.1|hdrip|dvdrip|xvid|'
                  'cd[0-9]|dvdscr|brrip|divx|batch|internal|specials|'
                  '\d{3,4}x\d{3,4}|\d{3,4}p).*?)$')
        match = re.match(tag_re, title, re.I)
        if match:
            title = match.group(1).strip()
            tags += re.split(split_re, match.group(2), flags=re.I)

        return {"title": title, "tags": tags}

    def __str__(self):
        """
        Return filename.

        >>> str(File('JoJos Bizarre Adventure (2012)'))
        'JoJos Bizarre Adventure (2012)'
        """
        return self.filename


class Torrent(File):

    """ Torrent, extending File with extra information about the torrent. """

    def __init__(self, filename, url=None, magnet=None, seeds=None):
        """
        Create a torrent from the given filename and optional links.

        >>> t_url = Torrent('My File', url='http://...', seeds=10)
        >>> t_mag = Torrent('My File', magnet='magnet:?xt=urn:sha1:...')
        >>> t_both = Torrent('My File', url='http://...',
        ...                  magnet='magnet:?xt=urn:sha1:...')

        Must provide either a url or magnet link:
        >>> Torrent('Cool File')
        Traceback (most recent call last):
            ...
        ValueError: Must specify a url or magnet link

        Args:
            filename (str):
                Filename or title identifying the torrent.
            url (str, None):
                URL to the torrent.
            magnet (str, None):
                Magnet link for this torrent.
            seeds (str, None):
                Number of seeds.
        """
        File.__init__(self, filename)

        if url is None and magnet is None:
            raise ValueError('Must specify a url or magnet link')

        self.url = url
        self.magnet = magnet
        self.seeds = seeds

    @property
    def id(self):
        """ Return unique identifier for this torrent. """
        return self.url or self.magnet

    def __str__(self):
        """
        Return representation including number of seeds.

        >>> str(File('My File', url='http://...')
        My File
        >>> str(File('My File', magnet='magnet:?xt=urn:sha1:...', seeds=5))
        My File (5 seeds)
        """
        if self.seeds:
            return "%s (%d seeds)" % (self.filename, self.seeds)
        else:
            return self.filename

    def __hash__(self):
        """ Return hash value based on id. """
        return hash(self.id)

    def __eq__(self, other):
        """ Return equality based on equality of ids. """
        try:
            return self.id == other.id
        except AttributeError:
            return False
