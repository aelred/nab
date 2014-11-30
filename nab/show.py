""" Handles TV shows. """
import re
from nab import show_elem, match, database, season


class Show(show_elem.ShowParentElem, show_elem.ShowElem):

    """ A TV show, part of a collection of ShowElem classes. """

    def __init__(self, title, ids=None, absolute=False, titles=None,
                 banner=None):
        """
        Create a TV show and automatically populate with data.

        Args:
            title (str): The title of the show.
            ids ({str: str or int}): A dictionary of IDs.
            absolute (bool): Whether this show uses absolute episode numbering.
            titles ([str]): An optional list of additional titles.
            banner (str): An optional url to a banner image of the show.
        """
        show_elem.ShowParentElem.__init__(self)
        show_elem.ShowElem.__init__(self, None, title, titles)
        self.ids = ids or {}
        self.absolute = absolute
        self.banner = banner

        # automatically get show data from database
        self.update_data()

    @property
    def show(self):
        """ Self. """
        return self

    @property
    def id(self):
        """ A probably-unique ID describing this episode. """
        return (re.sub(r'\W+', '', self.title),)

    def format(self):
        """ Format data in this show to make it easier to process. """
        # for all titles, remove bracketed year info
        # e.g. Archer (2009) -> Archer, Archer 2009, Archer (2009)
        newtitles = set()
        for t in set(self.titles):
            yearmatch = re.match(r"^(.*) \((\d+)\)$", t)
            if yearmatch:
                newtitles.add("%s %s" % yearmatch.group(1, 2))
                newtitles.add("%s" % yearmatch.group(1))
        self.titles.update(newtitles)

        show_elem.ShowParentElem.format(self)

        # remove any titles that conflict with season titles past season 1
        for se in self:
            if se == 1:
                continue
            for t in set(self.titles):
                ft = match.format_title(t)
                if ft in map(match.format_title, self[se].titles):
                    self.titles.remove(t)

    def merge(self, other):
        """ Merge data from another show into this one. """
        show_elem.ShowParentElem.__merge__(self, other)
        show_elem.ShowElem.__merge__(self, other)
        self.ids = dict(self.ids.items() + other.ids.items())

    def update_data(self):
        """ Get new data from databases for this show. """
        database.get_data(self)

    def to_yaml(self):
        """ Return a yaml representation of this show. """
        return {
            "id": self.id[0],
            "ids": self.ids,
            "titles": list(self.titles),
            "absolute": self.absolute,
            "seasons": show_elem.ShowParentElem.to_yaml(self),
            "banner": self.banner
        }

    @staticmethod
    def from_yaml(yml, title, parent):
        """ Create a show from the given yaml representation. """
        show = Show(title, yml["ids"], yml["absolute"], yml["titles"],
                    yml["banner"])
        show.update(show_elem.ShowParentElem.from_yaml(
            yml["seasons"], season.Season, show))
        return show

    def search_terms(self):
        """ Return a list of search terms to search for this show. """
        return set(map(match.format_title, self.titles))

    def match(self, f, total=True):
        """ Return true if the given File object matches this show. """
        if total:
            # filename must not match any season name (if seasons > 1)
            # e.g. Season 1 of a show has the same name as the show itself.
            #      Season 2 has a different name, then any torrent that matches
            #      the show name may just contain season 1, so we reject it.
            semax = max(self.keys())
            if (any(se.match(f, True) for se in self.values()) and semax > 1
               and f.season is None and f.episode is None):
                return False

            # there must be no episode number
            # or the file must give the full range of episodes
            epmax = len([ep for ep in self.episodes if ep.season.num != 0])
            if (f.episode is not None and
               (not self.absolute or f.episode != 1 or f.eprange != epmax)):
                return False

            # there must be no season number
            # or the file must give the full range of seasons (e.g. 1-4)
            if f.season is not None and (f.season != 1 or f.serange != semax):
                return False

        titles = map(match.format_title, self.titles)
        return match.format_title(f.title) in titles

    def __str__(self):
        """ Return a readable representation of this show. """
        return self.title.encode('utf-8')

    def __repr__(self):
        """ Return a readable, probably-unique representation. """
        return "<Show (%s)>" % str(self)
