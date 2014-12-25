""" Handles TV show seasons. """
from nab import show_elem
from nab import match
from nab import episode
from nab import files


class Season(show_elem.ShowParentElem, show_elem.ShowElem):

    """ A TV season, part of a collection of ShowElem classes. """

    def __init__(self, databases, show, num, title=None, titles=None):
        """
        Create a season for a TV show.

        Args:
            show (Show): The show this season is part of.
            num (int): The season number within the show.
            title (str):
                The optional title of the season. Do not use 'Show - Season 2',
                this is for when the season title is distinct in some way,
                such as "BlackAdder Goes Forth".
            titles ([str]): An optional list of additional titles.
        """
        show_elem.ShowParentElem.__init__(self)
        show_elem.ShowElem.__init__(self, show, title, titles)
        self.num = num

        # automatically get season data from database
        self.update_data(databases)

    @property
    def type(self):
        """ Type of show element. """
        return "season"

    @property
    def season(self):
        """ Self. """
        return self

    @property
    def id(self):
        """ A probably-unique ID describing this season. """
        return self.show.id + (self.num,)

    def update_data(self, databases):
        """ Retrieve and add data for a season from database plugins. """

        def args():
            return {'show_titles': self.show.titles, 'show_ids': self.show.ids,
                    'season_num': self.num}

        # special season has no titles
        if self.num != 0:
            for db in databases:
                self.titles.update(db.get_season_titles(**args()))

        num_episodes = max([db.get_num_episodes(**args()) for db in databases]
                           + [0])

        for ep_num in range(1, num_episodes + 1):
            if ep_num not in self:
                self[ep_num] = episode.Episode(databases, self, ep_num)
            else:
                self[ep_num].update_data(databases)

        self._format()

    def to_yaml(self):
        """ Return a yaml representation of this season. """
        return {
            "title": self.title,
            "titles": list(self.titles),
            "episodes": show_elem.ShowParentElem.to_yaml(self)
        }

    @staticmethod
    def from_yaml(yml, num, show):
        """ Create a season from the given yaml representation. """
        season = Season([], show, num, yml["title"], yml["titles"])
        season.update(
            show_elem.ShowParentElem.from_yaml(
                yml["episodes"], episode.Episode, season))
        return season

    def names(self, full=False):
        """ Return a list of names describing this season. """
        names = []

        if self.num == 0 and not full:
            return []

        # add show name without season number for season 1 if only season
        if self.num == 1 and 2 not in self.show:
            names.append({"titles": self.show.search_terms()})

        names.append({"titles": self.show.search_terms(), "senum": self.num})

        if self.titles:
            # season has a title
            titles = set(map(match.format_title, self.titles))
            names[-1]["titles"].update(titles)
            names.append({"titles": titles})

        return names

    def search_terms(self):
        """ Return a list of search terms to search for this season. """
        terms = []
        for n in self.names():
            for t in n["titles"]:
                if t == "":
                    continue
                if "senum" in n:
                    terms.append("%s S%02d" % (t, n["senum"]))
                    terms.append("%s %d" % (t, n["senum"]))
                    terms.append("%s Season %d" % (t, n["senum"]))
                else:
                    terms.append(t)
        # if absolute numbered, add episode range as search term
        if self.show.absolute:
            for t in self.show.titles:
                terms.append("%s %d-%d" % (t,
                                           self.episodes[0].absolute,
                                           self.episodes[-1].absolute))
        return terms

    def match(self, name, total=True, format_name=True):
        """ Return true if the given File object matches this season. """
        parse = files.parse_name(name, format_name)
        # if this is a total match, there must be no episode number
        if total and 'episode' in parse:
            # if using absolute numbering, see if this file matches
            # this season's absolute episode numbers
            # must match against SHOW not season in this case
            try:
                start = self.episodes[0].absolute
            except IndexError:
                pass  # there are no episodes in this season
            else:
                if (self.show.absolute and
                   self.show.match(name, False, format_name) and
                   parse.get('episode') == start and
                   parse.get('eprange') == start + len(self) - 1):
                    return True

            # ...or episode range must match episodes in season
            if parse.get('episode') != 1 or parse.get('eprange') != len(self):
                return False

        titles = map(match.format_title, self.titles)

        return ((parse['title'] in titles and 'season' not in parse) or
                (self.show.match(name, False, format_name) and
                 parse.get('season') == self.num and
                 parse.get('serange') == self.num))

    def __str__(self):
        """ Return a readable representation of this season. """
        if self.title:
            return self.title.encode('utf-8')
        return ("%s - S%02d" % (self.show, self.num))

    def __repr__(self):
        """ Return a readable, probably-unique representation. """
        return "<Season (%s)>" % str(self)
