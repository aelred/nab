""" Handles TV show episodes. """
from nab import show_elem, match


class Episode(show_elem.ShowElem):

    """ A TV show episode, part of a collection of ShowElem classes.  """

    def __init__(self, season, num, title, aired, titles=None):
        """
        Create a TV episode for a season.

        Args:
            season (Season): The season this episode is part of.
            num (int): The episode number within the season.
            title (str): The title of the episode.
            aired (int): When this episode aired in UNIX time.
            titles ([str]): An optional list of additional titles.
        """
        show_elem.ShowElem.__init__(self, season, title, titles)
        self.num = num
        self.owned = False
        self.watched = False
        self.wanted = True
        self.aired = aired

    def __repr__(self):
        """ Return a readable, probably-unique representation. """
        return "<Episode (%s)>" % str(self)

    @show_elem.ShowElem.season.setter
    def season(self, value):
        """ Set the episode season. This should usually only be done once. """
        self.parent = value

    @property
    def episode(self):
        """ Self. """
        return self

    @property
    def episodes(self):
        """ A list containing self. """
        return [self]

    @property
    def absolute(self):
        """ The absolute number of the episode. """
        if self.season.num == 0:
            return None
        eps = [ep for ep in self.show.episodes if ep.season.num != 0]
        return eps.index(self) + 1

    @property
    def previous(self):
        """ The episode before this, or None if no episode exists. """
        if self.season.num == 0:
            return None
        if self.season.num == 1 and self.num == 1:
            return None

        if self.num == 1:
            season = self.show[self.season.num-1]
            return season[len(season.episodes)-1]

        return self.season[self.num-1]

    @property
    def next(self):
        """ The episode after this, or None if no episode exists. """
        if self.season.num == 0:
            return None
        if self.season.num == len(self.show)-1:
            return None

        if self.num == len(self.season.episodes)-1:
            return self.show[self.season.num+1][1]

        return self.season[self.num+1]

    @property
    def aired_max(self):
        """ The latest airtime of this episode (which is just the airtime). """
        return self.aired

    @property
    def id(self):
        """ A probably-unique ID describing this episode. """
        return self.season.id + (self.num,)

    @property
    def epwanted(self):
        """ A list containing all episodes wanted in this episode. """
        if self.wanted:
            return [self]
        else:
            return []

    def has_aired(self):
        """
        Whether this episode has aired.

        Specials are always assumed to have aired because the airdates of
        special episodes are very unreliable and variable.
        """
        if show_elem.ShowElem.has_aired(self):
            return True

        if self.season.num == 0:
            return True

    def merge(self, episode):
        """ Merge data from another episode into this one. """
        if episode.owned:
            self.owned = True
        if episode.watched:
            self.watched = True
        if episode.wanted:
            self.wanted = True

        # take earliest existent airdate
        if (episode.aired is not None and
           (self.aired is None or episode.aired < self.aired)):
            self.aired = episode.aired

        show_elem.ShowElem.merge(self, episode)

    def to_yaml(self):
        """ Return a yaml representation of this episode. """
        return {
            "title": self.title,
            "titles": list(self.titles),
            "aired": self.aired,
            "owned": self.owned,
            "watched": self.watched,
            "wanted": self.wanted
        }

    @staticmethod
    def from_yaml(yml, num, season):
        """ Create an episode from the given yaml representation. """
        ep = Episode(season, num, yml["title"], yml["aired"], yml["titles"])
        ep.owned = yml["owned"]
        ep.watched = yml["watched"]
        ep.wanted = yml["wanted"]
        return ep

    def find(self, id_):
        """ Search for a ShowElem id in this episode. """
        if self.id == id_:
            return self
        else:
            return None

    def names(self, full=False):
        """ Return a list of names describing this episode. """
        names = self.season.names(full)
        for n in names:
            n["epnum"] = self.num

        titles = self.show.search_terms()

        # absolute numbering
        if self.season.show.absolute and self.season.num != 0:
            # using season title
            absnames = self.season.names(full)
            for n in absnames:
                n["epnum"] = self.absolute
            names += absnames
            # using show title
            names.append({
                "titles": titles,
                "epnum": self.absolute
            })

        # search episode titles for specials
        if self.season.num == 0:
            names.append({
                "titles": titles,
                "eptitles": set(map(match.format_title, self.titles))
            })

        return names

    def search_terms(self):
        """ Return a list of search terms to search for this episode. """
        terms = []
        for n in self.names():
            for t in n["titles"]:
                if t == "":
                    continue
                if "senum" in n and "epnum" in n:
                    terms.append("%s S%02dE%02d" % (t, n["senum"], n["epnum"]))
                    terms.append("%s %dx%d" % (t, n["senum"], n["epnum"]))
                if "senum" not in n and "epnum" in n:
                    terms.append("%s %02d" % (t, n["epnum"]))
                if "eptitles" in n:
                    terms += ["%s %s" % (t, et)
                              for et in n["eptitles"] if et != ""]
        return terms

    def match(self, f, total=True):
        """ Return true if the given File object matches this episode. """
        # match by title if a special
        if self.season.num == 0:
            titles = [" ".join([match.format_title(t), self.title])
                      for t in self.show.titles]
            return f.title in titles

        # match by absolute number if using absolute numbering or season 1
        if ((self.show.absolute or self.season.num == 1) and f.season is None
           and self.show.match(f, False)
           and self.absolute >= f.episode and self.absolute <= f.eprange):
            return True

        # match if season matches and episode matches
        return (self.season.match(f, False)
                and self.num >= f.episode and self.num <= f.eprange)

    def __str__(self):
        """ Return a readable representation of this episode. """
        if self.season.num == 0:
            return ("%s - %s" % (self.show, self.title.encode('utf-8')))
        if self.season.title:
            return ("%s - %02d" % (self.season, self.num))
        return ("%sE%02d" % (self.season, self.num))
