"""
Module for classes with a register that registers subclasses.

These classes are mostly used for plugins in nab.
"""
from nab import log
from nab import plugins
import inspect


class Register:

    """ A lookup class for subclasses of a particular Entry class. """

    def __init__(self):
        """ Initialize lookup table as empty. """
        self.table = {}

    def load(self, cfg, accounts):
        """
        Load plugins from part of a config file.

        Given a yaml-style list of plugins from a config file, load the plugins
        in that list with the given parameters.

        This method is memoized so plugins are not constantly instantiated.
        """
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
                results += self.load(entry, accounts)
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

                # check if plugin requires account details
                if plugin_class.has_account:
                    param_dict['account'] = accounts[plugin_class.name]

                plugin = plugin_class(*param_list, **param_dict)
                results.append(plugin)

        return results


class Entry(object):

    """ The plugin base class with methods to register subclasses. """

    @property
    def type(self):
        """ The type of this entry. """
        return self._type

    @classmethod
    def register(cls, name, has_account=False):
        """ Register a new subclass under the given name. """
        cls._register.table[name] = cls
        cls.name = name
        cls.has_account = has_account
        cls.log = log.log.getChild(name)
        cls.log.debug("Found plugin")

    @classmethod
    def get_all(cls, cfg, accounts=None):
        """ Return loaded plugins from a given config file part. """
        if accounts is None:
            accounts = {}
        return cls._register.load(cfg, accounts)

    @classmethod
    def list_entries(cls):
        """ Return a list of all registered plugins. """
        return cls._register.table.values()

    @classmethod
    def help_text(cls):
        """ Return help text for this plugin. """
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
        """ Return the name of this plugin. """
        return type(self).name
