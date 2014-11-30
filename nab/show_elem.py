""" Module for ShowElem, which represents an abstract TV show element. """
from itertools import chain
import time


class ShowElem(object):

    """ An abstract TV show element. """

    def __init__(self, parent, title, titles):
        """
        Create a new ShowElem.

        Args:
            parent (ShowParentElem): The parent show element (e.g. a TV season).
            title (str): The title of this show element.
            title ([str)): A list of additional titles.
        """
        self.parent = parent
        self.title = title
        self.titles = set()
        if titles:
            self.titles.update(titles)
        if self.title:
            self.titles.add(self.title)

    @property
    def show(self):
        """ The show this element is part of. """
        return self.parent.show

    @property
    def season(self):
        """ The season this element is part of. """
        return self.parent.season

    def has_aired(self):
        """ Return true if this show element has already aired. """
        # add an extra day to account for timezones
        if self.aired_max > time.time() + 60 * 60 * 24:
            return False

        if self.aired is not None:
            return True

        return False

    def merge(self, other):
        """ Merge data from another ShowElem into this ShowElem. """
        if self.title is None:
            self.title = other.title
        self.titles.update(other.titles)

    def format(self):
        """ Format this ShowElem to be easier to process. """
        pass

    def __eq__(self, other):
        """ Return true if ids are equal. """
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self):
        """ Return a hash of id. """
        return hash(self.id)


class ShowParentElem(dict):

    """ An abstract parent of show elements. """

    def __init__(self):
        """ Create a new ShowParentElem. """
        dict.__init__(self)

    def merge(self, other):
        """ Merge data from another ShowParentElem into this ShowParentElem. """
        for key in other:
            if key in self:
                self[key].merge(other[key])
            else:
                self[key] = other[key]

    @property
    def epwanted(self):
        """ True if any child episodes are wanted. """
        return [ep for ep in self.episodes if ep.wanted]

    @property
    def aired(self):
        """ Earliest airdate of child episode. """
        airdates = [ep.aired for ep in self.episodes if ep.aired is not None]
        if len(airdates):
            return min(airdates)
        else:
            return None

    @property
    def aired_max(self):
        """ Last airdate of child episode. """
        airdates = [ep.aired for ep in self.episodes if ep.aired is not None]
        if len(airdates):
            return max(airdates)
        else:
            return None

    @property
    def wanted(self):
        """ True if at least 75% of child episodes are wanted. """
        eps = [e for e in self.episodes if e.season.num != 0]
        wanted = [e for e in self.epwanted if e.season.num != 0]
        if len(eps) == 0:
            return False
        return float(len(wanted)) / float(len(eps)) > 0.75

    @property
    def episodes(self):
        """ All child episodes in order. """
        return list(chain(*[self[child].episodes for child in sorted(self)]))

    def format(self):
        """ Format all children. """
        for child in self.itervalues():
            child.format()

    def to_yaml(self):
        """ Return yaml representation of this ShowParentElem. """
        return dict([(k, v.to_yaml()) for k, v in self.iteritems()])

    @staticmethod
    def from_yaml(yml, child_type, parent):
        """ Create a new ShowParentElem from the given yaml representation. """
        return dict([(k, child_type.from_yaml(v, k, parent))
                     for k, v in yml.iteritems()])

    def find(self, id_):
        """
        Return ShowElem with the given ID in children.

        If no ShowElem with that ID exists, return None.
        """
        if self.id != id_[0:len(self.id)]:
            return None
        if id_ == self.id:
            return self

        for child in self.itervalues():
            f = child.find(id_)
            if f is not None:
                return f

        return None
