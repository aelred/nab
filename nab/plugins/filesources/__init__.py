""" File source and filter plugins for finding and filtering torrent files. """

from nab.plugins import register


class FileSource(register.Entry):

    """ Plugin used for getting torrents for shows, seasons or episodes. """

    _register = register.Register()
    _type = "file source"

    def find(self, entry):
        """
        Return a list of files that match the given ShowElem.

        Most plugins should probably extend Searcher, which abstracts away
        some of this behaviour to simple searching for strings.

        Args:
            entry (ShowElem)

        Returns ([dict]):
            A list of search results.
            Each result should be of the form:
            {
                'filename': str,
                'url': str (optional),
                'magnet': str (optional),
                'seeds': int (optional)
            }

            A result must contain one or both of 'url' and 'magnet'.
        """
        raise NotImplementedError()


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
        raise NotImplementedError()


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
                A list stating what this plugin can match (i.e. what torrents
                it can return). Same options and defaults as search_by.
        """
        self.search_by = search_by or ["show", "season", "episode"]
        self.match_by = match_by or ["show", "season", "episode"]

    def search(self, term):
        """
        Search using the given search term.

        Args:
            term (str)

        Returns ([dict]):
            A list of search results.
            Each result should be of the form:
            {
                'filename': str,
                'url': str (optional),
                'magnet': str (optional),
                'seeds': int (optional)
            }

            A result must contain one or both of 'url' and 'magnet'.
        """
        raise NotImplementedError()

    def _search_all(self, s_terms, entry):
        # search under every title
        files = []
        for term in s_terms:
            self.__class__.log.debug('Searching "%s"' % term)
            results = self.search(term)
            files += results

        return files

    def find(self, entry):
        """
        Return a list of files matching the given ShowElem.

        If this Searcher does not support matching this particular ShowElem,
        returns an empty list.

        Args:
            entry (ShowElem)

        Returns ([dict]):
            A list of search results.
            Each result should be of the form:
            {
                'filename': str,
                'url': str (optional),
                'magnet': str (optional),
                'seeds': int (optional)
            }

            A result must contain one or both of 'url' and 'magnet'.
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
