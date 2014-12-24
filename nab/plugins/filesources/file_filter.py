from nab.plugins.filesources import FileFilter


class KeywordFilter(FileFilter):
    key_str = {}

    def __init__(self, *keywords):
        self.keywords = keywords

        for keyword in self.keywords:
            if keyword not in self.__class__.key_str:
                self.__class__.key_str[keyword] = [keyword]

    def filter_field(self, field):
        keyword = "Other"
        for k in self.__class__.key_str:
            for kstr in self.__class__.key_str[k]:
                if kstr.lower() in field:
                    keyword = k
                    break

        try:
            rank = self.keywords.index(keyword)
        except ValueError:
            # keyword is not listed, check for 'Other' wildcard
            try:
                rank = self.keywords.index("Other")
            except ValueError:
                # other is not listed either! Reject file completely
                return None
        return 1.0 - float(rank) / len(self.keywords)


class TagFilter(KeywordFilter):

    def filter(self, f):
        return self.filter_field(f.tags)


class Quality(TagFilter):
    key_str = {
        "360p": ["360p", "x360"],
        "480p": ["480p", "x480"],
        "720p": ["720p", "x720", "HDTV"],
        "1080p": ["1080p", "x1080", "BRRip", "BDRip"],
    }
Quality.register("quality")


class Source(TagFilter):
    key_str = {
        "Cam": ["CAMRip", "TS", "TELESYNC", "PDVD"],
        "DVD": ["DVDRip", "DVD-5", "DVD-9"],
        "TV": ["TVRip", "TV Rip", "HDTV", "PDTV"],
        "BluRay": ["BRRip", "BDRip"]
    }
Source.register("source")


class Encoding(TagFilter):
    key_str = {
        "XviD": ["XviD", "DivX"],
        "h264": ["h264", "x264", "264"]
    }
Encoding.register("encoding")


class Groups(KeywordFilter):
    def filter(self, f):
        return self.filter_field([f.group])
Groups.register("groups")


class Fansubs(Groups):
    pass
Fansubs.register("fansubs")


class BadTags(TagFilter):
    def filter(self, f):
        has_tag = TagFilter.filter(self, f)
        if has_tag is not None:
            # includes a bad tag
            return None
        else:
            # does not include a bad tag
            return 1.0
BadTags.register("badtags")


class Seeds(FileFilter):

    def __init__(self, minimum=1):
        self.minimum = minimum

    def filter(self, f):
        # if num seeds are below minimum, reject
        if f.seeds is not None and f.seeds < self.minimum:
            return None

        if f.seeds is None:
            # if seed number is unknown, behave like there are 0.5 seeds
            # better than no seeds, but not as good as one!
            return 0.25
        return 1.0 - 10.0 / (f.seeds + 10.0)
Seeds.register("seeds")


class Weighted(FileFilter):
    def __init__(self, weight, filters):
        self.weight = weight
        self.filters = FileFilter.get_all(filters)

    def filter(self, f):
        values = [filt.filter(f) for filt in self.filters]
        if None in values:
            return None
        else:
            return sum(values) * self.weight


Weighted.register("weighted")
