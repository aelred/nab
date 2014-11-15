import re
from nab import show_elem, match, database, season


class Show(show_elem.ShowParentElem, show_elem.ShowElem):
    def __init__(self, title, ids=None, absolute=False, titles=None):
        show_elem.ShowParentElem.__init__(self)
        show_elem.ShowElem.__init__(self, None, title, titles)
        self.ids = ids or {}
        self.absolute = absolute

        # automatically get show data from database
        self.update_data()

    @property
    def show(self):
        return self

    @property
    def id(self):
        return (self.title,)

    def format(self):
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
        show_elem.ShowParentElem.__merge__(self, other)
        show_elem.ShowElem.__merge__(self, other)
        self.ids = dict(self.ids.items() + other.ids.items())

    def update_data(self):
        # get new data from database for this show
        database.get_data(self)

    def to_yaml(self):
        return {
            "ids": self.ids,
            "titles": list(self.titles),
            "absolute": self.absolute,
            "seasons": show_elem.ShowParentElem.to_yaml(self)
        }

    @staticmethod
    def from_yaml(yml, title, parent):
        show = Show(title, yml["ids"], yml["absolute"], yml["titles"])
        show.update(show_elem.ShowParentElem.from_yaml(
            yml["seasons"], season.Season, show))
        return show

    def search_terms(self):
        return set(map(match.format_title, self.titles))

    def match(self, f, total=True):
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

    def __eq__(self, other):
        return show_elem.ShowElem.__eq__(self, other)

    def __str__(self):
        return self.title.encode('utf-8')

    def __repr__(self):
        return "<Show (%s)>" % str(self)
