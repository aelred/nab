from itertools import chain
import time


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
