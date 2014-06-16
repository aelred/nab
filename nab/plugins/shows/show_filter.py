from nab.show import ShowFilter
from nab import match


class Exclude(ShowFilter):

    def __init__(self, *shows):
        self.shows = shows

    def filter_show(self, show):
        for t in show.titles:
            if t in self.shows:
                return False
        return True
Exclude.register("exclude")


class Specials(ShowFilter):

    def __init__(self, include=True, exclude=None):
        self.include = include or []
        self.exclude = exclude or []

    def filter_episode(self, episode):
        def func(ep, keywords, inverse=False):
            try:
                iter(keywords)
            except TypeError:
                return True

            for t in ep.titles:
                for keyword in keywords:
                    if keyword in match.format_title(t):
                        return not inverse
            return inverse

        if episode.season.num != 0:
            return True

        if not func(episode, self.include):
            return False

        if not func(episode, self.exclude, True):
            return False
        return True
Specials.register("specials")


class Watched(ShowFilter):

    def __init__(self, include):
        self.include = include

    def filter_episode(self, episode):
        return self.include or not episode.watched
Watched.register("watched")


class Owned(ShowFilter):

    def __init__(self, include):
        self.include = include

    def filter_episode(self, episode):
        return self.include or not episode.owned
Owned.register("owned")


class Next(ShowFilter):

    def __init__(self, include, include_first=True):
        self.include = include
        self.include_first = include_first

    def filter_episode(self, episode):
        if not self.include:
            return True

        if (episode.num == 1 and episode.season.num == 1
           and not self.include_first):
            return False

        if not episode.previous:
            return True

        return not self.include or episode.previous.watched
Next.register("next")
