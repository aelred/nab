""" Server that hosts a web interface to nab. """
from flask import Flask, request, abort, render_template, make_response
from flask.ext.holster.main import init_holster
import yaml
import copy
import urllib
import os
from urlparse import urlparse

app = Flask('nab')
init_holster(app)

_nab = None

_STATIC = os.path.join(os.path.dirname(__file__), 'static')


def init(nab_):
    """ Initialize server with the given list of shows. """
    global _nab
    _nab = nab_

    banners = os.path.join(_STATIC, 'banners')
    if not os.path.exists(banners):
        os.makedirs(banners)


def run():
    """ Run the server. Doesn't return until server closes. """
    app.run(debug=True, use_reloader=False)


@app.route('/')
def index():
    """ Return index page of web interface. """
    return render_template('index.html')


@app.route('/log')
def log_():
    """ Return log file in plain text. """
    response = make_response(_nab.logger.get_log_text())
    response.headers['content-type'] = 'text/plain'
    return response


@app.holster('/config', methods=['GET', 'POST'])
def config_all():
    """ Return entire config file. """
    return get_config([])


@app.holster('/config/<path:path>', methods=['GET', 'POST'])
def config_path(path=''):
    """ Return part of config file. """
    return get_config(path.split('/'))


@app.holster('/remove/<path:path>', methods=['POST'])
def remove(path):
    """ Remove part of config file. """
    path = path.split('/')
    plugin = request.values['plugin']
    conf_copy = copy.deepcopy(_nab.config.config)
    conf_sub = access_config_path(conf_copy, path)

    try:
        # search for plugin
        for i, p in enumerate(conf_sub):
            try:
                # test for:
                # - following
                # or
                # - following:
                #       params...
                if plugin == p or plugin in p.keys():
                    break
            except AttributeError:
                # this entry is not a dictionary, ignore
                pass
        index = i
    except AttributeError:
        # this is a dictionary
        index = plugin

    # delete plugin from config file
    del conf_sub[index]
    _nab.config.change_config(conf_copy)

    return conf_copy


def get_config(path):
    """ Return part of path along config file. """
    # navigate provided path along config file
    conf_copy = copy.deepcopy(_nab.config.config)
    conf_sub = access_config_path(conf_copy, path)

    if request.method == 'POST':
        # replace config path with given data
        access_config_path(conf_copy, path, yaml.safe_load(request.data))
        # update config
        _nab.config.change_config(conf_copy)

    return conf_sub


def access_config_path(config_data, path, config_set=None):
    """ Access and optionally set part of the config path. """
    conf_sub = config_data
    # navigate to second-from-last index, to allow referencing later
    for p in path[:-1]:
        conf_sub = conf_sub[p]

    if config_set is not None:
        conf_sub[path[-1]] = config_set

    if path:
        return conf_sub[path[-1]]
    else:
        return config_data


def _down_yaml(download):
    entry = _nab.download_manager.get_downloads()[download]
    status = _nab.downloader().get_download_status(download.id)
    status['id'] = download.id
    status['filename'] = download.filename
    status['url'] = download.url
    status['magnet'] = download.magnet
    status['entry'] = entry.id
    status['show'] = entry.id[0]
    return status


# RESTful downloads interface
@app.holster('/downloads', methods=['GET'])
def downloads():
    """ Return list of all downloads. """
    return map(_down_yaml, _nab.download_manager.get_downloads())


@app.holster('/downloads/<string:down_id>', methods=['GET'])
def download(down_id):
    """ Return information on a particular download ID. """
    down = next(d for d in _nab.download_manager.get_downloads()
                if d.id == down_id)
    return _down_yaml(down)


# format show data when sending
def _format_show(show):
    # download local copy of banner
    url = show['banner']
    if url:
        ext = os.path.splitext(urlparse(url).path)[1]
        local_path = os.path.join('static', 'banners', show['id'] + ext)
        abs_path = os.path.join(os.path.dirname(__file__), local_path)
        if not os.path.isfile(abs_path):
            urllib.urlretrieve(url, abs_path)
        show['banner'] = local_path
    return show


# RESTful shows interface
@app.holster('/shows', methods=['GET'])
def shows():
    """ Return a condensed view of all shows. """
    def format(show):
        yml = show.to_yaml()
        del yml['seasons']
        return _format_show(yml)
    return map(format, _nab.shows.itervalues())


@app.holster('/shows/<path:path>', methods=['GET'])
def show(path):
    """ Return complete information about a show, season or episode. """
    search = path.split('/')
    # everything after the show name is an integer (season/ep number)
    search[1:] = [int(s) for s in search[1:]]

    entry = _nab.shows.find(tuple(search))

    if not entry:
        abort(204)

    yml = entry.to_yaml()

    if len(search) == 1:
        # searching for show
        yml = _format_show(yml)

    return yml
