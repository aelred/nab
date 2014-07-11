from nab import log
from nab import plugins
import inspect
from memoized import memoized


class Register:

    def __init__(self):
        self.table = {}

    @memoized(hashable=False)
    def load(self, cfg):
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

    @classmethod
    def list_entries(cls):
        return cls._register.table.values()

    @classmethod
    def help_text(cls):
        text = "Name\n\t%s\nType\n\t%s\n" % (cls.name, cls._type)

        try:
            argspec = inspect.getargspec(cls.__init__)
        except TypeError:
            # has no __init__ method
            params = []
        else:
            # get parameters by inspection
            args = argspec.args
            if argspec.defaults:
                defaults = map(lambda d: [d], argspec.defaults)
            else:
                defaults = []
            defaults = [None] * (len(args) - len(defaults)) + defaults
            params = []

            # get regular parameters
            for arg, default in zip(args, defaults)[1:]:
                params.append(arg)
                if default:
                    if default[0] is None:
                        params[-1] += "\t(optional)"
                    else:
                        params[-1] += "\t(default: %s)" % default[0]

            # get variable arguments
            if argspec.varargs:
                params += argspec.varargs + "\t(list)"

            # get keyword arguments
            if argspec.keywords:
                params += argspec.keywords + "\t(dictionary)"

        # add parameter info
        text += "Parameters\n"
        if len(params) == 0:
            params.append("None")
        for param in params:
            text += "\t" + param + "\n"

        # add docstring
        if __doc__:
            text += "Description\n\t" + cls.__doc__ + "\n"

        return text.rstrip()

    def __str__(self):
        return type(self).name
