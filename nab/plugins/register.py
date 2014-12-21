""" Module for plugin base class. """
import nab.plugins

import inspect


class Register:

    """ A lookup class for subclasses of a particular Entry class. """

    def __init__(self):
        """ Initialize lookup table as empty. """
        self.table = {}

    def load(self, plugin_log, cfg, settings=None, accounts=None):
        """
        Load plugins from part of a config file.

        Given a yaml-style list of plugins from a config file, load the plugins
        in that list with the given parameters.
        """
        nab.plugins.load(plugin_log)
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
                results += self.load(plugin_log, entry, settings, accounts)
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
                    plugin_log.error("No plugin named %s" % entry)
                    continue

                # check if plugin requires config settings passed in
                if plugin_class.req_settings:
                    if settings is None:
                        raise ValueError('No global settings given.')
                    param_dict['settings'] = settings

                # check if plugin requires account details
                if plugin_class.req_account:
                    try:
                        param_dict['account'] = accounts[plugin_class.name]
                    except (KeyError, TypeError):
                        raise ValueError('No account given for plugin %s'
                                         % plugin_class.name)

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
    def init(cls, plugin_log):
        """ Call on plugin base classes only. """
        cls._logger = plugin_log

    @classmethod
    def register(cls, name, req_settings=False, req_account=False):
        """ Register a new subclass under the given name. """
        cls._register.table[name] = cls
        cls.name = name
        cls.req_settings = req_settings
        cls.req_account = req_account
        cls.log = cls._logger.getChild(name)
        cls.log.debug("Found plugin")

    @classmethod
    def get_all(cls, cfg, settings=None, accounts=None):
        """ Return loaded plugins from a given config file part. """
        return cls._register.load(cls._logger, cfg, settings, accounts)

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
