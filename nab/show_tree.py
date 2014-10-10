from itertools import chain
import re
import yaml
import time
import appdirs
import os

from nab import match


shows_file = os.path.join(appdirs.user_data_dir('nab'), 'shows.yaml')


class ShowElem(object):
    def __init__(self, parent, title, titles):
        self.parent = parent
        self.title = title
        self.titles = set()
        if titles:
            self.titles.update(titles)
        if self.title:
            self.titles.add(self.title)

    @property
    def show(self):
        return self.parent.show

    @property
    def season(self):
        return self.parent.season

    def has_aired(self):
        # add an extra day to account for timezones
        if self.aired_max > time.time() + 60 * 60 * 24:
            return False

        if self.aired is not None:
            return True

        return False

    def merge(self, other):
        if self.title is None:
            self.title = other.title
        self.titles.update(other.titles)

    def format(self):
        pass

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.id)


class ShowParentElem(dict):

    def __init__(self):
        dict.__init__(self)

    def merge(self, other):
        for key in other:
            if key in self:
                self[key].merge(other[key])
            else:
                self[key] = other[key]

    @property
    def epwanted(self):
        return [ep for ep in self.episodes if ep.wanted]

    @property
    def aired(self):
        airdates = [ep.aired for ep in self.episodes if ep.aired is not None]
        if len(airdates):
            return min(airdates)
        else:
            return None

    @property
    def aired_max(self):
        airdates = [ep.aired for ep in self.episodes if ep.aired is not None]
        if len(airdates):
            return max(airdates)
        else:
            return None

    @property
    def wanted(self):
        eps = [e for e in self.episodes if e.season.num != 0]
        wanted = [e for e in self.epwanted if e.season.num != 0]
        if len(eps) == 0:
            return False
        return float(len(wanted)) / float(len(eps)) > 0.75

    @property
    def episodes(self):
        return list(chain(*[self[child].episodes for child in sorted(self)]))

    def format(self):
        for child in self.itervalues():
            child.format()

    def to_yaml(self):
        return dict([(k, v.to_yaml()) for k, v in self.iteritems()])

    @staticmethod
    def from_yaml(yml, child_type, parent):
        return dict([(k, child_type.from_yaml(v, k, parent))
                     for k, v in yml.iteritems()])

    def find(self, id_):
        if self.id != id_[0:len(self.id)]:
            return None
        if id_ == self.id:
            return self

        for child in self.itervalues():
            f = child.find(id_)
            if f is not None:
                return f

        return None


class ShowTree(ShowParentElem):

    def __init__(self):
        ShowParentElem.__init__(self)
        try:
            with file(shows_file, 'r') as f:
                self.update(ShowTree.from_yaml(yaml.load(f), Show, self))
        except IOError:
            pass  # no shows.yaml file, doesn't matter!

    def find(self, id_):
        if isinstance(id_, str):
            id_ = (id_,)

        for child in self.itervalues():
            f = child.find(id_)
            if f is not None:
                return f

    def save(self):
        yaml.safe_dump(self.to_yaml(), file(shows_file, 'w'))

    def to_yaml(self):
        return ShowParentElem.to_yaml(self)


class Show(ShowParentElem, ShowElem):
    def __init__(self, title, ids=None, absolute=False, titles=None):
        ShowParentElem.__init__(self)
        ShowElem.__init__(self, None, title, titles)
        self.ids = ids or {}
        self.absolute = absolute

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

        ShowParentElem.format(self)

        # remove any titles that conflict with season titles past season 1
        for season in self:
            if season == 1:
                continue
            for t in set(self.titles):
                ft = match.format_title(t)
                if ft in map(match.format_title, self[season].titles):
                    self.titles.remove(t)

    def merge(self, other):
        ShowParentElem.__merge__(self, other)
        ShowElem.__merge__(self, other)
        self.ids = dict(self.ids.items() + other.ids.items())

    def to_yaml(self):
        return {
            "ids": self.ids,
            "titles": list(self.titles),
            "absolute": self.absolute,
            "seasons": ShowParentElem.to_yaml(self)
        }

    @staticmethod
    def from_yaml(yml, title, parent):
        show = Show(title, yml["ids"], yml["absolute"], yml["titles"])
        show.update(ShowParentElem.from_yaml(yml["seasons"], Season, show))
        return show

    def search_terms(self):
        return set(map(match.format_title, self.titles))

    def match(self, f, total=True):
        # filename must not match any season
        # e.g. Season 1 of a show has the same name as the show itself.
        #      Season 2 has a different name, then any torrent that matches
        #      the show name may just contain season 1, so we reject it.
        if total and any(s.match(f, True) for s in self.values()):
            return False

        if total and not (f.season is None and f.episode is None):
            return False

        titles = map(match.format_title, self.titles)
        return match.format_title(f.title) in titles

    def __eq__(self, other):
        return ShowElem.__eq__(self, other)

    def __str__(self):
        return self.title.encode('utf-8')

    def __repr__(self):
        return "<Show (%s)>" % str(self)


