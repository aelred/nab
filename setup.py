from distutils.core import setup
import py2exe
import os
import shutil


# get all plugins
plugins = []
for folder, sub, files in os.walk('plugins'):
    plugins_sub = []
    for f in files:
        path = os.path.join(folder, f)
        if os.path.isfile(path) and os.path.splitext(f)[1] == '.py':
            plugins_sub.append(path)
    plugins.append((folder, plugins_sub))

setup(
    options={'py2exe': {
        'bundle_files': 1,
        'compressed': True,
        'packages': ['plugins'],
        'includes':
        ['lxml._elementpath', 'dbhash']}},
    console=['__main__.py'],
    data_files=[('.', ['config.yaml'])] + plugins,
    )

# rename main file to ensemble.exe
shutil.move(os.path.join('dist', '__main__.exe'),
            os.path.join('dist', 'nab.exe'))
