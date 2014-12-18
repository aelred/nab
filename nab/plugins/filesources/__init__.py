""" File source and filter plugins for finding and filtering torrent files. """

from nab import register


class FileSource(register.Entry):

    """ Plugin used for getting torrents for shows, seasons or episodes. """

    _register = register.Register()
    _type = "file source"

    def find(self, entry):
        """
        Return a list of files.Torrent objects matching the given ShowElem.

        Most plugins should probably extend Searcher, which abstracts away
        some of this behaviour to simple searching for strings.
        """
        raise NotImplemented()


class FileFilter(register.Entry):

    """ Plugin used for filtering torrent files. """

    _register = register.Register()
    _type = "file filter"

    def filter(self, f):
        """
        Return a value indicating the acceptability of the given torrent.

        Values returned should be floats between 0 and 1, or the value None
        if the torrent should be rejected completely.

        A torrent is chosen based on the best average score across all
        given FileFilters.
        """
        raise NotImplemented()


class Searcher(FileSource):

    """
    Abstract plugin used for finding torrents from given search terms.

    Plugins should implement Searcher.search(term) and call constructor.
    """

    def __init__(self, search_by=None, match_by=None):
        """
        Create a Searcher with the given matching terms.

        Args:
            search_by ([str]):
                A list specifying whether this plugin can search by 'show',
                'season' or 'episode'. Defaults to all three.
            match_by ([str]):
                A list specifying what this plugin can match (i.e. what torrents
                it can return). Same options and defaults as search_by.
        """
        self.search_by = search_by or ["show", "season", "episode"]
        self.match_by = match_by or ["show", "season", "episode"]

    def search(self, terms):
        """
        Search using the given search term.

        Return a list of torrents.
        """
        raise NotImplemented()

    def _search_all(self, s_terms, entry):

        def valid_file(f):
            self.__class__.log.debug('Checking file %s' % f.filename)

            # title must not contain bad words!
            badwords = ["raw", "internal"]
            for tag in f.tags:
                if tag in badwords:
                    return False
                # no tags that are just numbers (avoiding obscure files)
                if re.match(r"\d+$", tag):
                    return False

            # there must be at least one seeder
            if f.seeds is not None and f.seeds == 0:
                return False

            match = entry.match(f)
            if match:
                self.__class__.log.debug('Valid file!')
            return match

        # search under every title
        files = []
        for term in s_terms:
            self.__class__.log.debug('Searching "%s"' % term)
            results = self.search(term)
            files += results

        return filter(valid_file, files)

    def find(self, entry):
        """
        Return a list of torrents matching the given ShowElem.

        If this Searcher does not support matching this particular ShowElem,
        returns an empty list.
        """
        # Only search for things this searcher supports
        for m in self.match_by:
            if entry.type == m:
                break
        else:
            return []

        # choose to search by show, season or episode
        s_terms = None
        if "episode" in self.search_by:
            try:
                s_terms = entry.episode.search_terms()
            except AttributeError:
                pass
        if s_terms is None and "season" in self.search_by:
            try:
                s_terms = entry.season.search_terms()
            except AttributeError:
                pass
        if s_terms is None and "show" in self.search_by:
            try:
                s_terms = entry.show.search_terms()
            except AttributeError:
                pass
        if s_terms is None:
            return

        # get results
        return self._search_all(s_terms, entry)

