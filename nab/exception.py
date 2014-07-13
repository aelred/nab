class PluginError(Exception):

    def __init__(self, plugin, msg):
        plugin.log.error(msg)
        self.msg = msg

    def __str__(self):
        return self.msg
