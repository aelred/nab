from itertools import chain
import log
import plugins


class Register:

    def __init__(self, cfg):
        self.table = {}
        self.cfg = cfg
        self._loadcache = None

    def load(self, cfg=None):
        use_cache = False

        if cfg is None:
            cfg = self.cfg
            use_cache = True

        if use_cache and self._loadcache:
            return self._loadcache

        plugins.load()
        results = []

        # handle case where given entry is just a string
        if isinstance(cfg, basestring):
            # transform into dictionary
            cfg = {cfg: {}}

        # handle case where entries are a list, not a dictionary
        try:
            cfg.keys()
        except AttributeError:
            # iterate on list
            for entry in cfg:
                results += self.load(entry)
        else:
            # iterate on dictionary
            for entry, params in cfg.iteritems():

                # check for list or dictionary parameters
                param_dict = {}
                param_list = []
                try:
                    params.iterkeys()
                except AttributeError:
                    param_list = params
                else:
                    param_dict = params

                # check if param is just a single value
                try:
                    iter(param_list)
                except TypeError:
                    param_list = [params]

                try:
                    plugin_class = self.table[entry]
                except KeyError:
                    log.log.error("No plugin named %s" % entry)
                    continue

                plugin = plugin_class(*param_list, **param_dict)
                results.append(plugin)

        if use_cache:
            self._loadcache = results

        return results


class Entry(object):

    @classmethod
    def register(cls, name):
        cls._register.table[name] = cls
        cls.name = name
        cls.log = log.log.getChild(name)
        cls.log.debug("Found plugin")

    @classmethod
    def get_all(cls, cfg=None):
        return cls._register.load(cfg)

    def __str__(self):
        return type(self).name