class Season(ShowParentElem, ShowElem):
    def __init__(self, show, num, title=None, titles=None):
        ShowParentElem.__init__(self)
        ShowElem.__init__(self, show, title, titles)
        self.num = num

    @property
    def season(self):
        return self

    @property
    def id(self):
        return self.show.id + (self.num,)

    def merge(self, season):
        ShowParentElem.merge(self, season)
        ShowElem.merge(self, season)

    def to_yaml(self):
        return {
            "title": self.title,
            "titles": list(self.titles),
            "episodes": ShowParentElem.to_yaml(self)
        }

    @staticmethod
    def from_yaml(yml, num, show):
        season = Season(show, num, yml["title"], yml["titles"])
        season.update(
            ShowParentElem.from_yaml(yml["episodes"], Episode, season))
        return season

    def names(self, full=False):
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
        return terms

    def match(self, f, total=True):
        if total and f.episode is not None:
            return False

        return ((f.title in map(match.format_title, self.titles)
                 and f.season is None) or
                (self.show.match(f, False) and f.season == self.num))

    def __eq__(self, other):
        return ShowElem.__eq__(self, other)

    def __str__(self):
        if self.title:
            return self.title.encode('utf-8')
        return ("%s - S%02d" % (self.show, self.num))

    def __repr__(self):
        return "<Season (%s)>" % str(self)


class Episode(ShowElem):
    def __init__(self, season, num, title, aired, titles=None):
        ShowElem.__init__(self, season, title, titles)
        self.num = num
        self.owned = False
        self.watched = False
        self.wanted = True
        self.aired = aired

    def __repr__(self):
        return "<Episode (%s)>" % str(self)

    @ShowElem.season.setter
    def season(self, value):
        self.parent = value

    @property
    def episode(self):
        return self

    @property
    def episodes(self):
        return [self]

    @property
    def absolute(self):
        if self.season.num == 0:
            return None
        eps = [ep for ep in self.show.episodes if ep.season.num != 0]
        return eps.index(self) + 1

    @property
    def previous(self):
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
        if self.season.num == 0:
            return None
        if self.season.num == len(self.show)-1:
            return None

        if self.num == len(self.season.episodes)-1:
            return self.show[self.season.num+1][1]

        return self.season[self.num+1]

    @property
    def aired_max(self):
        return self.aired

    @property
    def id(self):
        return self.season.id + (self.num,)

    @property
    def epwanted(self):
        if self.wanted:
            return [self]
        else:
            return []

    def has_aired(self):
        if ShowElem.has_aired(self):
            return True

        if self.season.num == 0:
            return True

    def merge(self, episode):
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

        ShowElem.merge(self, episode)

    def to_yaml(self):
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
        ep = Episode(season, num, yml["title"], yml["aired"], yml["titles"])
        ep.owned = yml["owned"]
        ep.watched = yml["watched"]
        ep.wanted = yml["wanted"]
        return ep

    def find(self, id_):
        if self.id == id_:
            return self
        else:
            return None

    def names(self, full=False):
        names = self.season.names(full)
        for n in names:
            n["epnum"] = self.num

        titles = self.show.search_terms()

        # absolute numbering
        if self.season.show.absolute and self.season.num != 0:
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

    def match(self, f):
        if self.season.num == 0:
            titles = [" ".join([match.format_title(t), self.title])
                      for t in self.show.titles]
            return f.title in titles

        if (self.show.absolute and f.season is None and
           self.show.match(f, False) and f.episode == self.absolute):
            return True

        return self.season.match(f, False) and f.episode == self.num

    def __str__(self):
        if self.season.num == 0:
            return ("%s - %s" % (self.show, self.title.encode('utf-8')))
        if self.season.title:
            return ("%s - %02d" % (self.season, self.num))
        return ("%sE%02d" % (self.season, self.num))
