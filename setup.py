from distutils.core import setup
from distutils.dir_util import remove_tree
import py2exe
import os
import shutil


# get all plugins
plugins = []
for folder, sub, files in os.walk('nab/plugins'):
    plugins_sub = []
    for f in files:
        path = os.path.join(folder, f)
        if os.path.isfile(path) and os.path.splitext(f)[1] == '.py':
            plugins_sub.append(path)
    plugins.append((folder, plugins_sub))

# delete previous dist
try:
    remove_tree('./dist', False)
except WindowsError:
    pass

setup(
    name='nab',
    version='0.1',
    description='Automatic TV show download tool',
    author='Felix Chapman',
    packages=['nab', 'nab.plugins', 'nab.plugins.databases',
              'nab.plugins.downloaders', 'nab.plugins.filesources',
              'nab.plugins.shows'],
    requires=['appdirs', 'requests', 'tvdb_api', 'filecache', 'plex',
              'watchdog', 'flask'],

    options={'py2exe': {
        'bundle_files': 1,
        'compressed': True,
        'packages': ['nab', 'nab.plugins'],
        'includes':
        ['lxml._elementpath', 'dbhash']}},
    console=['nab/__main__.py'],
    entry_points={'console_scripts': ['nab = nab.__main__:main']},
    data_files=[('.', ['config_default.yaml'])] + plugins,
    )

# rename main file to ensemble.exe
try:
    shutil.move(os.path.join('dist', '__main__.exe'),
                os.path.join('dist', 'nab.exe'))
except IOError:
    # if not an executable, skip
    pass
