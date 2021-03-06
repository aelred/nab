# use setuptools if available, else use distutils
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from distutils.dir_util import remove_tree

# if py2exe is not installed, then we can still install normally
try:
    import py2exe
except ImportError:
    pass

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
except OSError:
    pass

setup(
    name='nab',
    version='0.2',
    description='Automatic TV show download tool',
    author='Felix Chapman',
    packages=['nab', 'nab.plugins', 'nab.plugins.databases',
              'nab.plugins.downloaders', 'nab.plugins.filesources',
              'nab.plugins.shows'],
    install_requires=['appdirs', 'requests', 'tvdb_api', 'filecache',
                      'py-plex', 'watchdog', 'flask', 'pyyaml', 'memoized',
                      'unidecode', 'munkres', 'feedparser', 'py-utorrent',
                      'lxml', 'flask-holster'],

    dependency_links=[
        'https://github.com/ftao/py-utorrent/tarball/master#egg=py-utorrent'],

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
