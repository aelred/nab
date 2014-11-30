""" Module for exceptions used in nab. """


class PluginError(Exception):

    """ Thrown by plugins when a problem occurs. """

    def __init__(self, plugin, msg):
        """ Create a PluginError for the given plugin. """
        plugin.log.error(msg)
        self.msg = msg

    def __str__(self):
        """ Return the message associated with this error. """
        return self.msg
